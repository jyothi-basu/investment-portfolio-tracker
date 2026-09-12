"""Verify PAT security, public conversation APIs, and MCP session isolation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import asyncio
import os
from pathlib import Path
import socket
import sqlite3
import threading
import time
import unittest
import uuid
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
import httpx
import uvicorn

from app.repository import db
from app.security.jwt import get_jwt_settings
from app.security.personal_access_tokens import (
    PersonalAccessTokenError,
    authenticate_personal_access_token,
    create_personal_access_token,
)
from app.services import auth_service, portfolio_service
from app.services.chat_title_service import generate_title_if_needed, is_greeting_only
from main import create_fastapi_app


class MCPAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.original_db_path = db.DB_PATH
        self.original_environment = {
            name: os.environ.get(name)
            for name in ("SECRET_KEY", "JWT_SECRET_KEY", "JWT_COOKIE_SECURE")
        }
        self.test_db_path = Path(__file__).resolve().parent / f".mcp-test-{uuid.uuid4().hex}.db"
        db.DB_PATH = self.test_db_path
        os.environ["SECRET_KEY"] = "test-only-session-key-with-at-least-32-characters"
        os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-with-at-least-32-characters"
        os.environ["JWT_COOKIE_SECURE"] = "false"
        get_jwt_settings.cache_clear()
        db.init_db()
        portfolio_service.register_user("User One", "one@example.com", "password123")
        portfolio_service.register_user("User Two", "two@example.com", "password123")
        self.user_one = portfolio_service.authenticate_user("one@example.com", "password123")
        self.user_two = portfolio_service.authenticate_user("two@example.com", "password123")

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        for name, value in self.original_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        get_jwt_settings.cache_clear()
        self.test_db_path.unlink(missing_ok=True)

    def _jwt_headers(self, user_id):
        pair = auth_service.issue_token_pair(user_id)
        return {"Authorization": f"Bearer {pair.access_token}"}

    def _login_browser(self, client: TestClient):
        login_page = client.get("/login")
        csrf_token = login_page.text.split(
            'name="csrf_token" value="', 1
        )[1].split('"', 1)[0]
        return client.post(
            "/login",
            data={
                "email": "one@example.com",
                "password": "password123",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )

    def test_pat_is_argon2_hashed_and_raw_value_is_returned_once(self):
        issued = create_personal_access_token(self.user_one["user_id"], "Codex")
        stored = db.fetch_personal_access_token_by_selector(
            issued.token.split("_", 3)[2]
        )

        self.assertTrue(issued.token.startswith("ipt_pat_"))
        self.assertTrue(stored["token_hash"].startswith("$argon2"))
        self.assertNotIn(issued.token, tuple(stored))
        self.assertEqual(
            authenticate_personal_access_token(issued.token),
            self.user_one["user_id"],
        )
        self.assertIsNotNone(
            db.fetch_personal_access_token_by_selector(stored["token_selector"])[
                "last_used_at"
            ]
        )

    def test_revoked_and_expired_pats_are_rejected(self):
        issued = create_personal_access_token(self.user_one["user_id"], "Temporary")
        db.revoke_personal_access_token(issued.token_id, self.user_one["user_id"])
        with self.assertRaises(PersonalAccessTokenError):
            authenticate_personal_access_token(issued.token)

        expiry = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        expired = create_personal_access_token(
            self.user_one["user_id"], "Expiring", expiry
        )
        db.execute(
            "UPDATE personal_access_tokens SET expires_at = ? WHERE token_id = ?",
            ((datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(), expired.token_id),
        )
        with self.assertRaises(PersonalAccessTokenError):
            authenticate_personal_access_token(expired.token)

    def test_pat_management_uses_jwt_and_never_lists_raw_tokens(self):
        app = create_fastapi_app()
        headers = self._jwt_headers(self.user_one["user_id"])
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/personal-access-tokens",
                headers=headers,
                json={"name": "Codex CLI"},
            )
            listed = client.get("/api/v1/personal-access-tokens", headers=headers)
            revoked = client.delete(
                f"/api/v1/personal-access-tokens/{created.json()['token_id']}",
                headers=headers,
            )

        self.assertEqual(created.status_code, 201)
        self.assertIn("token", created.json())
        self.assertEqual(listed.status_code, 200)
        self.assertNotIn("token", listed.json()[0])
        self.assertEqual(revoked.status_code, 204)

    def test_browser_pat_page_displays_raw_token_only_after_creation(self):
        app = create_fastapi_app()
        with TestClient(app) as client:
            self._login_browser(client)
            page = client.get("/settings/personal-access-tokens")
            csrf_token = page.text.split(
                'name="csrf_token" value="', 1
            )[1].split('"', 1)[0]
            created = client.post(
                "/settings/personal-access-tokens",
                data={"name": "Browser test", "csrf_token": csrf_token},
            )
            raw_token = created.text.split(
                'id="new-personal-access-token"', 1
            )[1].split('value="', 1)[1].split('"', 1)[0]
            revisited = client.get("/settings/personal-access-tokens")
            token_id = db.fetch_personal_access_tokens(
                self.user_one["user_id"]
            )[0]["token_id"]
            revoked = client.post(
                f"/settings/personal-access-tokens/{token_id}/revoke",
                data={"csrf_token": csrf_token},
                follow_redirects=False,
            )

        self.assertEqual(created.status_code, 200)
        self.assertTrue(raw_token.startswith("ipt_pat_"))
        self.assertNotIn(raw_token, revisited.text)
        self.assertNotIn(raw_token, client.cookies.get("session", ""))
        self.assertEqual(revoked.status_code, 303)
        self.assertIsNotNone(
            db.fetch_personal_access_tokens(self.user_one["user_id"])[0]["revoked_at"]
        )

    def test_conversation_listing_is_user_scoped_and_hides_chat_id(self):
        own_chat = db.create_chat(self.user_one["user_id"], "Annual report")
        db.create_chat(self.user_two["user_id"], "Foreign chat")
        db.create_chat_message(own_chat, "USER", "Compare the annual reports")
        db.create_document(own_chat, self.user_one["user_id"], "report.pdf", "COMPLETED")
        app = create_fastapi_app()

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/conversations",
                headers=self._jwt_headers(self.user_one["user_id"]),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        summary = response.json()[0]
        self.assertNotIn("chat_id", summary)
        self.assertEqual(summary["chat_title"], "Annual report")
        self.assertEqual(summary["message_count"], 1)
        self.assertEqual(summary["uploaded_documents"], ["report.pdf"])

    def test_conversation_listing_accepts_pat_identity(self):
        db.create_chat(self.user_one["user_id"], "PAT conversation")
        issued = create_personal_access_token(self.user_one["user_id"], "MCP")
        app = create_fastapi_app()

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/conversations",
                headers={"Authorization": f"Bearer {issued.token}"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["chat_title"], "PAT conversation")

    def test_mcp_messages_require_pat_not_jwt(self):
        issued = create_personal_access_token(self.user_one["user_id"], "MCP")
        app = create_fastapi_app()
        with TestClient(app) as client:
            unauthenticated_sse = client.get("/mcp/sse")
            pat_response = client.post(
                "/mcp/messages?session_id=missing",
                headers={"Authorization": f"Bearer {issued.token}"},
                json={},
            )
            jwt_response = client.post(
                "/mcp/messages?session_id=missing",
                headers=self._jwt_headers(self.user_one["user_id"]),
                json={},
            )

        self.assertEqual(unauthenticated_sse.status_code, 401)
        self.assertEqual(pat_response.status_code, 404)
        self.assertEqual(jwt_response.status_code, 401)

    def test_authenticated_sse_lists_selects_and_searches_conversation(self):
        chat_id = db.create_chat(self.user_one["user_id"], "Aster report")
        chat = db.fetch_chat(chat_id, self.user_one["user_id"])
        foreign_chat_id = db.create_chat(self.user_two["user_id"], "Private report")
        foreign_chat = db.fetch_chat(foreign_chat_id, self.user_two["user_id"])
        issued = create_personal_access_token(self.user_one["user_id"], "SSE test")
        app = create_fastapi_app()

        with socket.socket() as candidate:
            candidate.bind(("127.0.0.1", 0))
            port = candidate.getsockname()[1]

        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        )
        thread = threading.Thread(target=server.run, daemon=True)
        chunks = [
            {
                "content": "Revenue: Rs. 1,240 crore",
                "metadata": {
                    "original_filename": "Aster_Report.pdf",
                    "page_number": 1,
                    "chunk_index": 0,
                },
                "distance": 0.2,
            },
            {
                "content": "Revenue: Rs. 860 crore",
                "metadata": {
                    "original_filename": "Nova_Report.pdf",
                    "page_number": 1,
                    "chunk_index": 0,
                },
                "distance": 0.3,
            },
        ]

        async def exercise_client():
            headers = {"Authorization": f"Bearer {issued.token}"}
            async with sse_client(
                f"http://127.0.0.1:{port}/mcp/sse",
                headers=headers,
            ) as streams:
                async with ClientSession(*streams) as client:
                    await client.initialize()
                    tools = await client.list_tools()
                    listed = await client.call_tool("list_conversations")
                    selected = await client.call_tool(
                        "select_conversation",
                        {"conversation_id": chat["conversation_id"]},
                    )
                    rejected = await client.call_tool(
                        "select_conversation",
                        {"conversation_id": foreign_chat["conversation_id"]},
                    )
                    searched = await client.call_tool(
                        "search_uploaded_documents",
                        {"query": "Aster revenue"},
                    )
                    return tools, listed, selected, rejected, searched

        with patch("app.mcp.server.retrieve_relevant_chunks", return_value=chunks):
            thread.start()
            deadline = time.monotonic() + 5
            while not server.started and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(server.started)
            try:
                tools, listed, selected, rejected, searched = asyncio.run(exercise_client())
            finally:
                server.should_exit = True
                thread.join(timeout=5)

        self.assertEqual(
            {tool.name for tool in tools.tools},
            {"list_conversations", "select_conversation", "search_uploaded_documents"},
        )
        self.assertIn(chat["conversation_id"], listed.content[0].text)
        self.assertFalse(selected.isError)
        self.assertTrue(rejected.isError)
        self.assertIn("Rs. 1,240 crore", searched.content[0].text)
        self.assertIn("Rs. 860 crore", searched.content[0].text)
        self.assertIn("Aster_Report.pdf", searched.content[0].text)
        self.assertIn("Nova_Report.pdf", searched.content[0].text)

    def test_codex_streamable_http_discovers_and_calls_tools(self):
        chat_id = db.create_chat(self.user_one["user_id"], "Streamable report")
        chat = db.fetch_chat(chat_id, self.user_one["user_id"])
        issued = create_personal_access_token(self.user_one["user_id"], "Codex")
        app = create_fastapi_app()

        with socket.socket() as candidate:
            candidate.bind(("127.0.0.1", 0))
            port = candidate.getsockname()[1]

        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        )
        thread = threading.Thread(target=server.run, daemon=True)
        chunks = [
            {
                "content": "Revenue: Rs. 1,240 crore",
                "metadata": {
                    "original_filename": "Aster_Report.pdf",
                    "page_number": 1,
                    "chunk_index": 0,
                },
                "distance": 0.2,
            }
        ]

        async def exercise_client():
            async with httpx.AsyncClient(
                headers={"Authorization": f"Bearer {issued.token}"}
            ) as http_client:
                async with streamable_http_client(
                    f"http://127.0.0.1:{port}/mcp/sse",
                    http_client=http_client,
                ) as streams:
                    async with ClientSession(streams[0], streams[1]) as client:
                        await client.initialize()
                        tools = await client.list_tools()
                        selected = await client.call_tool(
                            "select_conversation",
                            {"conversation_id": chat["conversation_id"]},
                        )
                        searched = await client.call_tool(
                            "search_uploaded_documents",
                            {"query": "Aster revenue"},
                        )
                        return tools, selected, searched, streams[2]()

        with patch("app.mcp.server.retrieve_relevant_chunks", return_value=chunks):
            thread.start()
            deadline = time.monotonic() + 5
            while not server.started and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(server.started)
            try:
                tools, selected, searched, session_id = asyncio.run(exercise_client())
            finally:
                server.should_exit = True
                thread.join(timeout=5)

        self.assertEqual(
            {tool.name for tool in tools.tools},
            {"list_conversations", "select_conversation", "search_uploaded_documents"},
        )
        self.assertIsNotNone(session_id)
        self.assertFalse(selected.isError)
        self.assertIn("Rs. 1,240 crore", searched.content[0].text)

    def test_title_generation_skips_greetings_and_runs_once(self):
        chat_id = db.create_chat(self.user_one["user_id"])
        self.assertTrue(is_greeting_only("Hi, thanks!"))
        self.assertIsNone(
            generate_title_if_needed(chat_id, self.user_one["user_id"], "Hello")
        )

        model = Mock()
        model.invoke.return_value = Mock(content="Compare Aster and Nova Revenue Today")
        with patch("app.services.chat_title_service.build_chat_model", return_value=model):
            title = generate_title_if_needed(
                chat_id,
                self.user_one["user_id"],
                "Which company has higher revenue?",
            )
            generate_title_if_needed(
                chat_id,
                self.user_one["user_id"],
                "A different meaningful question",
            )

        self.assertEqual(title, "Compare Aster and Nova Revenue Today")
        self.assertEqual(model.invoke.call_count, 1)


class ConversationMigrationTests(unittest.TestCase):
    def test_existing_chat_receives_public_uuid(self):
        original_db_path = db.DB_PATH
        test_db_path = Path(__file__).resolve().parent / f".migration-{uuid.uuid4().hex}.db"
        try:
            db.DB_PATH = test_db_path
            connection = sqlite3.connect(test_db_path)
            connection.executescript(
                """
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL
                );
                CREATE TABLE chats (
                    chat_id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                INSERT INTO users VALUES (1, 'Existing', 'existing@example.com', 'hash');
                INSERT INTO chats VALUES (1, 1, 'Existing chat', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                """
            )
            connection.close()

            db.init_db()
            migrated = db.fetch_chat(1, 1)

            self.assertEqual(str(uuid.UUID(migrated["conversation_id"])), migrated["conversation_id"])
        finally:
            db.DB_PATH = original_db_path
            test_db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

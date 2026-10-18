"""Verify JWT issuance, refresh rotation, revocation, and request authentication."""

from __future__ import annotations

import os
import pytest

from fastapi.testclient import TestClient

from app.repository import database
from app.repository import db
from app.security.jwt import TokenValidationError, decode_token, get_jwt_settings
from app.services import auth_service, portfolio_service
from main import create_fastapi_app
from tests.database_helpers import cleanup_test_database, configure_test_database


class TestJWTAuthentication:
    def setup_method(self):
        self.original_engine = database.engine
        self.original_session_factory = database.SessionLocal
        self.original_environment = {
            name: os.environ.get(name)
            for name in ("SECRET_KEY", "JWT_SECRET_KEY", "JWT_COOKIE_SECURE")
        }
        configure_test_database()
        os.environ["SECRET_KEY"] = (
            "test-only-session-key-with-at-least-32-characters"
        )
        os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-with-at-least-32-characters"
        os.environ["JWT_COOKIE_SECURE"] = "false"
        get_jwt_settings.cache_clear()
        db.init_db()
        portfolio_service.register_user(
            "Test User",
            "test@example.com",
            "password123",
        )
        self.user = portfolio_service.authenticate_user(
            "test@example.com",
            "password123",
        )

    def teardown_method(self):
        cleanup_test_database()
        database.engine = self.original_engine
        database.SessionLocal = self.original_session_factory
        for name, value in self.original_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        get_jwt_settings.cache_clear()

    def _login_browser(self, client: TestClient):
        login_page = client.get("/login")
        csrf_token = login_page.text.split(
            'name="csrf_token" value="', 1
        )[1].split('"', 1)[0]
        return client.post(
            "/login",
            data={
                "email": "test@example.com",
                "password": "password123",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )

    def test_refresh_token_is_rotated_and_cannot_be_reused(self):
        user = portfolio_service.authenticate_user(
            "test@example.com",
            "password123",
        )
        original_pair = auth_service.issue_token_pair(user["user_id"])
        replacement_pair = auth_service.rotate_refresh_token(
            original_pair.refresh_token
        )

        assert decode_token(replacement_pair.access_token, "access")["user_id"] == user["user_id"]
        with pytest.raises(TokenValidationError):
            auth_service.rotate_refresh_token(original_pair.refresh_token)

    def test_browser_login_uses_jwt_cookies_and_refreshes_access(self):
        app = create_fastapi_app()
        with TestClient(app) as client:
            login_response = self._login_browser(client)

            assert login_response.status_code == 303
            assert client.cookies.get("access_token") is not None
            original_refresh = client.cookies.get("refresh_token")
            assert original_refresh is not None
            assert client.get("/dashboard").status_code == 200

            client.cookies.delete("access_token")
            assert client.get("/dashboard").status_code == 200
            assert client.cookies.get("refresh_token") != original_refresh

    def test_bearer_access_token_authenticates_without_cookies(self):
        user = portfolio_service.authenticate_user(
            "test@example.com",
            "password123",
        )
        pair = auth_service.issue_token_pair(user["user_id"])
        app = create_fastapi_app()

        with TestClient(app) as client:
            response = client.get(
                "/dashboard",
                headers={"Authorization": f"Bearer {pair.access_token}"},
            )

        assert response.status_code == 200

    def test_logout_revokes_refresh_token_and_clears_cookies(self):
        app = create_fastapi_app()
        with TestClient(app) as client:
            self._login_browser(client)
            refresh_token = client.cookies.get("refresh_token")
            dashboard = client.get("/dashboard")
            csrf_token = dashboard.text.split(
                'name="csrf_token" value="', 1
            )[1].split('"', 1)[0]

            response = client.post(
                "/logout",
                data={"csrf_token": csrf_token},
                follow_redirects=False,
            )

            assert response.status_code == 303
            assert client.cookies.get("access_token") is None
            assert client.cookies.get("refresh_token") is None
            with pytest.raises(TokenValidationError):
                auth_service.rotate_refresh_token(refresh_token)

    def test_state_changing_form_rejects_missing_csrf_token(self):
        app = create_fastapi_app()
        with TestClient(app) as client:
            self._login_browser(client)
            response = client.post("/accounts", data={"broker_name": "Example"})

        assert response.status_code == 403

    def test_chat_id_is_checked_against_authenticated_user(self):
        own_chat_id = db.create_chat(self.user["user_id"], "Owned chat")
        portfolio_service.register_user(
            "Another User",
            "another@example.com",
            "password123",
        )
        another_user = portfolio_service.authenticate_user(
            "another@example.com",
            "password123",
        )
        foreign_chat_id = db.create_chat(another_user["user_id"], "Foreign chat")
        app = create_fastapi_app()

        with TestClient(app) as client:
            self._login_browser(client)
            response = client.get(
                f"/chat?chat_id={foreign_chat_id}",
                follow_redirects=False,
            )

        assert response.status_code == 303
        assert f"chat_id={own_chat_id}" in response.headers["location"]

    def test_authenticated_server_rendered_pages_still_load(self):
        app = create_fastapi_app()
        with TestClient(app) as client:
            self._login_browser(client)
            for path in (
                "/dashboard",
                "/accounts",
                "/transactions",
                "/prices",
                "/holdings",
                "/account-summary",
                "/portfolio-summary",
                "/chat",
            ):
                response = client.get(path)
                assert response.status_code == 200, path

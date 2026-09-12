"""Run the shared MCP server over STDIO for trusted local clients."""

from __future__ import annotations

import os
from uuid import UUID

from dotenv import load_dotenv

from app.mcp.server import bind_stdio_session, create_server, reset_stdio_session
from app.mcp.session_manager import session_manager
from app.repository import db


def _configured_conversation_id() -> str:
    value = (os.environ.get("MCP_CONVERSATION_ID") or "").strip()
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise RuntimeError(
            "MCP_CONVERSATION_ID must contain the UUID of an existing conversation."
        ) from exc


def run_stdio() -> None:
    """Initialize trusted local scope and start the blocking STDIO transport."""

    load_dotenv()
    db.init_db()
    conversation_id = _configured_conversation_id()
    chat = db.fetch_chat_by_conversation_id_unscoped(conversation_id)
    if not chat:
        raise RuntimeError("MCP_CONVERSATION_ID does not identify an existing conversation.")

    session_id = "stdio"
    session_manager.create(session_id, int(chat["user_id"]), conversation_id)
    context_token = bind_stdio_session(session_id)
    try:
        create_server().run(transport="stdio")
    finally:
        reset_stdio_session(context_token)
        session_manager.remove(session_id)

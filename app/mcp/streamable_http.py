"""Adapt PAT-scoped FastAPI requests to MCP Streamable HTTP sessions."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.responses import Response

from app.mcp.server import create_server
from app.mcp.session_manager import session_manager
from app.mcp.sse import _AlreadySentResponse, get_transport_security_settings


logger = logging.getLogger(__name__)


def _create_streamable_http_manager() -> StreamableHTTPSessionManager:
    return StreamableHTTPSessionManager(
        app=create_server()._mcp_server,
        stateless=False,
        security_settings=get_transport_security_settings(),
    )


@asynccontextmanager
async def run_streamable_http_manager(app):
    """Run the SDK manager's task group for the FastAPI application lifetime."""

    manager = _create_streamable_http_manager()
    app.state.streamable_http_manager = manager
    async with manager.run():
        try:
            yield
        finally:
            app.state.streamable_http_manager = None


def _response_from_events(response_start, body_parts) -> Response:
    status_code = response_start["status"] if response_start else 200
    raw_headers = response_start.get("headers", []) if response_start else []
    headers = {
        key.decode(): value.decode()
        for key, value in raw_headers
        if key.lower() != b"content-length"
    }
    return Response(
        content=b"".join(body_parts),
        status_code=status_code,
        headers=headers,
    )


async def handle_streamable_http(request, user_id: int) -> Response:
    """Authorize and execute one stateful Streamable HTTP MCP request."""

    session_id = request.headers.get("mcp-session-id")
    if session_id and not session_manager.get_for_user(session_id, user_id):
        logger.warning(
            "mcp.streamable_http.session_rejected session_id=%s user_id=%s",
            session_id,
            user_id,
        )
        return Response(status_code=404, content="MCP session not found.")

    manager = request.app.state.streamable_http_manager
    if manager is None:
        return Response(status_code=503, content="MCP transport is unavailable.")
    if request.method == "GET":
        if not session_id:
            return Response(status_code=400, content="Mcp-Session-Id is required.")
        await manager.handle_request(request.scope, request.receive, request._send)
        return _AlreadySentResponse()

    response_start = None
    body_parts = []

    async def capture_send(message):
        nonlocal response_start
        if message["type"] == "http.response.start":
            response_start = message
        elif message["type"] == "http.response.body":
            body_parts.append(message.get("body", b""))

    await manager.handle_request(request.scope, request.receive, capture_send)
    response = _response_from_events(response_start, body_parts)
    returned_session_id = response.headers.get("mcp-session-id")

    if not session_id and returned_session_id and request.method == "POST":
        session_manager.create(returned_session_id, user_id)
        logger.info(
            "mcp.streamable_http.connected session_id=%s user_id=%s",
            returned_session_id,
            user_id,
        )
    elif session_id and request.method == "DELETE":
        removed = session_manager.remove(session_id)
        logger.info(
            "mcp.streamable_http.disconnected session_id=%s user_id=%s cleaned=%s",
            session_id,
            user_id,
            bool(removed),
        )
    return response

"""Bridge authenticated FastAPI requests to the shared MCP SSE transport."""

from __future__ import annotations

import asyncio
from functools import lru_cache
import logging
import os

from mcp.server.sse import SseServerTransport
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import Response

from app.mcp.server import create_server
from app.mcp.session_manager import session_manager


logger = logging.getLogger(__name__)
_connection_lock = asyncio.Lock()


class _AlreadySentResponse(Response):
    """Tell FastAPI the SDK has already written the streaming ASGI response."""

    async def __call__(self, scope, receive, send) -> None:
        return None


def _csv_setting(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def get_transport_security_settings() -> TransportSecuritySettings:
    """Build the shared HTTP transport host and origin allowlists."""

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_csv_setting(
            "MCP_ALLOWED_HOSTS",
            "127.0.0.1,127.0.0.1:*,localhost,localhost:*",
        ),
        allowed_origins=_csv_setting(
            "MCP_ALLOWED_ORIGINS",
            "http://127.0.0.1:*,http://localhost:*",
        ),
    )


@lru_cache(maxsize=1)
def _get_transport() -> SseServerTransport:
    return SseServerTransport(
        "/mcp/messages",
        security_settings=get_transport_security_settings(),
    )


async def open_sse_connection(request, user_id: int) -> Response:
    """Open one SSE connection and mirror its SDK session into trusted state."""

    transport = _get_transport()
    connection = transport.connect_sse(
        request.scope,
        request.receive,
        request._send,
    )
    session_id = None
    entered = False
    try:
        # The SDK owns JSON-RPC framing and generates the wire session ID. The
        # lock lets us associate that ID with the PAT identity without copying
        # or replacing its transport implementation.
        async with _connection_lock:
            before = set(transport._read_stream_writers)
            streams = await connection.__aenter__()
            entered = True
            created = set(transport._read_stream_writers) - before
            if len(created) != 1:
                raise RuntimeError("Unable to identify the newly created MCP session.")
            session_id = next(iter(created)).hex
            session_manager.create(session_id, user_id)

        logger.info("mcp.sse.connected session_id=%s user_id=%s", session_id, user_id)
        await create_server()._mcp_server.run(
            streams[0],
            streams[1],
            create_server()._mcp_server.create_initialization_options(),
        )
    finally:
        if session_id:
            removed = session_manager.remove(session_id)
            logger.info(
                "mcp.sse.disconnected session_id=%s user_id=%s cleaned=%s",
                session_id,
                user_id,
                bool(removed),
            )
        if entered:
            await connection.__aexit__(None, None, None)
    return _AlreadySentResponse()


async def handle_sse_message(request, user_id: int) -> Response:
    """Authorize an MCP JSON-RPC POST before handing it to the SDK transport."""

    session_id = request.query_params.get("session_id", "")
    if not session_manager.get_for_user(session_id, user_id):
        logger.warning(
            "mcp.sse.message_rejected session_id=%s user_id=%s",
            session_id or "missing",
            user_id,
        )
        return Response(status_code=404, content="MCP session not found.")

    response_start = None
    body_parts = []

    async def capture_send(message):
        nonlocal response_start
        if message["type"] == "http.response.start":
            response_start = message
        elif message["type"] == "http.response.body":
            body_parts.append(message.get("body", b""))

    await _get_transport().handle_post_message(
        request.scope,
        request.receive,
        capture_send,
    )
    status_code = response_start["status"] if response_start else 202
    headers = dict(response_start.get("headers", [])) if response_start else {}
    return Response(
        content=b"".join(body_parts),
        status_code=status_code,
        headers={key.decode(): value.decode() for key, value in headers.items()},
    )

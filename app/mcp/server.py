"""Register shared MCP tools independently of STDIO and SSE transports."""

from __future__ import annotations

from contextvars import ContextVar
import logging
from uuid import UUID

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from app.ai.prompts import format_document_chunks
from app.ai.rag.retriever import retrieve_relevant_chunks
from app.mcp.session_manager import MCPSession, session_manager
from app.services import chat_service


_stdio_session_id: ContextVar[str | None] = ContextVar(
    "mcp_stdio_session_id",
    default=None,
)
logger = logging.getLogger(__name__)
mcp = FastMCP("Investment Portfolio Tracker RAG")


def _canonical_conversation_id(value: str) -> str:
    try:
        return str(UUID((value or "").strip()))
    except (AttributeError, ValueError) as exc:
        raise ToolError("Conversation not found or not authorized.") from exc


def _session_id_from_context(context: Context) -> str | None:
    try:
        request = context.request_context.request
    except ValueError:
        request = None
    if request is not None and hasattr(request, "query_params"):
        session_id = request.headers.get("mcp-session-id")
        if session_id:
            return str(session_id)
        session_id = request.query_params.get("session_id")
        if session_id:
            return str(session_id)
    return _stdio_session_id.get()


def _require_session(context: Context) -> MCPSession:
    session_id = _session_id_from_context(context)
    session = session_manager.get(session_id) if session_id else None
    if not session:
        raise ToolError("The MCP session is unavailable or has expired.")
    return session


@mcp.tool()
def list_conversations(ctx: Context) -> list[dict]:
    """List public conversation summaries owned by the authenticated MCP user."""

    session = _require_session(ctx)
    return chat_service.list_conversations(session.user_id)


@mcp.tool()
def select_conversation(conversation_id: str, ctx: Context) -> str:
    """Select an owned conversation for subsequent MCP document searches."""

    session = _require_session(ctx)
    public_id = _canonical_conversation_id(conversation_id)
    chat = chat_service.get_chat_by_conversation_id(public_id, session.user_id)
    if not chat:
        raise ToolError("Conversation not found or not authorized.")

    session_manager.select_conversation(
        session.session_id,
        session.user_id,
        public_id,
    )
    logger.info(
        "mcp.conversation.selected session_id=%s user_id=%s conversation_id=%s",
        session.session_id,
        session.user_id,
        public_id,
    )
    title = chat["title"] or "Untitled conversation"
    return f"Selected conversation {public_id}: {title}"


@mcp.tool()
def search_uploaded_documents(query: str, ctx: Context) -> str:
    """Search documents in the authenticated session's selected conversation."""

    query_text = (query or "").strip()
    if not query_text:
        return "No document query was provided."

    session = _require_session(ctx)
    if not session.active_conversation_id:
        raise ToolError("Select a conversation before searching uploaded documents.")

    chat = chat_service.get_chat_by_conversation_id(
        session.active_conversation_id,
        session.user_id,
    )
    if not chat:
        raise ToolError("Conversation not found or not authorized.")

    chunks = retrieve_relevant_chunks(
        query_text,
        session.user_id,
        int(chat["chat_id"]),
        limit=8,
    )
    if not chunks:
        return (
            "No relevant uploaded document evidence was found for the query: "
            f"{query_text!r}."
        )

    return "\n".join(
        [
            f"Document search results for: {query_text}",
            format_document_chunks(chunks),
        ]
    )


def create_server() -> FastMCP:
    """Return the singleton server whose tools are shared by all transports."""

    return mcp


def bind_stdio_session(session_id: str):
    """Bind a trusted local STDIO session for the lifetime of the server."""

    return _stdio_session_id.set(session_id)


def reset_stdio_session(token) -> None:
    _stdio_session_id.reset(token)

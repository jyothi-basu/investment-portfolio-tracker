"""Single registry for shared AI and MCP business tools."""

from collections.abc import Callable
from dataclasses import dataclass
import json
import logging

from mcp.server.fastmcp import Context

from app.ai.context import get_trusted_chat_id, get_trusted_user_id

from .application import get_application_help
from .common import ToolExecutionResult, json_content
from .documents import search_uploaded_documents, search_uploaded_documents_for_context
from .portfolio import (
    PORTFOLIO_ASSISTANT_TOOLS,
    get_demat_accounts_for_user,
    get_holdings_for_user,
    get_portfolio_summary_for_user,
    get_stock_prices_for_user,
    get_transactions_for_user,
)

logger = logging.getLogger(__name__)

SHARED_TOOL_NAMES = (
    "get_portfolio_summary",
    "get_holdings",
    "get_transactions",
    "get_stock_prices",
    "get_demat_accounts",
    "search_uploaded_documents",
    "get_application_help",
)


@dataclass(frozen=True)
class ToolSpec:
    """Backend-owned execution policy for one registered assistant tool."""

    name: str
    handler: Callable
    category: str
    read_only: bool
    parallel_safe: bool
    retryable: bool

_ASSISTANT_TOOLS = (
    *PORTFOLIO_ASSISTANT_TOOLS,
    search_uploaded_documents,
    get_application_help,
)


def _assistant_result(tool, args):
    value = tool.invoke(args)
    content = value if isinstance(value, str) else json_content(value)
    citations = []
    if tool.name == "search_uploaded_documents":
        try:
            citations = json.loads(content).get("citations", [])
        except (TypeError, ValueError, AttributeError):
            pass
    return ToolExecutionResult(content=content, citations=citations)


_TOOL_POLICIES = {
    "get_portfolio_summary": ("portfolio", True, True, True),
    "get_holdings": ("portfolio", True, True, True),
    "get_transactions": ("portfolio", True, True, True),
    "get_stock_prices": ("portfolio", True, True, True),
    "get_demat_accounts": ("portfolio", True, True, True),
    "search_uploaded_documents": ("documents", True, True, True),
    "get_application_help": ("application", True, True, False),
}


TOOL_REGISTRY: dict[str, ToolSpec] = {
    tool.name: ToolSpec(
        name=tool.name,
        handler=lambda args, tool=tool: _assistant_result(tool, args),
        category=_TOOL_POLICIES[tool.name][0],
        read_only=_TOOL_POLICIES[tool.name][1],
        parallel_safe=_TOOL_POLICIES[tool.name][2],
        retryable=_TOOL_POLICIES[tool.name][3],
    )
    for tool in _ASSISTANT_TOOLS
}


def get_tool_spec(tool_name):
    """Return the trusted execution specification for a shared tool."""

    spec = TOOL_REGISTRY.get(tool_name)
    if spec is None:
        raise ValueError(f"Unknown tool requested by the model: {tool_name}")
    return spec


def get_assistant_tools():
    """Return all seven shared tools for LangChain tool binding."""

    return list(_ASSISTANT_TOOLS)


def execute_tool_call(tool_name, tool_args=None):
    """Execute a model-selected tool using trusted request context."""

    executor = get_tool_spec(tool_name).handler
    try:
        return executor(tool_args if isinstance(tool_args, dict) else {})
    except Exception:
        logger.exception("assistant tool execution failed name=%s", tool_name)
        raise


def get_mcp_tool_adapters(session_resolver, retrieve_fn=None):
    """Return MCP adapters using authenticated session identity.

    The resolver is supplied by the MCP transport and returns its trusted
    session. No identity values are present in any tool schema.
    """

    def session_user_id(ctx):
        return session_resolver(ctx).user_id

    def get_portfolio_summary(ctx: Context):
        return get_portfolio_summary_for_user(session_user_id(ctx))

    def get_holdings(ctx: Context):
        return get_holdings_for_user(session_user_id(ctx))

    def get_transactions(ctx: Context):
        return get_transactions_for_user(session_user_id(ctx))

    def get_stock_prices(ctx: Context):
        return get_stock_prices_for_user(session_user_id(ctx))

    def get_demat_accounts(ctx: Context):
        return get_demat_accounts_for_user(session_user_id(ctx))

    def search_documents(query: str, ctx: Context, limit: int = 8):
        session = session_resolver(ctx)
        if not session.active_conversation_id:
            raise ValueError("Select a conversation before searching uploaded documents.")
        from app.services import chat_service

        chat = chat_service.get_chat_by_conversation_id(
            session.active_conversation_id,
            session.user_id,
        )
        if not chat:
            raise ValueError("Conversation not found or not authorized.")
        return search_uploaded_documents_for_context(
            query,
            session.user_id,
            int(chat["chat_id"]),
            limit=limit,
            retrieve_fn=retrieve_fn,
        )

    def application_help(query: str = "", ctx: Context = None):
        return get_application_help.invoke({"query": query})

    return {
        "get_portfolio_summary": get_portfolio_summary,
        "get_holdings": get_holdings,
        "get_transactions": get_transactions,
        "get_stock_prices": get_stock_prices,
        "get_demat_accounts": get_demat_accounts,
        "search_uploaded_documents": search_documents,
        "get_application_help": application_help,
    }

"""LangChain tools for trusted portfolio, document, and app-help access.

The decorated tool functions are the model-facing surface. Each tool reads the
authenticated user and active chat from request-scoped context, so the LLM never
gets to choose user_id or chat_id. The helpers return read-only evidence that the
orchestrator can pass back into the model and, when relevant, cite in the final
response.
"""

from dataclasses import dataclass, field
from typing import Callable

from langchain_core.tools import tool

from app.ai.app_help import build_application_help
from app.ai.context import get_trusted_chat_id, get_trusted_user_id
from app.ai.prompts import build_document_citation, format_document_chunks, format_portfolio_context
from app.ai.rag.retriever import retrieve_relevant_chunks
from app.services import portfolio_service


@dataclass(frozen=True)
class ToolExecutionResult:
    """Structured tool output used by the orchestrator and final citations."""

    content: str
    citations: list[str] = field(default_factory=list)


def _require_context():
    """Read the trusted request scope for tool execution."""

    return get_trusted_user_id(), get_trusted_chat_id()


def _dedupe_preserve_order(items):
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _build_portfolio_result():
    user_id, _ = _require_context()
    summary = portfolio_service.calculate_portfolio_summary(user_id)
    holdings = portfolio_service.calculate_holdings_by_symbol(user_id)
    content = format_portfolio_context(summary, holdings)
    return ToolExecutionResult(content=content)


def _build_document_search_result(query, limit=8):
    user_id, chat_id = _require_context()
    query_text = (query or "").strip()
    if not query_text:
        return ToolExecutionResult(content="No document query was provided.")

    safe_limit = max(1, min(int(limit or 8), 8))
    chunks = retrieve_relevant_chunks(query_text, user_id, chat_id, limit=safe_limit)
    if not chunks:
        return ToolExecutionResult(
            content=(
                f"No relevant uploaded document evidence was found for the query: {query_text!r}."
            )
        )

    content = "\n".join(
        [
            f"Document search results for: {query_text}",
            format_document_chunks(chunks),
        ]
    )
    citations = _dedupe_preserve_order(
        [build_document_citation(chunk.get("metadata")) for chunk in chunks]
    )
    return ToolExecutionResult(content=content, citations=citations)


def _build_application_help_result(query=""):
    content = build_application_help(query=query)
    return ToolExecutionResult(content=content)


@tool("get_portfolio_information")
def get_portfolio_information() -> str:
    """Return the authenticated user's exact portfolio snapshot and holdings."""

    return _build_portfolio_result().content


@tool("search_uploaded_documents")
def search_uploaded_documents(query: str, limit: int = 8) -> str:
    """Search the current chat's uploaded documents for evidence relevant to query."""

    return _build_document_search_result(query=query, limit=limit).content


@tool("get_application_help")
def get_application_help(query: str = "") -> str:
    """Return application-usage guidance for questions about how to use the app."""

    return _build_application_help_result(query=query).content


TOOL_REGISTRY: dict[str, Callable[..., ToolExecutionResult]] = {
    "get_portfolio_information": lambda **_: _build_portfolio_result(),
    "search_uploaded_documents": lambda **kwargs: _build_document_search_result(
        query=kwargs.get("query", ""),
        limit=kwargs.get("limit", 8),
    ),
    "get_application_help": lambda **kwargs: _build_application_help_result(
        query=kwargs.get("query", "")
    ),
}


def get_assistant_tools():
    """Return the LangChain tool objects exposed to the model."""

    return [get_portfolio_information, search_uploaded_documents, get_application_help]


def execute_tool_call(tool_name, tool_args=None):
    """Execute a model-selected tool using trusted request context."""

    executor = TOOL_REGISTRY.get(tool_name)
    if executor is None:
        raise ValueError(f"Unknown tool requested by the model: {tool_name}")
    if not isinstance(tool_args, dict):
        tool_args = {}
    try:
        return executor(**tool_args)
    except Exception as exc:
        print(f"[assistant-tool-error] {tool_name} failed: {exc!r}")
        raise

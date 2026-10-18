"""Production LangGraph nodes for the portfolio assistant."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage
from sqlalchemy.exc import OperationalError

from app.ai.provider_factory import build_chat_model, get_chat_provider_settings
from app.ai.prompts import format_citations
from app.ai.tools import ToolExecutionResult, execute_tool_call, get_assistant_tools, get_tool_spec
from app.services import chat_service
from app.services.chat_title_service import generate_title_if_needed

from .state import PortfolioAssistantState

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4.1-mini"
MAX_RESPONSE_TOKENS = 300
MAX_TOOL_ROUNDS = 4


def _message_content(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )
    return str(content or "")


def _latest_user_message(messages) -> str:
    for message in reversed(messages or []):
        if isinstance(message, HumanMessage):
            return _message_content(message)
    return ""


def _normalise_tool_call(tool_call: Any) -> dict[str, Any]:
    if isinstance(tool_call, dict):
        return {"name": tool_call.get("name"), "args": tool_call.get("args") or {}, "id": tool_call.get("id")}
    return {"name": getattr(tool_call, "name", None), "args": getattr(tool_call, "args", {}) or {}, "id": getattr(tool_call, "id", None)}


def _append_citations(answer: str, citations: list[str]) -> str:
    deduped = list(dict.fromkeys(str(item).strip() for item in citations if str(item).strip()))
    if not deduped or "\n\nSources:\n" in answer:
        return answer
    citation_block = format_citations(deduped)
    return f"{answer.rstrip()}\n\n{citation_block}" if citation_block else answer


def agent_node(state: PortfolioAssistantState) -> dict[str, Any]:
    """Invoke the model using only conversation messages and tool schemas.

    Trusted identity, provider configuration, and backend metadata remain
    server-side graph state and are never included in prompt messages. This
    node selects tools or produces a final response; it never executes tools.
    """

    settings = get_chat_provider_settings(default_model=DEFAULT_MODEL)
    model = build_chat_model(default_model=DEFAULT_MODEL, temperature=0.4, max_tokens=MAX_RESPONSE_TOKENS)
    response = model.bind_tools(get_assistant_tools()).invoke(state.get("messages", []))
    tool_calls = [_normalise_tool_call(call) for call in (getattr(response, "tool_calls", None) or [])]
    if tool_calls and (state.get("tool_rounds") or 0) >= MAX_TOOL_ROUNDS:
        raise RuntimeError("The assistant could not complete the request after multiple tool calls.")
    if tool_calls:
        return {"messages": [response], "provider": state.get("provider") or settings.provider, "tool_calls": tool_calls, "assistant_response": None}

    citations = [citation for result in state.get("tool_results") or [] for citation in result.get("citations", [])]
    response.content = _append_citations(_message_content(response), citations)
    return {"messages": [response], "provider": state.get("provider") or settings.provider, "tool_calls": [], "assistant_response": response}


def _is_transient_failure(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError, OSError, OperationalError)):
        return True
    return exc.__class__.__name__ in {"TimeoutException", "ConnectError", "ReadError", "TemporaryFailure"}


def _execute_tool(tool_call: dict[str, Any], retryable: bool) -> dict[str, Any]:
    tool_name = tool_call.get("name")
    tool_id = tool_call.get("id") or f"{tool_name}-call"
    attempts = 2 if retryable else 1
    last_error = None
    for attempt in range(attempts):
        try:
            result = execute_tool_call(tool_name, tool_call.get("args") or {})
            if isinstance(result, ToolExecutionResult):
                content, citations = result.content, result.citations
            else:
                content, citations = str(result), []
            return {"tool_call_id": tool_id, "name": tool_name, "status": "completed", "content": content, "citations": citations}
        except Exception as exc:
            last_error = exc
            if attempt + 1 >= attempts or not _is_transient_failure(exc):
                break
            logger.warning("Retrying transient tool failure name=%s", tool_name)
    return {"tool_call_id": tool_id, "name": tool_name, "status": "error", "content": json.dumps({"error": f"Tool execution failed: {last_error}"}), "citations": []}


def _execute_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    specs = []
    for call in tool_calls:
        try:
            specs.append(get_tool_spec(call.get("name")))
        except Exception as exc:
            specs.append(exc)

    results: list[dict[str, Any]] = []
    index = 0
    while index < len(tool_calls):
        spec = specs[index]
        if isinstance(spec, Exception):
            results.append({"tool_call_id": tool_calls[index].get("id"), "name": tool_calls[index].get("name"), "status": "error", "content": json.dumps({"error": str(spec)}), "citations": []})
            index += 1
            continue
        if spec.parallel_safe:
            end = index
            while end < len(tool_calls) and not isinstance(specs[end], Exception) and specs[end].parallel_safe:
                end += 1
            work = [
                (
                    tool_calls[pos],
                    specs[pos].retryable,
                    copy_context(),
                )
                for pos in range(index, end)
            ]

            def execute_in_context(item):
                tool_call, retryable, context = item
                return context.run(_execute_tool, tool_call, retryable)

            with ThreadPoolExecutor(max_workers=end - index) as executor:
                results.extend(
                    executor.map(execute_in_context, work)
                )
            index = end
        else:
            results.append(_execute_tool(tool_calls[index], spec.retryable))
            index += 1
    return results


def tool_executor_node(state: PortfolioAssistantState) -> dict[str, Any]:
    """Execute registered tools and append ordered ToolMessages.

    Scheduling, retryability, and parallel safety come only from trusted
    registry metadata. Tool output is temporary execution state and is never
    persisted as a chat message.
    """

    tool_calls = state.get("tool_calls") or []
    results = _execute_tool_calls(tool_calls)
    return {
        "messages": [ToolMessage(content=result["content"], tool_call_id=result["tool_call_id"]) for result in results],
        "tool_results": [*(state.get("tool_results") or []), *results],
        "tool_calls": [],
        "tool_rounds": (state.get("tool_rounds") or 0) + 1,
    }


def conversation_title_node(state: PortfolioAssistantState) -> dict[str, Any]:
    """Generate a title once through the existing title service only."""

    metadata = state.get("metadata") or {}
    message = metadata.get("user_message") or _latest_user_message(state.get("messages", []))
    generated = generate_title_if_needed(state["chat_id"], state["user_id"], message)
    return {"conversation_title_generated": bool(state.get("conversation_title_generated") or generated)}


def persistence_node(state: PortfolioAssistantState) -> dict[str, Any]:
    """Persist only user/assistant messages and the chat timestamp.

    ToolMessages, tool calls, tool results, and execution metadata are never
    written to the configured relational database.
    """

    metadata = state.get("metadata") or {}
    user_message = metadata.get("user_message") or _latest_user_message(state.get("messages", []))
    if user_message and not metadata.get("user_message_persisted"):
        chat_service.add_user_message(state["chat_id"], user_message)
    assistant_response = state.get("assistant_response")
    if assistant_response:
        chat_service.add_assistant_message(state["chat_id"], _message_content(assistant_response))
    chat_service.touch_chat(state["chat_id"])
    return {"metadata": {**metadata, "user_message_persisted": True}}

"""LangGraph nodes kept separate from the production LangChain assistant."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from app.ai.provider_factory import build_chat_model, get_chat_provider_settings
from app.ai.tools import get_assistant_tools
from app.services import chat_service
from app.services.chat_title_service import generate_title_if_needed

from .state import PortfolioAssistantState


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
        return {
            "name": tool_call.get("name"),
            "args": tool_call.get("args") or {},
            "id": tool_call.get("id"),
        }
    return {
        "name": getattr(tool_call, "name", None),
        "args": getattr(tool_call, "args", {}) or {},
        "id": getattr(tool_call, "id", None),
    }


def agent_node(state: PortfolioAssistantState) -> dict[str, Any]:
    """Invoke the provider using only conversation messages and tool schemas.

    Trusted identity, provider settings, and backend metadata remain in graph
    state and are never included in the prompt sent to the model. The model
    receives only the conversation ``messages`` and the schemas returned by
    the shared tool registry. This node selects tools or produces a final
    ``AIMessage``; it does not execute tools.
    """

    settings = get_chat_provider_settings()
    model = build_chat_model()
    response = model.bind_tools(get_assistant_tools()).invoke(state.get("messages", []))
    tool_calls = [
        _normalise_tool_call(tool_call)
        for tool_call in (getattr(response, "tool_calls", None) or [])
    ]
    assistant_response = response if not tool_calls else None
    return {
        "messages": [response],
        "provider": state.get("provider") or settings.provider,
        "tool_calls": tool_calls,
        "assistant_response": assistant_response,
        "tool_results": [],
    }


def tool_executor_node(state: PortfolioAssistantState) -> dict[str, Any]:
    """Record tool-call execution slots without executing business tools.

    Actual shared-registry execution is intentionally deferred to Commit 2.
    This node preserves every requested call ID and arguments in execution
    state only; it does not create prompt messages, touch trusted context, or
    persist anything.
    """

    tool_calls = state.get("tool_calls") or []
    tool_results = [
        {
            "tool_call_id": tool_call.get("id"),
            "name": tool_call.get("name"),
            "args": tool_call.get("args") or {},
            "status": "pending",
        }
        for tool_call in tool_calls
    ]
    return {
        "tool_results": tool_results,
    }


def conversation_title_node(state: PortfolioAssistantState) -> dict[str, Any]:
    """Apply the existing delayed-title behavior exactly once.

    Greeting-only messages and chats that already have a title are ignored by
    the existing title service. This node owns title-generation timing; it
    returns only title-related graph state and does not persist messages.
    """

    metadata = state.get("metadata") or {}
    message = metadata.get("user_message") or _latest_user_message(state.get("messages", []))
    generated = generate_title_if_needed(
        state["chat_id"],
        state["user_id"],
        message,
    )
    return {
        "conversation_title_generated": bool(
            state.get("conversation_title_generated") or generated
        )
    }


def persistence_node(state: PortfolioAssistantState) -> dict[str, Any]:
    """Persist the durable conversation boundary only.

    The eventual SQLite writes are limited to the user message, assistant
    message, chat timestamp, and title update performed by the title service.
    Tool calls, tool results, and all other execution metadata remain graph
    state and are never persisted.
    """

    metadata = state.get("metadata") or {}
    user_message = metadata.get("user_message") or _latest_user_message(
        state.get("messages", [])
    )
    if user_message and not metadata.get("user_message_persisted"):
        chat_service.add_user_message(state["chat_id"], user_message)

    assistant_response = state.get("assistant_response")
    if assistant_response:
        chat_service.add_assistant_message(
            state["chat_id"],
            _message_content(assistant_response),
        )
    chat_service.touch_chat(state["chat_id"])
    return {"metadata": {**metadata, "user_message_persisted": True}}

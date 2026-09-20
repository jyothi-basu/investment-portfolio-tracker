"""Backend-owned state for the future portfolio assistant graph.

Trusted conversation fields describe the lifetime of a graph run and are
available to backend nodes. Execution-only fields describe one pass through
the graph and are intentionally excluded from persistence. In particular,
``user_id`` and ``chat_id`` are routing/authorization data; they must never be
copied into prompt messages.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, ToolCall
from langgraph.graph.message import add_messages


class PortfolioAssistantState(TypedDict, total=False):
    """Trusted conversation state and execution-local graph state.

    ``user_id`` and ``chat_id`` are backend-owned routing data. They are never
    copied into prompt messages by the graph nodes.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    user_id: int
    chat_id: int
    provider: str
    conversation_title_generated: bool
    metadata: dict[str, Any]

    # Execution-only values. These are populated during one graph run and are
    # intentionally not persisted by the persistence node.
    tool_calls: list[ToolCall] | None
    tool_results: list[dict[str, Any]] | None
    assistant_response: AIMessage | None

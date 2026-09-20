"""Routing decisions for the isolated portfolio assistant graph."""

from .state import PortfolioAssistantState


def route_after_agent(state: PortfolioAssistantState) -> str:
    """Route tool-producing responses to execution, otherwise to title work."""

    return "tool_executor" if state.get("tool_calls") else "conversation_title"


def route_after_tool_executor(state: PortfolioAssistantState) -> str:
    """Always return to the agent after tool execution."""

    return "agent"

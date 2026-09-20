"""Builder for the future portfolio assistant StateGraph."""

from langgraph.graph import END, START, StateGraph

from .edges import route_after_agent, route_after_tool_executor
from .nodes import (
    agent_node,
    conversation_title_node,
    persistence_node,
    tool_executor_node,
)
from .state import PortfolioAssistantState


def build_portfolio_graph():
    """Compile the isolated four-node portfolio assistant graph."""

    workflow = StateGraph(PortfolioAssistantState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tool_executor", tool_executor_node)
    workflow.add_node("conversation_title", conversation_title_node)
    workflow.add_node("persistence", persistence_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "tool_executor": "tool_executor",
            "conversation_title": "conversation_title",
        },
    )
    workflow.add_conditional_edges(
        "tool_executor",
        route_after_tool_executor,
        {"agent": "agent"},
    )
    workflow.add_edge("conversation_title", "persistence")
    workflow.add_edge("persistence", END)
    return workflow.compile()

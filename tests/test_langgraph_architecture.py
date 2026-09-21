"""Unit tests for LangGraph orchestration without database access."""

from threading import Barrier
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

import app.ai.langgraph.nodes as nodes
from app.ai.langgraph.edges import route_after_agent, route_after_tool_executor
from app.ai.langgraph.graph import build_portfolio_graph
from app.ai.tools import ToolExecutionResult


class TestLangGraphArchitecture:
    def test_graph_contains_expected_nodes_and_routes(self):
        graph = build_portfolio_graph()
        assert {name for name in graph.get_graph().nodes if not name.startswith("__")} == {
            "agent",
            "tool_executor",
            "conversation_title",
            "persistence",
        }
        assert route_after_agent({"tool_calls": [{"name": "get_holdings"}]}) == "tool_executor"
        assert route_after_agent({"tool_calls": []}) == "conversation_title"
        assert route_after_tool_executor({}) == "agent"

    def test_agent_prompt_contains_only_conversation_messages(self):
        response = AIMessage(content="Final answer")
        model = Mock()
        model.bind_tools.return_value.invoke.return_value = response
        captured = {}

        def invoke(messages):
            captured["messages"] = messages
            return response

        model.bind_tools.return_value.invoke.side_effect = invoke
        with patch.object(nodes, "get_chat_provider_settings", return_value=Mock(provider="openai")), \
                patch.object(nodes, "build_chat_model", return_value=model), \
                patch.object(nodes, "get_assistant_tools", return_value=[]):
            result = nodes.agent_node(
                {
                    "messages": [HumanMessage(content="How many shares do I own?")],
                    "user_id": 42,
                    "chat_id": 99,
                    "provider": "secret-provider-config",
                    "metadata": {"internal": "must not be prompted"},
                    "tool_rounds": 0,
                }
            )

        assert captured["messages"] == [HumanMessage(content="How many shares do I own?")]
        assert "42" not in repr(captured["messages"])
        assert "99" not in repr(captured["messages"])
        assert result["assistant_response"] is response

    def test_independent_tools_execute_concurrently_and_keep_order(self):
        barrier = Barrier(2)

        def execute(name, args):
            barrier.wait(timeout=2)
            return ToolExecutionResult(content=name, citations=[])

        with patch.object(nodes, "execute_tool_call", side_effect=execute):
            result = nodes.tool_executor_node(
                {
                    "tool_calls": [
                        {"name": "get_holdings", "args": {}, "id": "first"},
                        {"name": "get_transactions", "args": {}, "id": "second"},
                    ],
                    "tool_results": [],
                    "tool_rounds": 0,
                }
            )

        assert [message.tool_call_id for message in result["messages"]] == ["first", "second"]
        assert [message.content for message in result["messages"]] == ["get_holdings", "get_transactions"]

    def test_unknown_tool_isolated_as_structured_tool_message(self):
        with patch.object(nodes, "execute_tool_call") as execute:
            result = nodes.tool_executor_node(
                {
                    "tool_calls": [{"name": "unknown_tool", "args": {}, "id": "bad-call"}],
                    "tool_results": [],
                    "tool_rounds": 0,
                }
            )

        execute.assert_not_called()
        assert result["messages"][0].tool_call_id == "bad-call"
        assert "Unknown tool" in result["messages"][0].content

    def test_retryable_tool_retries_once_but_validation_error_does_not(self):
        transient = Mock(side_effect=[TimeoutError("temporary"), ToolExecutionResult("ok", [])])
        with patch.object(nodes, "execute_tool_call", transient):
            result = nodes.tool_executor_node(
                {
                    "tool_calls": [{"name": "get_holdings", "args": {}, "id": "retry"}],
                    "tool_results": [],
                    "tool_rounds": 0,
                }
            )
        assert transient.call_count == 2
        assert result["messages"][0].content == "ok"

        invalid = Mock(side_effect=ValueError("invalid input"))
        with patch.object(nodes, "execute_tool_call", invalid):
            result = nodes.tool_executor_node(
                {
                    "tool_calls": [{"name": "get_application_help", "args": {}, "id": "no-retry"}],
                    "tool_results": [],
                    "tool_rounds": 0,
                }
            )
        assert invalid.call_count == 1
        assert result["messages"][0].tool_call_id == "no-retry"

    def test_persistence_ignores_tool_messages_and_execution_metadata(self):
        with patch.object(nodes, "generate_title_if_needed", return_value=None), \
                patch.object(nodes.chat_service, "add_user_message") as add_user, \
                patch.object(nodes.chat_service, "add_assistant_message") as add_assistant, \
                patch.object(nodes.chat_service, "touch_chat") as touch:
            nodes.persistence_node(
                {
                    "chat_id": 9,
                    "metadata": {"user_message": "Show holdings"},
                    "messages": [ToolMessage(content="internal", tool_call_id="tool-1")],
                    "assistant_response": AIMessage(content="You hold 10 shares."),
                    "tool_calls": [{"name": "get_holdings"}],
                    "tool_results": [{"content": "internal"}],
                }
            )

        add_user.assert_called_once_with(9, "Show holdings")
        add_assistant.assert_called_once_with(9, "You hold 10 shares.")
        touch.assert_called_once_with(9)

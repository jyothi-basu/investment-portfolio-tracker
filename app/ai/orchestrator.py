"""Request-level orchestration for the production LangGraph assistant."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.ai.context import push_assistant_context
from app.ai.langgraph import build_portfolio_graph
from app.ai.prompts import PROJECT_ASSISTANT_SYSTEM_PROMPT


class ChatServiceError(RuntimeError):
    """Raised when the assistant cannot complete a request safely."""


def _build_messages(user_message, history=None):
    messages = [SystemMessage(content=PROJECT_ASSISTANT_SYSTEM_PROMPT)]
    for item in history or []:
        role = (item.get("role") or "").strip().lower()
        content = (item.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=user_message.strip()))
    return messages


def _message_text(content):
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ).strip()
    return str(content or "").strip()


def generate_chat_response(user_message, user_id, chat_id, history=None):
    """Run the compiled graph inside trusted user/chat context."""

    initial_state = {
        "messages": _build_messages(user_message, history=history),
        "user_id": user_id,
        "chat_id": chat_id,
        "conversation_title_generated": False,
        "metadata": {"user_message": user_message.strip()},
        "tool_calls": None,
        "tool_results": None,
        "assistant_response": None,
        "tool_rounds": 0,
    }
    try:
        with push_assistant_context(user_id=user_id, chat_id=chat_id):
            state = build_portfolio_graph().invoke(
                initial_state,
                config={"recursion_limit": 16},
            )
    except ChatServiceError:
        raise
    except Exception as exc:
        raise ChatServiceError("Unable to complete the assistant request right now.") from exc

    response = state.get("assistant_response")
    answer = _message_text(getattr(response, "content", response))
    if not answer:
        raise ChatServiceError("AI provider returned an empty response.")
    return answer

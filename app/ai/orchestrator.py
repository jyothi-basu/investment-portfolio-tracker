"""Request-level orchestration for trusted assistant tool execution."""

from app.ai.chat import get_chat_response
from app.ai.context import push_assistant_context


def generate_chat_response(user_message, user_id, chat_id, history=None):
    """Generate a chat response using a trusted user/chat tool context."""

    with push_assistant_context(user_id=user_id, chat_id=chat_id):
        return get_chat_response(user_message=user_message, history=history)

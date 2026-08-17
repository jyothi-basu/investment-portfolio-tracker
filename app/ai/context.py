"""Request-scoped assistant context for trusted user and chat access.

This module keeps user_id and chat_id out of model-controlled tool parameters.
The Flask route or orchestration layer sets the trusted context once per request,
and the tool implementations read it internally when they need portfolio or RAG
data.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class AssistantRequestContext:
    """Trusted request context for assistant tool execution."""

    user_id: int
    chat_id: int


_ASSISTANT_CONTEXT: ContextVar[AssistantRequestContext | None] = ContextVar(
    "assistant_request_context",
    default=None,
)


@contextmanager
def push_assistant_context(user_id, chat_id):
    """Bind the authenticated user and active chat for the current request."""

    token = _ASSISTANT_CONTEXT.set(AssistantRequestContext(user_id=user_id, chat_id=chat_id))
    try:
        yield _ASSISTANT_CONTEXT.get()
    finally:
        _ASSISTANT_CONTEXT.reset(token)


def get_assistant_context():
    """Return the trusted request context or raise if tool execution is unbound."""

    context = _ASSISTANT_CONTEXT.get()
    if context is None:
        raise RuntimeError("Assistant tool context has not been initialized.")
    return context


def get_trusted_user_id():
    """Return the authenticated user_id for tool execution."""

    return get_assistant_context().user_id


def get_trusted_chat_id():
    """Return the active chat_id for tool execution."""

    return get_assistant_context().chat_id

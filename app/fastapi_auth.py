"""FastAPI authentication and trusted request-context helpers.

This module mirrors the existing Flask trust boundary for the migration layer.
It reads authenticated user state from server-side session data, validates the
active chat, and binds the assistant request context so downstream tools can
access trusted `user_id` and `chat_id` without exposing them to the model.
"""

from __future__ import annotations

from contextlib import contextmanager

from fastapi import HTTPException, Request, status

from app.ai.context import AssistantRequestContext, push_assistant_context


def _read_session_int(request: Request, key: str):
    value = request.session.get(key)
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_authenticated_user_id(request: Request) -> int:
    """Return the trusted authenticated user_id from the session."""

    user_id = _read_session_int(request, "user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in to continue.",
        )
    return user_id


def get_active_chat_id(request: Request):
    """Return the trusted active chat_id from the session if available."""

    return _read_session_int(request, "active_chat_id")


def get_trusted_request_context(request: Request) -> AssistantRequestContext:
    """Return the authenticated user/chat context required by assistant tools."""

    user_id = get_authenticated_user_id(request)
    chat_id = get_active_chat_id(request)
    if chat_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active chat is required for assistant requests.",
        )
    return AssistantRequestContext(user_id=user_id, chat_id=chat_id)


@contextmanager
def bind_trusted_request_context(request: Request):
    """Bind trusted assistant context for the duration of a FastAPI request."""

    context = get_trusted_request_context(request)
    with push_assistant_context(user_id=context.user_id, chat_id=context.chat_id):
        yield context

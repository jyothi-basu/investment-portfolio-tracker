"""Generate permanent conversation titles after the first meaningful message."""

from __future__ import annotations

import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.provider_factory import build_chat_model
from app.repository import db


logger = logging.getLogger(__name__)

GREETING_PHRASES = {
    "good afternoon",
    "good evening",
    "good morning",
    "hello",
    "hey",
    "hi",
    "ok",
    "okay",
    "thanks",
    "thank you",
}
GREETING_WORDS = {
    "afternoon",
    "evening",
    "good",
    "hello",
    "hey",
    "hi",
    "morning",
    "ok",
    "okay",
    "thank",
    "thanks",
    "there",
    "you",
}


def is_greeting_only(message: str) -> bool:
    """Return whether a message contains only a greeting or acknowledgement."""

    normalized = re.sub(r"[^a-z0-9\s]", " ", (message or "").lower())
    normalized = " ".join(normalized.split())
    return (
        not normalized
        or normalized in GREETING_PHRASES
        or set(normalized.split()).issubset(GREETING_WORDS)
    )


def _message_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )
    return str(content or "")


def _normalize_title(raw_title: str, message: str) -> str:
    first_line = raw_title.strip().splitlines()[0] if raw_title.strip() else ""
    cleaned = re.sub(r"^[\s\"']+|[\s\"']+$", "", first_line)
    cleaned = re.sub(r"^(title\s*:\s*)", "", cleaned, flags=re.IGNORECASE)
    words = cleaned.split()[:6]
    if not words:
        words = re.findall(r"[A-Za-z0-9][A-Za-z0-9&+.'-]*", message)[:6]
    return " ".join(words)


def generate_title_if_needed(chat_id: int, user_id: int, message: str) -> str | None:
    """Generate a title once, leaving greeting-only and already-titled chats unchanged."""

    chat = db.fetch_chat(chat_id, user_id)
    if not chat or chat["title"] or is_greeting_only(message):
        return None

    try:
        model = build_chat_model(temperature=0, max_tokens=30)
        response = model.invoke(
            [
                SystemMessage(
                    content=(
                        "Create a concise conversation title of at most six words. "
                        "Return only the title, without quotes or punctuation."
                    )
                ),
                HumanMessage(content=message),
            ]
        )
        title = _normalize_title(_message_text(response.content), message)
        if title:
            db.update_chat_title_if_empty(chat_id, user_id, title)
            logger.info(
                "chat.title.generated chat_id=%s user_id=%s",
                chat_id,
                user_id,
            )
            return title
    except Exception:
        # Title generation must never prevent the user's chat request.
        logger.exception(
            "chat.title.generation_failed chat_id=%s user_id=%s",
            chat_id,
            user_id,
        )
    return None

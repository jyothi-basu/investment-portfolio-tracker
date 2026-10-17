"""SQLAlchemy repository for chats, messages, and normalized documents."""

from __future__ import annotations

from typing import Any
import uuid

from sqlalchemy import delete, func, select, update

from app.repository.models import Chat, ChatMessage, Document, utc_now
from app.repository.serialization import model_to_dict, row_to_dict
from app.repository.session import session_scope


CHAT_MESSAGE_ROLES = {"USER", "ASSISTANT"}
DOCUMENT_STATUSES = {"UPLOADED", "PROCESSING", "COMPLETED", "REJECTED", "FAILED"}


def _normalize_status(status: str) -> str:
    normalized = status.strip().upper() if status else ""
    if normalized not in DOCUMENT_STATUSES:
        raise ValueError("processing_status must be a valid document status")
    return normalized


def fetch_chats(user_id: int) -> list[dict[str, Any]]:
    with session_scope() as session:
        chats = session.scalars(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(Chat.updated_at.desc(), Chat.chat_id.desc())
        ).all()
        return [model_to_dict(chat) for chat in chats]


def fetch_chat(chat_id: int, user_id: int) -> dict[str, Any] | None:
    with session_scope() as session:
        chat = session.scalar(
            select(Chat).where(Chat.chat_id == chat_id, Chat.user_id == user_id)
        )
        return model_to_dict(chat) if chat is not None else None


def fetch_chat_by_conversation_id(
    conversation_id: str, user_id: int
) -> dict[str, Any] | None:
    with session_scope() as session:
        chat = session.scalar(
            select(Chat).where(
                Chat.conversation_id == conversation_id,
                Chat.user_id == user_id,
            )
        )
        return model_to_dict(chat) if chat is not None else None


def fetch_chat_by_conversation_id_unscoped(
    conversation_id: str,
) -> dict[str, Any] | None:
    with session_scope() as session:
        chat = session.scalar(
            select(Chat).where(Chat.conversation_id == conversation_id)
        )
        return model_to_dict(chat) if chat is not None else None


def fetch_conversation_summaries(user_id: int) -> list[dict[str, Any]]:
    last_message = (
        select(ChatMessage.content)
        .where(ChatMessage.chat_id == Chat.chat_id)
        .order_by(ChatMessage.message_id.desc())
        .limit(1)
        .correlate(Chat)
        .scalar_subquery()
    )
    with session_scope() as session:
        rows = session.execute(
            select(
                Chat.chat_id,
                Chat.conversation_id,
                Chat.title.label("chat_title"),
                Chat.updated_at,
                func.count(ChatMessage.message_id).label("message_count"),
                last_message.label("last_message"),
            )
            .outerjoin(ChatMessage, ChatMessage.chat_id == Chat.chat_id)
            .where(Chat.user_id == user_id)
            .group_by(Chat.chat_id, Chat.conversation_id, Chat.title, Chat.updated_at)
            .order_by(Chat.updated_at.desc(), Chat.chat_id.desc())
        ).all()
        return [row_to_dict(row) for row in rows]


def create_chat(user_id: int, title: str | None = None) -> int:
    with session_scope() as session:
        chat = Chat(
            conversation_id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
        )
        session.add(chat)
        session.flush()
        return chat.chat_id


def update_chat_title(chat_id: int, user_id: int, title: str) -> int:
    with session_scope() as session:
        result = session.execute(
            update(Chat)
            .where(Chat.chat_id == chat_id, Chat.user_id == user_id)
            .values(title=title, updated_at=utc_now())
        )
        return result.rowcount


def update_chat_title_if_empty(chat_id: int, user_id: int, title: str) -> int:
    with session_scope() as session:
        result = session.execute(
            update(Chat)
            .where(
                Chat.chat_id == chat_id,
                Chat.user_id == user_id,
                (Chat.title.is_(None) | (func.trim(Chat.title) == "")),
            )
            .values(title=title, updated_at=utc_now())
        )
        return result.rowcount


def touch_chat(chat_id: int) -> int:
    with session_scope() as session:
        result = session.execute(
            update(Chat).where(Chat.chat_id == chat_id).values(updated_at=utc_now())
        )
        return result.rowcount


def delete_chat(chat_id: int, user_id: int) -> int:
    with session_scope() as session:
        result = session.execute(
            delete(Chat).where(Chat.chat_id == chat_id, Chat.user_id == user_id)
        )
        return result.rowcount


def fetch_chat_messages(chat_id: int, user_id: int) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = session.execute(
            select(
                ChatMessage.message_id,
                ChatMessage.chat_id,
                ChatMessage.role,
                ChatMessage.content,
                ChatMessage.created_at,
            )
            .join(Chat, Chat.chat_id == ChatMessage.chat_id)
            .where(ChatMessage.chat_id == chat_id, Chat.user_id == user_id)
            .order_by(ChatMessage.message_id)
        ).all()
        return [row_to_dict(row) for row in rows]


def create_chat_message(chat_id: int, role: str, content: str) -> int:
    normalized_role = role.strip().upper() if role else ""
    if normalized_role not in CHAT_MESSAGE_ROLES:
        raise ValueError("role must be USER or ASSISTANT")
    with session_scope() as session:
        message = ChatMessage(chat_id=chat_id, role=normalized_role, content=content)
        session.add(message)
        session.flush()
        return message.message_id


def delete_chat_messages(chat_id: int) -> int:
    with session_scope() as session:
        result = session.execute(delete(ChatMessage).where(ChatMessage.chat_id == chat_id))
        return result.rowcount


def fetch_documents(user_id: int) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = session.execute(
            select(
                Document.document_id,
                Document.chat_id,
                Document.original_filename,
                Document.uploaded_at,
                Document.processing_status,
            )
            .join(Chat, Chat.chat_id == Document.chat_id)
            .where(Chat.user_id == user_id)
            .order_by(Document.uploaded_at.desc(), Document.document_id.desc())
        ).all()
        return [row_to_dict(row) for row in rows]


def fetch_documents_for_chat(chat_id: int, user_id: int) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = session.execute(
            select(
                Document.document_id,
                Document.chat_id,
                Document.original_filename,
                Document.uploaded_at,
                Document.processing_status,
            )
            .join(Chat, Chat.chat_id == Document.chat_id)
            .where(Document.chat_id == chat_id, Chat.user_id == user_id)
            .order_by(Document.uploaded_at.desc(), Document.document_id.desc())
        ).all()
        return [row_to_dict(row) for row in rows]


def fetch_document(document_id: int, user_id: int) -> dict[str, Any] | None:
    with session_scope() as session:
        row = session.execute(
            select(
                Document.document_id,
                Document.chat_id,
                Document.original_filename,
                Document.uploaded_at,
                Document.processing_status,
            )
            .join(Chat, Chat.chat_id == Document.chat_id)
            .where(Document.document_id == document_id, Chat.user_id == user_id)
        ).first()
        return row_to_dict(row) if row is not None else None


def create_document(
    chat_id: int,
    user_id: int,
    original_filename: str,
    processing_status: str = "UPLOADED",
) -> int:
    normalized_status = _normalize_status(processing_status)
    with session_scope() as session:
        chat = session.scalar(
            select(Chat).where(Chat.chat_id == chat_id, Chat.user_id == user_id)
        )
        if chat is None:
            raise ValueError("chat does not belong to user")
        document = Document(
            chat_id=chat_id,
            original_filename=original_filename,
            processing_status=normalized_status,
        )
        session.add(document)
        session.flush()
        return document.document_id


def update_document_status(document_id: int, user_id: int, processing_status: str) -> int:
    normalized_status = _normalize_status(processing_status)
    with session_scope() as session:
        document = session.scalar(
            select(Document)
            .join(Chat, Chat.chat_id == Document.chat_id)
            .where(Document.document_id == document_id, Chat.user_id == user_id)
        )
        if document is None:
            return 0
        document.processing_status = normalized_status
        session.flush()
        return 1


def delete_document(document_id: int, user_id: int) -> int:
    with session_scope() as session:
        document = session.scalar(
            select(Document)
            .join(Chat, Chat.chat_id == Document.chat_id)
            .where(Document.document_id == document_id, Chat.user_id == user_id)
        )
        if document is None:
            return 0
        session.delete(document)
        return 1

"""Tests for the isolated SQLAlchemy chat and document repositories."""

from __future__ import annotations

import pytest

from app.repository import database
from app.repository.auth_repository import create_user
from app.repository.chat_repository import (
    create_chat,
    create_chat_message,
    create_document,
    delete_chat,
    delete_chat_messages,
    delete_document,
    fetch_chat,
    fetch_chat_by_conversation_id,
    fetch_chat_by_conversation_id_unscoped,
    fetch_chat_messages,
    fetch_chats,
    fetch_conversation_summaries,
    fetch_document,
    fetch_documents,
    fetch_documents_for_chat,
    touch_chat,
    update_chat_title,
    update_chat_title_if_empty,
    update_document_status,
)
from app.repository.models import Base


@pytest.fixture
def chat_database(tmp_path):
    original_engine = database.engine
    original_factory = database.SessionLocal
    database.configure_database(f"sqlite:///{tmp_path / 'chat.db'}")
    Base.metadata.create_all(database.get_engine())
    try:
        yield
    finally:
        database.get_engine().dispose()
        database.engine = original_engine
        database.SessionLocal = original_factory


def test_chat_and_message_crud_is_user_scoped(chat_database):
    owner_id = create_user("Chat User", "chat@example.com", "hash")
    other_user_id = create_user("Other Chat User", "other-chat@example.com", "hash")
    chat_id = create_chat(owner_id, "Initial title")
    chat = fetch_chat(chat_id, owner_id)

    assert chat["title"] == "Initial title"
    assert fetch_chat(chat_id, other_user_id) is None
    assert fetch_chat_by_conversation_id(chat["conversation_id"], owner_id)["chat_id"] == chat_id
    assert fetch_chat_by_conversation_id_unscoped(chat["conversation_id"])["user_id"] == owner_id

    message_id = create_chat_message(chat_id, "USER", "Show my holdings")
    create_chat_message(chat_id, "ASSISTANT", "You hold ABC.")
    assert fetch_chat_messages(chat_id, owner_id)[0]["message_id"] == message_id
    assert fetch_chat_messages(chat_id, other_user_id) == []
    assert fetch_conversation_summaries(owner_id)[0]["message_count"] == 2
    assert fetch_conversation_summaries(owner_id)[0]["last_message"] == "You hold ABC."

    assert update_chat_title_if_empty(chat_id, owner_id, "Should not replace") == 0
    assert update_chat_title(chat_id, owner_id, "Updated title") == 1
    assert touch_chat(chat_id) == 1
    assert delete_chat_messages(chat_id) == 2
    assert fetch_chat_messages(chat_id, owner_id) == []


def test_document_crud_derives_ownership_from_chat(chat_database):
    owner_id = create_user("Document User", "document@example.com", "hash")
    other_user_id = create_user("Other Document User", "other-document@example.com", "hash")
    chat_id = create_chat(owner_id)
    document_id = create_document(chat_id, owner_id, "report.pdf")

    assert fetch_documents(owner_id)[0]["document_id"] == document_id
    assert fetch_documents(other_user_id) == []
    assert fetch_documents_for_chat(chat_id, owner_id)[0]["chat_id"] == chat_id
    assert fetch_documents_for_chat(chat_id, other_user_id) == []
    assert fetch_document(document_id, other_user_id) is None

    assert update_document_status(document_id, owner_id, "PROCESSING") == 1
    assert fetch_document(document_id, owner_id)["processing_status"] == "PROCESSING"
    with pytest.raises(ValueError):
        update_document_status(document_id, owner_id, "UNKNOWN")

    assert delete_document(document_id, other_user_id) == 0
    assert delete_document(document_id, owner_id) == 1
    assert fetch_documents(owner_id) == []


def test_deleting_chat_cascades_messages_and_documents(chat_database):
    user_id = create_user("Delete User", "delete@example.com", "hash")
    chat_id = create_chat(user_id)
    create_chat_message(chat_id, "USER", "Question")
    document_id = create_document(chat_id, user_id, "report.txt")

    assert delete_chat(chat_id, user_id) == 1
    assert fetch_chat(chat_id, user_id) is None
    assert fetch_document(document_id, user_id) is None

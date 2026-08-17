"""Chat session service that coordinates persistent chats and message storage."""

from app.repository import db
from app.services import document_service
from app.ai.rag import delete_chat_chunks


def list_chats(user_id):
    return db.fetch_chats(user_id)


def get_chat(chat_id, user_id):
    return db.fetch_chat(chat_id, user_id)


def create_chat(user_id, title=None):
    chat_id = db.create_chat(user_id, title=title)
    if not title:
        db.update_chat_title(chat_id, user_id, f"Chat {chat_id}")
    return chat_id


def delete_chat(chat_id, user_id):
    if not db.fetch_chat(chat_id, user_id):
        return False, "Chat not found."

    for document in db.fetch_documents_for_chat(chat_id, user_id):
        ok, message = document_service.delete_document(document["document_id"], user_id)
        if not ok:
            return False, message

    try:
        delete_chat_chunks(chat_id, user_id)
    except Exception as exc:
        print(f"[chat-delete-chunks] chat_id={chat_id} user_id={user_id} failed: {exc!r}")
        return False, "Unable to delete chat data from the search index."

    db.delete_chat(chat_id, user_id)
    return True, "Chat deleted."


def list_messages(chat_id, user_id):
    return db.fetch_chat_messages(chat_id, user_id)


def add_user_message(chat_id, content):
    return db.create_chat_message(chat_id, "USER", content)


def add_assistant_message(chat_id, content):
    return db.create_chat_message(chat_id, "ASSISTANT", content)


def touch_chat(chat_id):
    return db.touch_chat(chat_id)

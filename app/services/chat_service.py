"""Chat session service that coordinates persistent chats and message storage."""

from app.repository import db
from app.services import document_service
from app.ai.rag import delete_chat_chunks


def list_chats(user_id):
    return db.fetch_chats(user_id)


def list_conversations(user_id):
    """Return public conversation summaries without exposing internal chat IDs."""

    documents_by_chat = {}
    for document in db.fetch_documents(user_id):
        documents_by_chat.setdefault(document["chat_id"], []).append(
            document["original_filename"]
        )

    summaries = []
    for row in db.fetch_conversation_summaries(user_id):
        last_message = (row["last_message"] or "").strip()
        summaries.append(
            {
                "conversation_id": row["conversation_id"],
                "chat_title": row["chat_title"],
                "updated_at": row["updated_at"],
                "message_count": int(row["message_count"]),
                "last_message_preview": last_message[:160] or None,
                "uploaded_documents": documents_by_chat.get(row["chat_id"], []),
            }
        )
    return summaries


def get_chat(chat_id, user_id):
    return db.fetch_chat(chat_id, user_id)


def get_chat_by_conversation_id(conversation_id, user_id):
    return db.fetch_chat_by_conversation_id(conversation_id, user_id)


def create_chat(user_id, title=None):
    return db.create_chat(user_id, title=title)


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

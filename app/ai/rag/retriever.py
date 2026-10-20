"""Metadata-filtered retriever for configured document vector stores."""

from app.ai.rag.embeddings import get_embeddings
from app.ai.rag.vector_store import search
from app.ai.provider_errors import raise_provider_error


def retrieve_relevant_chunks(query_text, user_id, chat_id, limit=8):
    if not query_text or not query_text.strip():
        return []

    try:
        query_embedding = get_embeddings().embed_query(query_text)
    except Exception as exc:
        raise_provider_error(exc, operation="embeddings")
    return search(query_embedding, user_id, chat_id, limit)

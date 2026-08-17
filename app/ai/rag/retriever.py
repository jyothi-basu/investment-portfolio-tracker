"""Metadata-filtered retriever for document chunks stored in Chroma."""

from app.ai.rag.embeddings import get_embeddings
from app.ai.rag.vector_store import get_collection


def retrieve_relevant_chunks(query_text, user_id, chat_id, limit=8):
    if not query_text or not query_text.strip():
        return []

    embeddings = get_embeddings()
    query_embedding = embeddings.embed_query(query_text)
    collection = get_collection()
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=limit,
        # Use an explicit ownership predicate so Chroma validates the filter unambiguously.
        where={
            "$and": [
                {"user_id": {"$eq": int(user_id)}},
                {"chat_id": {"$eq": int(chat_id)}},
            ]
        },
    )

    documents = result.get("documents", [[]])[0] or []
    metadatas = result.get("metadatas", [[]])[0] or []
    distances = result.get("distances", [[]])[0] or []

    chunks = []
    for index, document_text in enumerate(documents):
        chunks.append(
            {
                "content": document_text,
                "metadata": metadatas[index] if index < len(metadatas) else {},
                "distance": distances[index] if index < len(distances) else None,
            }
        )
    return chunks

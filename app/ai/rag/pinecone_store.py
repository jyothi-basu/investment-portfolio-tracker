"""Pinecone implementation of the document vector-store contract."""

from functools import lru_cache
import os

from app.ai.rag.chunk_utils import prepare_chunks
from app.ai.rag.embeddings import get_embeddings
from app.ai.rag.errors import VectorStoreConfigurationError
from app.ai.provider_errors import raise_provider_error


def _required_setting(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise VectorStoreConfigurationError(
            f"{name} is required when VECTOR_STORE_PROVIDER=pinecone."
        )
    return value


@lru_cache(maxsize=1)
def get_index():
    try:
        from pinecone import Pinecone
    except ImportError as exc:
        raise VectorStoreConfigurationError(
            "VECTOR_STORE_PROVIDER=pinecone requires the pinecone package. "
            "Install it with: pip install pinecone"
        ) from exc

    client = Pinecone(api_key=_required_setting("PINECONE_API_KEY"))
    index_host = os.environ.get("PINECONE_INDEX_HOST", "").strip()
    if index_host:
        return client.Index(host=index_host)
    return client.Index(_required_setting("PINECONE_INDEX_NAME"))


def _namespace():
    return os.environ.get("PINECONE_NAMESPACE", "default").strip() or "default"


def add_document_chunks(
    document_id,
    user_id,
    chat_id,
    original_filename,
    chunks,
    document_type=None,
    company=None,
):
    prepared = prepare_chunks(
        document_id,
        user_id,
        chat_id,
        original_filename,
        chunks,
        document_type=document_type,
        company=company,
    )
    texts = [item["text"] for item in prepared]
    try:
        vectors = get_embeddings().embed_documents(texts)
    except Exception as exc:
        raise_provider_error(exc, operation="embeddings")

    records = []
    for item, vector in zip(prepared, vectors):
        metadata = dict(item["metadata"])
        # Pinecone returns metadata with query matches, so retain the chunk text there.
        metadata["_content"] = item["text"]
        records.append({"id": item["id"], "values": vector, "metadata": metadata})

    get_index().upsert(vectors=records, namespace=_namespace())
    return [item["id"] for item in prepared]


def _ownership_filter(**values):
    return {"$and": [{key: {"$eq": int(value)}} for key, value in values.items()]}


def delete_document_chunks(document_id, user_id):
    get_index().delete(
        filter=_ownership_filter(document_id=document_id, user_id=user_id),
        namespace=_namespace(),
    )


def delete_chat_chunks(chat_id, user_id):
    get_index().delete(
        filter=_ownership_filter(chat_id=chat_id, user_id=user_id),
        namespace=_namespace(),
    )


def _field(value, name, default=None):
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def search(query_embedding, user_id, chat_id, limit):
    result = get_index().query(
        vector=query_embedding,
        top_k=limit,
        include_metadata=True,
        namespace=_namespace(),
        filter=_ownership_filter(user_id=user_id, chat_id=chat_id),
    )
    matches = _field(result, "matches", []) or []
    chunks = []
    for match in matches:
        metadata = dict(_field(match, "metadata", {}) or {})
        content = metadata.pop("_content", "")
        score = _field(match, "score")
        chunks.append(
            {
                "content": content,
                "metadata": metadata,
                "distance": (1 - score) if isinstance(score, (int, float)) else None,
            }
        )
    return chunks

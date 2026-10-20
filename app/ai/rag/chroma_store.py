"""Chroma implementation of the document vector-store contract."""

from pathlib import Path

import chromadb

from app.ai.rag.chunk_utils import prepare_chunks
from app.ai.rag.embeddings import get_embeddings
from app.ai.provider_errors import raise_provider_error


BASE_DIR = Path(__file__).resolve().parents[3]
CHROMA_DIR = BASE_DIR / "data" / "chroma"
COLLECTION_NAME = "investment_portfolio_documents"


def _ensure_chroma_dir():
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)


def get_collection():
    _ensure_chroma_dir()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=COLLECTION_NAME)


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
    get_collection().upsert(
        ids=[item["id"] for item in prepared],
        documents=texts,
        embeddings=vectors,
        metadatas=[item["metadata"] for item in prepared],
    )
    return [item["id"] for item in prepared]


def delete_document_chunks(document_id, user_id):
    get_collection().delete(
        where={
            "$and": [
                {"document_id": {"$eq": int(document_id)}},
                {"user_id": {"$eq": int(user_id)}},
            ]
        }
    )


def delete_chat_chunks(chat_id, user_id):
    get_collection().delete(
        where={
            "$and": [
                {"chat_id": {"$eq": int(chat_id)}},
                {"user_id": {"$eq": int(user_id)}},
            ]
        }
    )


def search(query_embedding, user_id, chat_id, limit):
    result = get_collection().query(
        query_embeddings=[query_embedding],
        n_results=limit,
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
    return [
        {
            "content": document,
            "metadata": metadatas[index] if index < len(metadatas) else {},
            "distance": distances[index] if index < len(distances) else None,
        }
        for index, document in enumerate(documents)
    ]

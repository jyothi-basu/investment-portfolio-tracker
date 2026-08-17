"""Chroma persistence for document chunks with user and chat ownership metadata."""

from pathlib import Path

import chromadb

from app.ai.rag.embeddings import get_embeddings


BASE_DIR = Path(__file__).resolve().parents[3]
CHROMA_DIR = BASE_DIR / "data" / "chroma"
COLLECTION_NAME = "investment_portfolio_documents"


def _ensure_chroma_dir():
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)


def get_collection():
    _ensure_chroma_dir()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=COLLECTION_NAME)


def _build_metadata(document_id, user_id, chat_id, original_filename, chunk_index, document_type=None, company=None, page_number=None):
    metadata = {
        "document_id": int(document_id),
        "user_id": int(user_id),
        "chat_id": int(chat_id),
        "original_filename": original_filename,
        "chunk_index": int(chunk_index),
    }
    if page_number is not None:
        metadata["page_number"] = int(page_number)
    if document_type:
        metadata["document_type"] = document_type
    if company:
        metadata["company"] = company
    return metadata


def add_document_chunks(document_id, user_id, chat_id, original_filename, chunks, document_type=None, company=None):
    if not chunks:
        raise ValueError("chunks must not be empty")

    chunk_texts = []
    chunk_metadatas = []
    for default_index, chunk in enumerate(chunks):
        if isinstance(chunk, dict):
            text = (chunk.get("text") or "").strip()
            metadata = dict(chunk.get("metadata") or {})
            chunk_index = metadata.get("chunk_index", default_index)
            page_number = metadata.get("page_number")
        else:
            text = (chunk or "").strip()
            metadata = {}
            chunk_index = default_index
            page_number = None

        if not text:
            continue

        # Keep metadata separate from chunk text so retrieval filters do not leak into prompts.
        chunk_texts.append(text)
        chunk_metadatas.append(
            _build_metadata(
                document_id=document_id,
                user_id=user_id,
                chat_id=chat_id,
                original_filename=original_filename,
                chunk_index=chunk_index,
                document_type=document_type,
                company=company,
                page_number=page_number,
            )
        )

    if not chunk_texts:
        raise ValueError("chunks must not be empty")

    embeddings = get_embeddings()
    vectors = embeddings.embed_documents(chunk_texts)
    collection = get_collection()
    ids = [f"document-{document_id}-chunk-{index}" for index in range(len(chunk_texts))]
    collection.add(ids=ids, documents=chunk_texts, embeddings=vectors, metadatas=chunk_metadatas)
    return ids


def delete_document_chunks(document_id, user_id):
    collection = get_collection()
    collection.delete(
        where={
            "$and": [
                {"document_id": {"$eq": int(document_id)}},
                {"user_id": {"$eq": int(user_id)}},
            ]
        }
    )


def delete_chat_chunks(chat_id, user_id):
    collection = get_collection()
    collection.delete(
        where={
            "$and": [
                {"chat_id": {"$eq": int(chat_id)}},
                {"user_id": {"$eq": int(user_id)}},
            ]
        }
    )

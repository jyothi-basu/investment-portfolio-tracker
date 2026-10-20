"""Tests for configurable vector-store selection and result normalization."""

from unittest.mock import Mock

import pytest

from app.ai.rag import pinecone_store, vector_store
from app.ai.rag.errors import VectorStoreConfigurationError


def test_vector_store_defaults_to_chroma(monkeypatch):
    monkeypatch.delenv("VECTOR_STORE_PROVIDER", raising=False)
    assert vector_store.get_provider() == "chroma"


def test_vector_store_accepts_pinecone(monkeypatch):
    monkeypatch.setenv("VECTOR_STORE_PROVIDER", "pinecone")
    assert vector_store.get_provider() == "pinecone"


def test_vector_store_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("VECTOR_STORE_PROVIDER", "unknown")
    with pytest.raises(VectorStoreConfigurationError):
        vector_store.get_provider()


def test_pinecone_ownership_filter_is_user_and_chat_scoped():
    assert pinecone_store._ownership_filter(user_id=7, chat_id=11) == {
        "$and": [
            {"user_id": {"$eq": 7}},
            {"chat_id": {"$eq": 11}},
        ]
    }


def test_pinecone_search_normalizes_matches(monkeypatch):
    index = Mock()
    index.query.return_value = {
        "matches": [
            {
                "id": "document-4-chunk-0",
                "score": 0.8,
                "metadata": {
                    "_content": "Revenue increased.",
                    "document_id": 4,
                    "user_id": 7,
                    "chat_id": 11,
                    "original_filename": "report.txt",
                    "chunk_index": 0,
                },
            }
        ]
    }
    monkeypatch.setattr(pinecone_store, "get_index", lambda: index)
    monkeypatch.setenv("PINECONE_NAMESPACE", "test")

    result = pinecone_store.search([0.1, 0.2], user_id=7, chat_id=11, limit=3)

    assert result == [
        {
            "content": "Revenue increased.",
            "metadata": {
                "document_id": 4,
                "user_id": 7,
                "chat_id": 11,
                "original_filename": "report.txt",
                "chunk_index": 0,
            },
            "distance": pytest.approx(0.2),
        }
    ]
    index.query.assert_called_once_with(
        vector=[0.1, 0.2],
        top_k=3,
        include_metadata=True,
        namespace="test",
        filter={
            "$and": [
                {"user_id": {"$eq": 7}},
                {"chat_id": {"$eq": 11}},
            ]
        },
    )

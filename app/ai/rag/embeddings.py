"""Embedding factory used by the Chroma vector-store layer."""

from app.ai.provider_factory import build_embeddings_model


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def get_embeddings():
    return build_embeddings_model(default_model=DEFAULT_EMBEDDING_MODEL)

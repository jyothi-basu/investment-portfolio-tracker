"""Provider-neutral facade for document vector storage."""

import os

from app.ai.rag.errors import VectorStoreConfigurationError


def get_provider():
    value = os.environ.get("VECTOR_STORE_PROVIDER", "chroma").strip().lower()
    if value in {"chroma", "pinecone"}:
        return value
    raise VectorStoreConfigurationError(
        f"Unsupported vector-store provider {value!r}. "
        "Supported providers are: chroma, pinecone."
    )


def _backend():
    if get_provider() == "chroma":
        from app.ai.rag import chroma_store

        return chroma_store

    from app.ai.rag import pinecone_store

    return pinecone_store


def add_document_chunks(*args, **kwargs):
    return _backend().add_document_chunks(*args, **kwargs)


def delete_document_chunks(*args, **kwargs):
    return _backend().delete_document_chunks(*args, **kwargs)


def delete_chat_chunks(*args, **kwargs):
    return _backend().delete_chat_chunks(*args, **kwargs)


def search(*args, **kwargs):
    return _backend().search(*args, **kwargs)

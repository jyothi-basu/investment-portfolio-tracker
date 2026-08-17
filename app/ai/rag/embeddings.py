"""OpenAI embedding factory used by the Chroma vector-store layer."""

import os

from langchain_openai import OpenAIEmbeddings


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def get_embeddings():
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    model = os.environ.get("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip() or DEFAULT_EMBEDDING_MODEL
    return OpenAIEmbeddings(model=model, api_key=api_key)

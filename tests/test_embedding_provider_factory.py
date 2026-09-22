"""Provider selection tests for the provider-agnostic embedding factory."""

from unittest.mock import Mock

import langchain_google_genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.ai import provider_factory


def _clear_embedding_environment(monkeypatch):
    for name in (
        "EMBEDDINGS_PROVIDER",
        "EMBEDDINGS_MODEL",
        "EMBEDDINGS_API_KEY",
        "EMBEDDINGS_BASE_URL",
        "LLM_PROVIDER",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "OPENAI_PROVIDER",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_API_BASE",
        "OPENAI_EMBEDDING_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_local_embeddings_provider_keeps_sentence_transformer_branch(monkeypatch):
    _clear_embedding_environment(monkeypatch)
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "local")
    monkeypatch.setenv("EMBEDDINGS_MODEL", "example/local-model")
    constructor = Mock(return_value=object())
    monkeypatch.setattr(provider_factory, "LocalSentenceTransformerEmbeddings", constructor)

    result = provider_factory.create_embedding_model()

    constructor.assert_called_once_with(model_name="example/local-model")
    assert result is constructor.return_value


def test_openai_embeddings_provider_preserves_existing_branch(monkeypatch):
    _clear_embedding_environment(monkeypatch)
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "openai")
    monkeypatch.setenv("EMBEDDINGS_MODEL", "text-embedding-test")
    monkeypatch.setenv("EMBEDDINGS_API_KEY", "openai-test-key")
    constructor = Mock(return_value=object())
    monkeypatch.setattr(provider_factory, "OpenAIEmbeddings", constructor)

    result = provider_factory.create_embedding_model()

    constructor.assert_called_once_with(
        model="text-embedding-test",
        api_key="openai-test-key",
        base_url=None,
    )
    assert result is constructor.return_value


def test_gemini_embeddings_uses_model_key_fallback_and_no_base_url(monkeypatch):
    _clear_embedding_environment(monkeypatch)
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "gemini")
    monkeypatch.setenv("EMBEDDINGS_MODEL", "gemini-embedding-001")
    monkeypatch.setenv("EMBEDDINGS_API_KEY", "")
    monkeypatch.setenv("LLM_API_KEY", "google-ai-studio-key")
    monkeypatch.setenv("EMBEDDINGS_BASE_URL", "https://should-not-be-used.example")
    constructor = Mock(return_value=object())
    monkeypatch.setattr(
        langchain_google_genai,
        "GoogleGenerativeAIEmbeddings",
        constructor,
    )
    load_local_model = Mock(side_effect=AssertionError("local model must not load"))
    monkeypatch.setattr(provider_factory, "_load_sentence_transformer", load_local_model)

    result = provider_factory.create_embedding_model()

    constructor.assert_called_once_with(
        model="gemini-embedding-001",
        google_api_key="google-ai-studio-key",
        vertexai=False,
    )
    load_local_model.assert_not_called()
    assert result is constructor.return_value
    assert callable(GoogleGenerativeAIEmbeddings.embed_documents)
    assert callable(GoogleGenerativeAIEmbeddings.embed_query)


def test_openai_compatible_embeddings_still_require_and_use_base_url(monkeypatch):
    _clear_embedding_environment(monkeypatch)
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "openai-compatible")
    monkeypatch.setenv("EMBEDDINGS_MODEL", "compatible-embedding-model")
    monkeypatch.setenv("EMBEDDINGS_API_KEY", "compatible-test-key")
    monkeypatch.setenv("EMBEDDINGS_BASE_URL", "https://embeddings.example/v1")
    constructor = Mock(return_value=object())
    monkeypatch.setattr(provider_factory, "OpenAIEmbeddings", constructor)

    result = provider_factory.create_embedding_model()

    constructor.assert_called_once_with(
        model="compatible-embedding-model",
        api_key="compatible-test-key",
        base_url="https://embeddings.example/v1",
    )
    assert result is constructor.return_value

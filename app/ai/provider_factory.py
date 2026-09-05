"""Provider-aware factories for chat models and embedding models.

The AI layer uses this module as a single decision point for model selection.
It keeps the rest of the codebase agnostic to the concrete provider while still
supporting OpenAI-compatible or Gemini chat endpoints and either
OpenAI-compatible or local SentenceTransformer embeddings through environment
config.
"""

from __future__ import annotations

import os
from functools import lru_cache
from dataclasses import dataclass

from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


DEFAULT_CHAT_MODEL = "gpt-4.1-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class ProviderConfigurationError(RuntimeError):
    """Raised when provider configuration is missing or unsupported."""


@dataclass(frozen=True)
class ProviderSettings:
    """Resolved provider settings for a chat or embedding client."""

    provider: str
    api_key: str
    model: str
    base_url: str | None = None


class LocalSentenceTransformerEmbeddings(Embeddings):
    """SentenceTransformer-backed embeddings for local or offline retrieval."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = _load_sentence_transformer(model_name)

    def _encode(self, texts: list[str]) -> list[list[float]]:
        normalized_texts = [str(text or "") for text in texts]
        vectors = self._model.encode(
            normalized_texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        if hasattr(vectors, "tolist"):
            return vectors.tolist()
        return [list(vector) for vector in vectors]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([text])[0]


def _first_non_empty(*values, default=""):
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _normalize_provider(provider):
    normalized = _first_non_empty(provider, default="openai").lower()
    normalized = normalized.replace(" ", "-").replace("_", "-")
    if normalized in {"openai", "openai-compatible", "gemini"}:
        return normalized
    raise ProviderConfigurationError(
        f"Unsupported AI provider {provider!r}. Supported providers are: "
        "openai, openai-compatible, gemini."
    )


def _normalize_embedding_provider(provider):
    normalized = _first_non_empty(provider, default="openai").lower()
    normalized = normalized.replace(" ", "-").replace("_", "-")
    if normalized in {"openai", "openai-compatible", "local"}:
        return normalized
    raise ProviderConfigurationError(
        f"Unsupported embedding provider {provider!r}. Supported providers are: "
        "openai, openai-compatible, local."
    )


@lru_cache(maxsize=4)
def _load_sentence_transformer(model_name):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ProviderConfigurationError(
            "EMBEDDINGS_PROVIDER=local requires the sentence-transformers package. "
            "Install it with: pip install sentence-transformers"
        ) from exc

    try:
        return SentenceTransformer(model_name)
    except Exception as exc:
        raise ProviderConfigurationError(
            f"EMBEDDINGS_MODEL={model_name!r} could not be loaded for EMBEDDINGS_PROVIDER=local. "
            "Check that the model name is valid, that the model can be downloaded, and that your environment "
            "has network access or a local cache for the SentenceTransformer weights."
        ) from exc


def _read_chat_settings(default_model=DEFAULT_CHAT_MODEL):
    provider = _normalize_provider(
        _first_non_empty(
            os.environ.get("LLM_PROVIDER"),
            os.environ.get("OPENAI_PROVIDER"),
            default="openai",
        )
    )
    api_key = _first_non_empty(os.environ.get("LLM_API_KEY"), os.environ.get("OPENAI_API_KEY"))
    if not api_key:
        raise ProviderConfigurationError("LLM_API_KEY is not set.")

    model = _first_non_empty(os.environ.get("LLM_MODEL"), os.environ.get("OPENAI_MODEL"), default=default_model)
    base_url = _first_non_empty(
        os.environ.get("LLM_BASE_URL"),
        os.environ.get("OPENAI_BASE_URL"),
        os.environ.get("OPENAI_API_BASE"),
    )
    if provider == "openai-compatible" and not base_url:
        raise ProviderConfigurationError("LLM_BASE_URL is required for openai-compatible providers.")

    if provider == "gemini":
        base_url = None

    return ProviderSettings(provider=provider, api_key=api_key, model=model, base_url=base_url or None)


def _build_gemini_chat_model(*, settings, temperature, max_tokens):
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:
        raise ProviderConfigurationError(
            "LLM_PROVIDER=gemini requires the langchain-google-genai package. "
            "Install it with: pip install langchain-google-genai"
        ) from exc

    try:
        return ChatGoogleGenerativeAI(
            model=settings.model,
            temperature=temperature,
            max_output_tokens=max_tokens,
            api_key=settings.api_key,
        )
    except Exception as exc:
        raise ProviderConfigurationError(
            f"LLM_PROVIDER=gemini could not initialize model {settings.model!r}. "
            "Check LLM_MODEL and LLM_API_KEY, and ensure the model name is valid."
        ) from exc


def _read_embedding_settings(default_model=DEFAULT_EMBEDDING_MODEL):
    provider = _normalize_embedding_provider(
        _first_non_empty(
            os.environ.get("EMBEDDINGS_PROVIDER"),
            os.environ.get("LLM_PROVIDER"),
            os.environ.get("OPENAI_PROVIDER"),
            default="openai",
        )
    )
    if provider == "local":
        model = _first_non_empty(os.environ.get("EMBEDDINGS_MODEL"))
        if not model:
            raise ProviderConfigurationError(
                "EMBEDDINGS_MODEL is required when EMBEDDINGS_PROVIDER=local."
            )
        return ProviderSettings(provider=provider, api_key="", model=model, base_url=None)

    api_key = _first_non_empty(
        os.environ.get("EMBEDDINGS_API_KEY"),
        os.environ.get("LLM_API_KEY"),
        os.environ.get("OPENAI_API_KEY"),
    )
    if not api_key:
        raise ProviderConfigurationError("EMBEDDINGS_API_KEY is not set.")

    model = _first_non_empty(
        os.environ.get("EMBEDDINGS_MODEL"),
        os.environ.get("OPENAI_EMBEDDING_MODEL"),
        default=default_model,
    )
    base_url = _first_non_empty(
        os.environ.get("EMBEDDINGS_BASE_URL"),
        os.environ.get("LLM_BASE_URL"),
        os.environ.get("OPENAI_BASE_URL"),
        os.environ.get("OPENAI_API_BASE"),
    )
    if provider == "openai-compatible" and not base_url:
        raise ProviderConfigurationError(
            "EMBEDDINGS_BASE_URL is required for openai-compatible providers."
        )

    return ProviderSettings(provider=provider, api_key=api_key, model=model, base_url=base_url or None)


def build_chat_model(*, default_model=DEFAULT_CHAT_MODEL, temperature=0.4, max_tokens=None):
    """Create the configured chat model for tool-calling and classification."""

    settings = _read_chat_settings(default_model=default_model)

    if settings.provider == "gemini":
        return _build_gemini_chat_model(
            settings=settings,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    return ChatOpenAI(
        model=settings.model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=settings.api_key,
        base_url=settings.base_url,
    )


def get_chat_provider_settings(*, default_model=DEFAULT_CHAT_MODEL) -> ProviderSettings:
    """Return the resolved chat provider settings without building the client."""

    return _read_chat_settings(default_model=default_model)


def build_embeddings_model(*, default_model=DEFAULT_EMBEDDING_MODEL):
    """Create the configured embedding model for Chroma ingestion and retrieval."""

    return create_embedding_model(default_model=default_model)


def create_embedding_model(*, default_model=DEFAULT_EMBEDDING_MODEL):
    """Create the configured embedding model for Chroma ingestion and retrieval."""

    settings = _read_embedding_settings(default_model=default_model)

    if settings.provider == "local":
        return LocalSentenceTransformerEmbeddings(model_name=settings.model)

    return OpenAIEmbeddings(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
    )


def get_embedding_provider_settings(*, default_model=DEFAULT_EMBEDDING_MODEL) -> ProviderSettings:
    """Return the resolved embedding provider settings without building the client."""

    return _read_embedding_settings(default_model=default_model)

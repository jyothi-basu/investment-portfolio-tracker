"""Provider-failure classification tests."""

from app.ai.provider_errors import (
    AIProviderError,
    EMBEDDING_QUOTA_MESSAGE,
    EMBEDDING_TEMPORARY_MESSAGE,
    LLM_MODEL_UNAVAILABLE_MESSAGE,
    LLM_QUOTA_MESSAGE,
    LLM_TEMPORARY_MESSAGE,
    classify_provider_failure,
    raise_provider_error,
)


class ProviderException(RuntimeError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def test_llm_rate_limit_uses_quota_message():
    failure = classify_provider_failure(
        ProviderException("rate limit exceeded", status_code=429),
        operation="llm",
    )
    assert failure.category == "quota"
    assert failure.user_message == LLM_QUOTA_MESSAGE


def test_llm_model_not_found_uses_model_message():
    failure = classify_provider_failure(
        ProviderException("model not found", status_code=404),
        operation="llm",
    )
    assert failure.category == "model_unavailable"
    assert failure.user_message == LLM_MODEL_UNAVAILABLE_MESSAGE


def test_embedding_rate_limit_uses_embedding_quota_message():
    failure = classify_provider_failure(
        ProviderException("resource exhausted", status_code=429),
        operation="embeddings",
    )
    assert failure.category == "quota"
    assert failure.user_message == EMBEDDING_QUOTA_MESSAGE


def test_authentication_and_server_errors_use_generic_messages():
    assert classify_provider_failure(
        ProviderException("invalid api key", status_code=401),
        operation="llm",
    ).user_message == LLM_TEMPORARY_MESSAGE
    assert classify_provider_failure(
        ProviderException("service unavailable", status_code=503),
        operation="embeddings",
    ).user_message == EMBEDDING_TEMPORARY_MESSAGE


def test_raise_provider_error_preserves_safe_classification():
    try:
        raise_provider_error(
            ProviderException("quota exceeded", status_code=429),
            operation="llm",
        )
    except AIProviderError as exc:
        assert str(exc) == LLM_QUOTA_MESSAGE
        assert exc.failure.category == "quota"
    else:
        raise AssertionError("raise_provider_error must raise AIProviderError")

"""Translate provider failures into safe, user-facing application errors."""

from __future__ import annotations

from dataclasses import dataclass


LLM_QUOTA_MESSAGE = (
    "We're sorry, but the AI assistant has temporarily reached its usage limit. "
    "Please try again later. You can still manage your portfolio and transactions."
)
LLM_MODEL_UNAVAILABLE_MESSAGE = (
    "We're sorry, but the AI assistant is temporarily unavailable. "
    "Please try again later."
)
LLM_TEMPORARY_MESSAGE = (
    "The AI service is temporarily unavailable. Please try again shortly. "
    "Your existing portfolio data has not been affected."
)
EMBEDDING_QUOTA_MESSAGE = (
    "We're sorry, but document processing has temporarily reached its usage limit. "
    "Please try uploading or searching documents again later. "
    "Your existing portfolio features remain available."
)
EMBEDDING_TEMPORARY_MESSAGE = (
    "Document processing is temporarily unavailable. Please try again shortly. "
    "Your existing portfolio data has not been affected."
)


@dataclass(frozen=True)
class ProviderFailure:
    """Safe classification of a failure from an external AI provider."""

    operation: str
    category: str
    user_message: str


class AIProviderError(RuntimeError):
    """Application-level error raised after an AI provider failure is classified."""

    def __init__(self, failure: ProviderFailure, *, cause: Exception | None = None):
        super().__init__(failure.user_message)
        self.failure = failure
        self.cause = cause


def _status_code(exc: Exception):
    for candidate in (
        getattr(exc, "status_code", None),
        getattr(exc, "status", None),
        getattr(getattr(exc, "response", None), "status_code", None),
    ):
        try:
            if candidate is not None:
                return int(candidate)
        except (TypeError, ValueError):
            continue
    return None


def _exception_text(exc: Exception) -> str:
    parts = [exc.__class__.__name__, str(exc)]
    for attribute in ("code", "error_code", "reason"):
        value = getattr(exc, attribute, None)
        if value:
            parts.append(str(value))
    return " ".join(parts).lower()


def classify_provider_failure(exc: Exception, *, operation: str) -> ProviderFailure:
    """Classify a provider exception without exposing provider details to users."""

    text = _exception_text(exc)
    status_code = _status_code(exc)
    is_embedding = operation == "embeddings"

    quota_signal = (
        status_code == 429
        or "rate limit" in text
        or "ratelimit" in text
        or "quota" in text
        or "resource exhausted" in text
        or "resourceexhausted" in text
    )
    if quota_signal:
        return ProviderFailure(
            operation=operation,
            category="quota",
            user_message=EMBEDDING_QUOTA_MESSAGE if is_embedding else LLM_QUOTA_MESSAGE,
        )

    model_unavailable = (
        status_code == 404
        or "model not found" in text
        or "model_not_found" in text
        or "model unavailable" in text
        or "model_unavailable" in text
    )
    if model_unavailable and not is_embedding:
        return ProviderFailure(
            operation=operation,
            category="model_unavailable",
            user_message=LLM_MODEL_UNAVAILABLE_MESSAGE,
        )

    # Authentication, provider 5xx responses, timeouts, and unknown provider
    # failures receive a generic message rather than an inaccurate quota claim.
    return ProviderFailure(
        operation=operation,
        category="temporary",
        user_message=EMBEDDING_TEMPORARY_MESSAGE if is_embedding else LLM_TEMPORARY_MESSAGE,
    )


def raise_provider_error(exc: Exception, *, operation: str) -> None:
    """Raise a classified provider error while retaining the original cause."""

    if isinstance(exc, AIProviderError):
        raise exc
    failure = classify_provider_failure(exc, operation=operation)
    raise AIProviderError(failure, cause=exc) from exc

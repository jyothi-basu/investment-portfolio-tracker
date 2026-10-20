"""Errors raised by configurable RAG providers."""


class VectorStoreConfigurationError(RuntimeError):
    """Raised when the configured vector-store provider is not usable."""

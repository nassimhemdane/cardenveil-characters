"""Stable exception hierarchy for PDF character imports."""

from cardenveil.errors import CardenveilError


class CharacterImportError(CardenveilError):
    """Base exception raised by the PDF import pipeline."""


class CharacterExtractionError(CharacterImportError):
    """Raised when a document cannot be converted into extracted data."""


class InvalidExtractionError(CharacterExtractionError):
    """Raised when provider output fails the structured extraction schema."""


class CharacterMappingError(CharacterImportError):
    """Raised when valid extracted data cannot map to a character sheet."""


class LLMProviderError(CharacterExtractionError):
    """Provider-neutral failure from an external LLM or VLM."""


class LLMAuthenticationError(LLMProviderError):
    """Non-retryable provider authentication or authorization failure."""


class LLMQuotaError(LLMProviderError):
    """Provider quota or rate-limit failure after configured retries."""


class MissingPDFDependencyError(CharacterImportError, ImportError):
    """Raised when an optional PDF/provider dependency is not installed."""

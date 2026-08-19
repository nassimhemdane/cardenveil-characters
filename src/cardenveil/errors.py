"""Public exception hierarchy."""


class CardenveilError(Exception):
    """Base exception for the library."""


class ValidationError(CardenveilError, ValueError):
    """Raised when an object violates a structural domain invariant."""


class UnknownContentError(CardenveilError, LookupError):
    """Raised when a catalog does not contain a requested definition."""


class SerializationError(CardenveilError, ValueError):
    """Raised when serialized data cannot be decoded safely."""

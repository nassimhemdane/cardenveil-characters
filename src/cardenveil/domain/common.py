"""Shared primitives and stable identifiers used by the domain."""

from __future__ import annotations

import re
from dataclasses import dataclass

from cardenveil.errors import ValidationError

_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


@dataclass(frozen=True, slots=True, order=True)
class ContentId:
    """Stable ID for content definitions, independent from display names."""

    value: str

    def __post_init__(self) -> None:
        """Validate the stable content-ID syntax."""
        if not _ID_PATTERN.fullmatch(self.value):
            raise ValidationError(f"Invalid content ID: {self.value!r}")

    def __str__(self) -> str:
        """Return the serialized ID value."""
        return self.value


@dataclass(frozen=True, slots=True, order=True)
class CharacterId:
    """Stable ID for a character entity."""

    value: str

    def __post_init__(self) -> None:
        """Validate the stable character-ID syntax."""
        if not _ID_PATTERN.fullmatch(self.value):
            raise ValidationError(f"Invalid character ID: {self.value!r}")

    def __str__(self) -> str:
        """Return the serialized ID value."""
        return self.value

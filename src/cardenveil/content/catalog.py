"""Small typed catalogs for official definitions; custom definitions remain valid domain objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from cardenveil.domain import ContentId
from cardenveil.errors import UnknownContentError, ValidationError


class Identified(Protocol):
    """Protocol implemented by definitions carrying a stable content ID."""

    id: ContentId


T = TypeVar("T", bound=Identified)


@dataclass(frozen=True, slots=True)
class Catalog(Generic[T]):
    """Immutable-by-convention typed lookup for uniquely identified definitions."""

    _items: dict[ContentId, T]

    @classmethod
    def from_items(cls, items: list[T]) -> Catalog[T]:
        """Build a catalog and reject duplicate stable IDs."""
        indexed = {item.id: item for item in items}
        if len(indexed) != len(items):
            raise ValidationError("Catalog contains duplicate IDs")
        return cls(indexed)

    def all(self) -> tuple[T, ...]:
        """Return every definition in declaration order."""
        return tuple(self._items.values())

    def get(self, item_id: str | ContentId) -> T:
        """Resolve one definition or raise ``UnknownContentError``."""
        key = item_id if isinstance(item_id, ContentId) else ContentId(item_id)
        try:
            return self._items[key]
        except KeyError as error:
            raise UnknownContentError(str(key)) from error

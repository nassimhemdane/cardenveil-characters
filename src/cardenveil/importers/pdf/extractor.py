"""Provider-neutral extraction interface."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from cardenveil.importers.pdf.models import ExtractedCharacter


@runtime_checkable
class CharacterDocumentExtractor(Protocol):
    """Convert a visual PDF document into provider-neutral extracted data."""

    def extract(self, pdf_path: Path) -> ExtractedCharacter:
        """Analyze ``pdf_path`` and return validated semantic fields."""
        ...

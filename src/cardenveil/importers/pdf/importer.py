"""Orchestration of validation, extraction, mapping, and optional debug artifacts."""

from __future__ import annotations

import logging
from pathlib import Path

from cardenveil.domain import CharacterSheet
from cardenveil.importers.pdf.assets import PDFImageAssetExtractor
from cardenveil.importers.pdf.errors import CharacterExtractionError, CharacterImportError
from cardenveil.importers.pdf.extractor import CharacterDocumentExtractor
from cardenveil.importers.pdf.mapper import CharacterMapper
from cardenveil.serialization import character_to_archive, character_to_json

LOGGER = logging.getLogger(__name__)


class CharacterPDFImporter:
    """Provider-neutral entry point converting a visual PDF into a character sheet."""

    def __init__(
        self,
        extractor: CharacterDocumentExtractor,
        mapper: CharacterMapper | None = None,
        debug_directory: str | Path | None = None,
        asset_extractor: PDFImageAssetExtractor | None = None,
    ) -> None:
        """Configure semantic extraction, mapping, debug output, and optional image assets."""

        self.extractor = extractor
        self.mapper = mapper or CharacterMapper()
        self.debug_directory = Path(debug_directory) if debug_directory is not None else None
        self.asset_extractor = asset_extractor

    def load(self, pdf_path: str | Path) -> CharacterSheet:
        """Validate and import one PDF into the canonical ``CharacterSheet`` type."""

        path = Path(pdf_path)
        self._validate_pdf(path)
        LOGGER.info(
            "Importing character PDF: file=%s bytes=%d pages=%s",
            path,
            path.stat().st_size,
            _page_count(path),
        )
        try:
            extracted = self.extractor.extract(path)
            sheet = self.mapper.map(extracted, path)
            if self.asset_extractor is not None:
                self.asset_extractor.extract(path, sheet)
        except CharacterImportError:
            raise
        except Exception as error:
            raise CharacterExtractionError(
                f"Unexpected extraction failure for {path.name}"
            ) from error
        if self.debug_directory is not None:
            self._write_debug(
                extracted.model_dump_json(by_alias=True, indent=2),
                character_to_json(sheet),
            )
        LOGGER.info("Character PDF imported: file=%s character_id=%s", path, sheet.id)
        return sheet

    def load_to_archive(
        self,
        pdf_path: str | Path,
        output_directory: str | Path,
    ) -> tuple[CharacterSheet, Path]:
        """Import one PDF and directly create its ``{character-id}.zip`` exchange archive."""

        sheet = self.load(pdf_path)
        asset_root = self.asset_extractor.asset_root if self.asset_extractor is not None else None
        archive_path = Path(output_directory) / f"{sheet.id}.zip"
        character_to_archive(sheet, archive_path, asset_root=asset_root)
        LOGGER.info("Character archive written: character_id=%s archive=%s", sheet.id, archive_path)
        return sheet, archive_path

    @staticmethod
    def _validate_pdf(path: Path) -> None:
        """Reject missing paths, wrong extensions, directories, and invalid PDF signatures."""

        if not path.is_file():
            raise CharacterImportError(f"PDF file does not exist: {path}")
        if path.suffix.lower() != ".pdf":
            raise CharacterImportError(f"Expected a .pdf file: {path}")
        try:
            with path.open("rb") as stream:
                signature = stream.read(5)
        except OSError as error:
            raise CharacterImportError(f"Cannot read PDF file: {path}") from error
        if signature != b"%PDF-":
            raise CharacterImportError(f"Invalid PDF signature: {path}")

    def _write_debug(self, extracted_json: str, character_json: str) -> None:
        """Write both pipeline boundaries only when a debug directory was requested."""

        assert self.debug_directory is not None
        self.debug_directory.mkdir(parents=True, exist_ok=True)
        (self.debug_directory / "extracted_character.json").write_text(
            extracted_json + "\n", encoding="utf-8"
        )
        (self.debug_directory / "character_sheet.json").write_text(
            character_json + "\n", encoding="utf-8"
        )


def _page_count(path: Path) -> int | str:
    """Return a page count when optional pypdf is available, otherwise ``unknown``."""

    try:
        from pypdf import PdfReader
    except ImportError:
        return "unknown"
    try:
        return len(PdfReader(path).pages)
    except Exception:
        return "unknown"

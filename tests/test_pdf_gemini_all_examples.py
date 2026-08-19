"""Opt-in batch evaluation of every reference character PDF with Gemini."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import pytest

from cardenveil import CharacterSheet
from cardenveil.importers.pdf import (
    CharacterPDFImporter,
    GeminiCharacterDocumentExtractor,
    PDFImageAssetExtractor,
)
from cardenveil.importers.pdf.config import GeminiConfig

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parents[1]
REFERENCE_PDFS = tuple(sorted((PROJECT_ROOT / "References" / "Pdf").glob("*.pdf")))


def _live_test_enabled() -> bool:
    """Load ``.env`` and require explicit consent before consuming Gemini quota."""

    try:
        from dotenv import load_dotenv
    except ImportError:
        return False
    load_dotenv(PROJECT_ROOT / ".env")
    return bool(
        os.getenv("GEMINI_API_KEY") and os.getenv("CARDENVEIL_RUN_GEMINI_INTEGRATION") == "1"
    )


@pytest.mark.skipif(
    not _live_test_enabled(),
    reason="Set GEMINI_API_KEY and CARDENVEIL_RUN_GEMINI_INTEGRATION=1 for the live test",
)
@pytest.mark.parametrize("pdf_path", REFERENCE_PDFS, ids=lambda path: path.stem)
def test_gemini_converts_every_reference_pdf_for_manual_review(pdf_path: Path) -> None:
    """Produce review artifacts without imposing subjective semantic-quality assertions."""

    output_root = Path(os.getenv("CARDENVEIL_GEMINI_OUTPUT_DIR", PROJECT_ROOT / "gemini-output"))
    character_directory = output_root / pdf_path.stem
    config = replace(GeminiConfig.from_env(PROJECT_ROOT / ".env"), max_attempts=1)
    extractor = GeminiCharacterDocumentExtractor(config)
    sheet, archive_path = CharacterPDFImporter(
        extractor,
        debug_directory=character_directory,
        asset_extractor=PDFImageAssetExtractor(output_root / "assets"),
    ).load_to_archive(pdf_path, output_root)

    assert isinstance(sheet, CharacterSheet)
    assert sheet.identity.nom
    assert archive_path == output_root / f"{sheet.id}.zip"
    assert archive_path.is_file()

"""Opt-in live Gemini test using one real PDF from the reference dataset."""

import os
from pathlib import Path

import pytest

from cardenveil import CharacterSheet

pytestmark = pytest.mark.integration


def _live_test_enabled() -> bool:
    """Load an optional dotenv file and require explicit consent for a live API call."""

    try:
        from dotenv import load_dotenv
    except ImportError:
        return False
    load_dotenv()
    return bool(
        os.getenv("GEMINI_API_KEY") and os.getenv("CARDENVEIL_RUN_GEMINI_INTEGRATION") == "1"
    )


@pytest.mark.skipif(
    not _live_test_enabled(),
    reason="Set GEMINI_API_KEY and CARDENVEIL_RUN_GEMINI_INTEGRATION=1 for the live test",
)
def test_real_gemini_imports_reference_pdf() -> None:
    """Call Gemini multimodally and require a genuine canonical character sheet."""

    from cardenveil.importers.pdf import CharacterPDFImporter, GeminiCharacterDocumentExtractor

    pdf = Path(__file__).parents[1] / "References" / "Pdf" / "Aurore.pdf"
    sheet = CharacterPDFImporter(GeminiCharacterDocumentExtractor.from_env()).load(pdf)
    assert isinstance(sheet, CharacterSheet)
    assert sheet.identity.nom

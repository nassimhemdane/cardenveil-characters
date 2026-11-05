"""Check the targeted publication workflow offline, with no Gemini quota consumption."""

import importlib
import json
import zipfile
from pathlib import Path

import pytest

from cardenveil.importers.pdf import GeminiConfig
from cardenveil.importers.pdf.models import ExtractedCatalogMetadata
from cardenveil.serialization import character_from_archive
from test_archive_normalizer import _source_archive

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def publisher(monkeypatch):
    """Load the publication CLI with its existing local maintenance helpers."""
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    return importlib.import_module("publish_character_archive")


def test_single_publication_preserves_source_and_syncs_metadata(publisher, monkeypatch, tmp_path):
    """Validate compression, explicit difficulty, metadata copy and duplicate protection."""
    source = tmp_path / "incoming.zip"
    _source_archive(source)
    original_bytes = source.read_bytes()
    (tmp_path / "Final").mkdir()
    (tmp_path / "web").mkdir()
    metadata_path = tmp_path / "web/catalog-metadata.json"
    metadata_path.write_text(json.dumps({"classVocabulary": ["Mage"], "characters": {}}), encoding="utf-8")
    monkeypatch.setattr(publisher.GeminiConfig, "from_env", lambda path: GeminiConfig(api_key="FAKE_TEST_KEY"))
    calls = []

    def extract(self, payload):
        """Return deterministic editorial output while checking the cleaned request."""
        sheet = json.loads(payload)
        assert sheet["identity"]["nom"] == "Éléonore du Val"
        calls.append(sheet["id"])
        return ExtractedCatalogMetadata(loreSummary="Résumé.\n", gameplaySummary="Style de jeu.", difficulty=1, classes=["Mage"])

    monkeypatch.setattr(publisher.GeminiCharacterDocumentExtractor, "extract_catalog_metadata_from_json", extract)
    metadata = publisher.publish(source, 3.5, root=tmp_path)
    archive_path = tmp_path / "Final/eleonore-du-val.zip"
    character = character_from_archive(archive_path)
    assert metadata["difficulty"] == 3.5 and metadata["loreSummary"] == "Résumé."
    assert character.derived.pvMax == 60 + 5 * character.stats.force
    assert source.read_bytes() == original_bytes
    assert archive_path.stat().st_size < source.stat().st_size
    with zipfile.ZipFile(archive_path) as archive:
        assert json.loads(archive.read("metadata.json")) == metadata
        assert len([name for name in archive.namelist() if name.endswith(".png")]) == 3
    assert json.loads(metadata_path.read_text(encoding="utf-8"))["characters"][character.id] == metadata
    with pytest.raises(FileExistsError):
        publisher.publish(source, 3.5, root=tmp_path)
    with pytest.raises(ValueError):
        publisher.publish(source, 3.7, root=tmp_path)
    assert len(calls) == 1

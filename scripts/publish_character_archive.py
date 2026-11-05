"""Prepare one new catalogue character, with compressed assets and Gemini metadata.

This local preparation command does not commit, push, or replace existing characters.
Example: py -3.11 -X utf8 scripts/publish_character_archive.py Toconvert/Garreth.zip --difficulty 3.5
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from dataclasses import replace
from pathlib import Path

from apply_october_updates import rewrite
from recalculate_confirmed_values import apply_values

from cardenveil.importers.archive import normalize_character_archive
from cardenveil.importers.pdf import GeminiCharacterDocumentExtractor, GeminiConfig
from cardenveil.importers.sheet_cleanup import normalize_and_empty_gear
from cardenveil.naming import slugify_character_id
from cardenveil.serialization import character_from_archive, character_to_json

ROOT = Path(__file__).resolve().parents[1]


def prepare_sheet(sheet: dict) -> None:
    """Apply established text/gear cleanup and previously confirmed derived-value formulas."""
    normalize_and_empty_gear(sheet)
    apply_values(sheet)
    old_maximum = sheet["derived"]["pvMax"]
    new_maximum = 60 + 5 * sheet["stats"]["force"]
    sheet["derived"]["pvMax"] = new_maximum
    # Preserve damage already recorded; a full-health source remains at full health.
    if sheet["derived"]["pvActuels"] == old_maximum:
        sheet["derived"]["pvActuels"] = new_maximum


def publish(source: Path, difficulty: float, *, root: Path = ROOT) -> dict:
    """Stage and validate a new archive, call Gemini once, then install archive and metadata."""
    if not 0.5 <= difficulty <= 5 or difficulty * 2 != int(difficulty * 2):
        raise ValueError("Difficulty must be between 0.5 and 5 in half-point increments")
    original = character_from_archive(source)
    identifier = slugify_character_id(original.identity.nom)
    final = root / "Final"
    destination = final / f"{identifier}.zip"
    metadata_path = root / "web/catalog-metadata.json"
    document = json.loads(metadata_path.read_text(encoding="utf-8"))
    for existing in final.glob("*.zip"):
        character = character_from_archive(existing)
        if character.id == identifier or slugify_character_id(character.identity.nom) == identifier:
            raise FileExistsError(f"Character already published: {character.identity.nom}")
    if identifier in document["characters"] or destination.exists():
        raise FileExistsError(f"Character metadata or archive already exists: {identifier}")
    final.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".publish-", dir=final) as work:
        staging = Path(work)
        result = normalize_character_archive(source, staging)
        rewrite(result.destination, staging / "backup", prepare_sheet)
        character = character_from_archive(result.destination)
        config = replace(GeminiConfig.from_env(root / ".env"), max_attempts=1, request_timeout_seconds=90)
        extractor = GeminiCharacterDocumentExtractor(config)
        metadata = extractor.extract_catalog_metadata_from_json(character_to_json(character, indent=None)).model_dump(mode="json", by_alias=True)
        metadata["difficulty"] = difficulty
        for key in ("loreSummary", "gameplaySummary", "creator"):
            metadata[key] = " ".join(metadata[key].split())
        if any(value not in document["classVocabulary"] for value in metadata["class"]):
            raise ValueError("Gemini returned an unknown class")
        with zipfile.ZipFile(result.destination, "a", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
        document["characters"][identifier] = metadata
        # The source stays untouched and no existing canonical archive is overwritten.
        shutil.copy2(result.destination, destination)
        try:
            temporary = metadata_path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(metadata_path)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    print(f"[READY] {character.identity.nom}: {result.image_count} images; {source.stat().st_size} -> {destination.stat().st_size} bytes")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return metadata


def main() -> None:
    """Read the targeted source and explicit difficulty; never process unrelated archives."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--difficulty", type=float, required=True)
    args = parser.parse_args()
    publish(args.source, args.difficulty)


if __name__ == "__main__":
    main()

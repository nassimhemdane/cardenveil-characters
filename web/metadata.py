"""Manage the central catalogue metadata and synchronize it into character archives."""

from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path

from cardenveil.serialization import character_from_archive

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "Final"
METADATA_PATH = ROOT / "web" / "catalog-metadata.json"


def load_document() -> dict[str, object]:
    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


def initialize_entries() -> None:
    document = load_document()
    characters = document.setdefault("characters", {})
    for archive in sorted(FINAL.glob("*.zip")):
        character = character_from_archive(archive)
        characters.setdefault(
            character.id,
            {
                "loreSummary": "",
                "gameplaySummary": "",
                "difficulty": None,
                "creator": "",
                "class": [],
            },
        )
    METADATA_PATH.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Metadata initialized for {len(characters)} characters")


def validate() -> None:
    document = load_document()
    allowed = set(document.get("classVocabulary", []))
    for character_id, metadata in document.get("characters", {}).items():
        difficulty = metadata.get("difficulty")
        if difficulty is not None and (
            not isinstance(difficulty, (int, float))
            or not 0.5 <= difficulty <= 5
            or difficulty * 2 != int(difficulty * 2)
        ):
            raise ValueError(f"Difficulté invalide pour {character_id}: {difficulty!r}")
        character_classes = metadata.get("class", [])
        if isinstance(character_classes, str):
            character_classes = [character_classes] if character_classes else []
        if not isinstance(character_classes, list) or any(
            not isinstance(item, str) or item not in allowed for item in character_classes
        ):
            raise ValueError(
                f"Classe non normalisée pour {character_id}: {character_classes!r}"
            )
    print("Metadata validation: OK")


def sync_archives() -> None:
    validate()
    document = load_document()
    metadata_by_id = document.get("characters", {})
    for archive_path in sorted(FINAL.glob("*.zip")):
        character = character_from_archive(archive_path)
        metadata = metadata_by_id.get(character.id, {})
        with tempfile.NamedTemporaryFile(
            prefix=f".{character.id}-", suffix=".zip", dir=FINAL, delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        try:
            with zipfile.ZipFile(archive_path, "r") as source, zipfile.ZipFile(
                temporary_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9
            ) as destination:
                for info in source.infolist():
                    if info.filename.casefold() != "metadata.json":
                        destination.writestr(info, source.read(info.filename))
                destination.writestr(
                    "metadata.json",
                    json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                )
            temporary_path.replace(archive_path)
        finally:
            temporary_path.unlink(missing_ok=True)
    print(f"Synchronized metadata into {len(list(FINAL.glob('*.zip')))} archives")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("init", "validate", "sync"))
    args = parser.parse_args()
    {"init": initialize_entries, "validate": validate, "sync": sync_archives}[args.command]()


if __name__ == "__main__":
    main()

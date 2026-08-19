"""Contract tests against every character archive supplied as a reference."""

import json
import zipfile
from pathlib import Path

import pytest

from cardenveil.serialization import character_from_archive, character_to_dict

REFERENCES = Path(__file__).parents[1] / "References" / "Expected"
ARCHIVES = sorted(REFERENCES.glob("*.zip"))


def _archive_json(path: Path) -> dict[str, object]:
    """Read the original JSON object without passing through core code."""

    with zipfile.ZipFile(path) as archive:
        filename = next(name for name in archive.namelist() if name.endswith(".rpsheet.json"))
        payload = json.loads(archive.read(filename).decode("utf-8-sig"))
    assert isinstance(payload, dict)
    return payload


@pytest.mark.parametrize("archive_path", ARCHIVES, ids=lambda path: path.stem)
def test_every_reference_archive_has_an_exact_one_to_one_roundtrip(
    archive_path: Path,
) -> None:
    """Prove that no key, value, HTML fragment, or scalar type changes in a roundtrip."""

    original = _archive_json(archive_path)
    character = character_from_archive(archive_path)
    assert character_to_dict(character) == original


def test_load_all_reference_characters_and_display_them() -> None:
    """Load all supplied characters and print a useful inventory for manual inspection."""

    characters = [character_from_archive(path) for path in ARCHIVES]
    for character in characters:
        print(
            f"{character.id}: {character.identity.nom} | "
            f"capacités={len(character.capacities)} | "
            f"armes={len(character.weapons)} | inventaire={len(character.inventoryItems)}"
        )
    assert len(characters) == 6
    names = {character.identity.nom for character in characters}
    assert {"Agaric", "Haykel, the bone eater", "Waldemar"} <= names

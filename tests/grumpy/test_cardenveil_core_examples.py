"""Executable examples for Grumpy's integration with cardenveil-core."""

import pytest

from cardenveil import CardenveilCore, Character, FileCharacterRepository
from cardenveil.domain import (
    SheetIdentity,
    SheetProgression,
    SheetStats,
    SheetWeapon,
)
from cardenveil.errors import SerializationError, ValidationError
from cardenveil.serialization import (
    character_from_archive,
    character_from_json,
    character_to_archive,
    character_to_json,
)
from cardenveil.validation import Severity, validate_character


@pytest.fixture
def grumpy_character() -> Character:
    """Build a small but useful character with the standard 52 stat points."""

    return Character(
        id="grumpy-hero",
        identity=SheetIdentity(
            nom="Grumpy",
            joueur="Développeur",
            niveau=1,
            race="Humain",
            alignement="Neutre Bon",
        ),
        stats=SheetStats(force=14, agilite=12, esprit=16, social=10),
        progression=SheetProgression(xpDepenses=0, xpDisponibles=5),
        weapons=[SheetWeapon(nom="Épée longue", de="1d8", notes="Polyvalente")],
        notes="Personnage créé par les tests d'exemple.",
    )


def test_create_and_validate_character(grumpy_character: Character) -> None:
    """A standard character can be constructed and has no validation issue."""

    assert grumpy_character.identity.nom == "Grumpy"
    assert grumpy_character.stats.esprit == 16
    assert grumpy_character.weapons[0].nom == "Épée longue"

    result = validate_character(grumpy_character)
    assert result.is_valid
    assert result.issues == ()


def test_nonstandard_stat_total_produces_a_warning() -> None:
    """Validation reports imported/evolved stat totals without rejecting the sheet."""

    character = Character(id="veteran", stats=SheetStats(20, 20, 20, 20))

    result = validate_character(character)

    assert result.is_valid
    assert len(result.issues) == 1
    assert result.issues[0].severity is Severity.WARNING
    assert result.issues[0].code == "stats.total.nonstandard"


def test_json_round_trip_is_lossless(grumpy_character: Character) -> None:
    """The canonical JSON serializer preserves the complete dataclass tree."""

    payload = character_to_json(grumpy_character)
    restored = character_from_json(payload)

    assert '"id": "grumpy-hero"' in payload
    assert restored == grumpy_character


def test_unknown_json_field_is_rejected(grumpy_character: Character) -> None:
    """Schema drift is visible instead of silently discarding unknown data."""

    payload = character_to_json(grumpy_character)
    payload = payload.replace('"schemaVersion": 1', '"unknownField": true, "schemaVersion": 1')

    with pytest.raises(SerializationError, match="Unknown field"):
        character_from_json(payload)


def test_repository_saves_loads_and_lists(tmp_path, grumpy_character: Character) -> None:
    """The application facade persists one canonical JSON file per character."""

    core = CardenveilCore(FileCharacterRepository(tmp_path / "characters"))

    saved_path = core.save_character(grumpy_character)

    assert saved_path.name == "grumpy-hero.rpsheet.json"
    assert core.load_character("grumpy-hero") == grumpy_character
    assert core.load_all_characters() == [grumpy_character]


def test_repository_rejects_unsafe_character_id(tmp_path) -> None:
    """A character ID cannot escape the configured storage directory."""

    core = CardenveilCore(FileCharacterRepository(tmp_path))

    with pytest.raises(ValidationError, match="Unsafe character ID"):
        core.save_character(Character(id="../outside"))


def test_zip_archive_round_trip(tmp_path, grumpy_character: Character) -> None:
    """A character without image assets can be exchanged as a standalone ZIP."""

    archive = character_to_archive(grumpy_character, tmp_path / "grumpy-hero.zip")

    assert archive.is_file()
    assert character_from_archive(archive) == grumpy_character

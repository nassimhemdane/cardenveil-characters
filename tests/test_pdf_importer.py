"""Offline tests for the provider-neutral PDF import pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from cardenveil import CharacterSheet
from cardenveil.importers.pdf.errors import (
    CharacterExtractionError,
    CharacterImportError,
    CharacterMappingError,
)
from cardenveil.importers.pdf.importer import CharacterPDFImporter
from cardenveil.importers.pdf.mapper import CharacterMapper
from cardenveil.importers.pdf.models import (
    ExtractedAbility,
    ExtractedCardSuit,
    ExtractedCharacter,
    ExtractedDefense,
    ExtractedEquipment,
    ExtractedEquipmentPiece,
    ExtractedIdentity,
    ExtractedNarrative,
    ExtractedResources,
    ExtractedSkill,
    ExtractedSkillId,
    ExtractedStats,
    ExtractedWeapon,
)


class FakeCharacterDocumentExtractor:
    """Deterministic fake returning prevalidated extraction data without network calls."""

    def __init__(self, result: ExtractedCharacter) -> None:
        """Store the extraction returned for every valid PDF."""

        self.result = result
        self.paths: list[Path] = []

    def extract(self, pdf_path: Path) -> ExtractedCharacter:
        """Record the path and return the configured extraction."""

        self.paths.append(pdf_path)
        return self.result


class FailingExtractor:
    """Fake provider simulating an unexpected third-party exception."""

    def extract(self, pdf_path: Path) -> ExtractedCharacter:
        """Raise a raw provider exception for translation testing."""

        raise RuntimeError(f"provider failed for {pdf_path.name}")


def _pdf(tmp_path: Path, name: str = "Mimyr.pdf") -> Path:
    """Create a minimal signature-valid PDF fixture for importer boundary tests."""

    path = tmp_path / name
    path.write_bytes(b"%PDF-1.7\n%%EOF\n")
    return path


def _extracted_character() -> ExtractedCharacter:
    """Build a rich semantic extraction covering every mapper branch."""

    return ExtractedCharacter(
        identity=ExtractedIdentity(
            nom="Éléonore du Val",
            joueur="Nassim",
            niveau=4,
            race="Aasimar",
            alignement="Chaotique Bon",
            age="38",
        ),
        stats=ExtractedStats(force=16, agilite=8, esprit=16, social=6),
        skills=[
            ExtractedSkill(id=ExtractedSkillId.ATHLETISME, trained=True, bonus=3),
            ExtractedSkill(id=ExtractedSkillId.ARCANES, trained=True, bonus=3),
        ],
        weapons=[ExtractedWeapon(nom="Épée longue", de="1d8", notes="Garde")],
        capacities=[
            ExtractedAbility(
                name="Lame radiante",
                prepared=True,
                description="Enchante une arme.",
                value_main="+ Mod Esprit",
                color=ExtractedCardSuit.HEART,
                base_cost=11,
                reduced_cost=5,
                incantation="Esprit",
                usage="Bonus action",
            )
        ],
        narrative=ExtractedNarrative(
            background="Soldat enrôlé de force.",
            objectif="Créer une magie propre.",
            traitsSpeciaux=["Résistance radiante."],
        ),
        defense=ExtractedDefense(parade="8", armure=2),
        resources=ExtractedResources(or_="20", rations=2, token_force=3, token_esprit=3),
        equipment=ExtractedEquipment(
            plastron=ExtractedEquipmentPiece(nom="Plastron", deflexion=2, armure=2)
        ),
        notes="Valeurs copiées sans recalcul.",
    )


def test_fake_extractor_maps_to_real_character_sheet_and_writes_debug(tmp_path: Path) -> None:
    """Exercise PDF validation, fake extraction, complete mapping, and debug artifacts."""

    pdf = _pdf(tmp_path)
    fake = FakeCharacterDocumentExtractor(_extracted_character())
    mapper = CharacterMapper(clock=lambda: datetime(2026, 8, 18, 12, tzinfo=UTC))
    debug = tmp_path / "debug"
    sheet = CharacterPDFImporter(fake, mapper, debug).load(pdf)

    assert isinstance(sheet, CharacterSheet)
    assert sheet.id == "eleonore-du-val"
    assert sheet.identity.nom == "Éléonore du Val"
    assert sheet.stats.force == 16
    assert sheet.skills.athletisme.trained
    assert sheet.capacities[0].cost.base == 11
    assert sheet.capacities[0].cost.incantationReduction == 6
    assert sheet.equipment.plastron.armure == 2
    assert fake.paths == [pdf]
    assert (debug / "extracted_character.json").is_file()
    assert (debug / "character_sheet.json").is_file()
    assert '"or"' in (debug / "extracted_character.json").read_text(encoding="utf-8")
    assert '"or_"' not in (debug / "extracted_character.json").read_text(encoding="utf-8")


def test_partial_extraction_maps_unknown_values_without_semantic_invention(tmp_path: Path) -> None:
    """Unknown fields become required sheet blanks while the PDF filename supplies an ID."""

    sheet = CharacterPDFImporter(
        FakeCharacterDocumentExtractor(ExtractedCharacter()),
        CharacterMapper(clock=lambda: datetime(2026, 1, 1, tzinfo=UTC)),
    ).load(_pdf(tmp_path, "Personnage inconnu.pdf"))
    assert sheet.id == "personnage-inconnu"
    assert sheet.identity.nom == ""
    assert sheet.stats.force == 0
    assert sheet.capacities == []
    assert sheet.portrait == ""


@pytest.mark.parametrize("name", ["missing.pdf", "character.txt"])
def test_missing_or_wrong_file_is_rejected_before_extraction(tmp_path: Path, name: str) -> None:
    """Reject invalid input paths without invoking a provider."""

    path = tmp_path / name
    if path.suffix == ".txt":
        path.write_text("not a PDF", encoding="utf-8")
    with pytest.raises(CharacterImportError):
        CharacterPDFImporter(FakeCharacterDocumentExtractor(ExtractedCharacter())).load(path)


def test_invalid_pdf_signature_is_rejected(tmp_path: Path) -> None:
    """A renamed non-PDF must not consume provider quota."""

    path = tmp_path / "fake.pdf"
    path.write_text("not really a PDF", encoding="utf-8")
    with pytest.raises(CharacterImportError, match="signature"):
        CharacterPDFImporter(FakeCharacterDocumentExtractor(ExtractedCharacter())).load(path)


def test_invalid_stat_and_enum_fail_pydantic_validation() -> None:
    """Structured extraction rejects out-of-range scores and uncontrolled suit strings."""

    with pytest.raises(ValidationError):
        ExtractedStats(force=21)
    with pytest.raises(ValidationError):
        ExtractedAbility(color="coeur")  # type: ignore[arg-type]


def test_duplicate_skill_mapping_is_explicitly_rejected(tmp_path: Path) -> None:
    """Prevent an ambiguous extraction from silently overwriting a skill."""

    skill = ExtractedSkill(id=ExtractedSkillId.ARCANES, trained=True)
    extracted = ExtractedCharacter(skills=[skill, skill])
    with pytest.raises(CharacterMappingError, match="Duplicate"):
        CharacterPDFImporter(FakeCharacterDocumentExtractor(extracted)).load(_pdf(tmp_path))


def test_unexpected_provider_exception_is_wrapped(tmp_path: Path) -> None:
    """Raw provider exceptions never leak through the orchestration boundary."""

    with pytest.raises(CharacterExtractionError) as captured:
        CharacterPDFImporter(FailingExtractor()).load(_pdf(tmp_path))
    assert isinstance(captured.value.__cause__, RuntimeError)

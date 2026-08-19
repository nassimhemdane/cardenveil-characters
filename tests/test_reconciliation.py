"""Offline tests for name matching, binary review files, and validated archive fixes."""

from __future__ import annotations

import zipfile
from datetime import UTC, datetime
from pathlib import Path

from cardenveil.domain import Character, SheetIdentity, SheetStats
from cardenveil.importers.pdf.mapper import CharacterMapper
from cardenveil.importers.pdf.models import ExtractedCharacter
from cardenveil.reconciliation import (
    comparison_issues,
    index_archives_by_character_name,
    parse_review_report,
    patch_character_archive,
    render_review_report,
)
from cardenveil.serialization import character_from_archive, character_to_archive


def test_archive_index_uses_character_name_instead_of_filename(tmp_path: Path) -> None:
    """A misleading ZIP filename must not influence identity matching."""

    character = Character(id="azella", identity=SheetIdentity(nom="Azélla du Lac"))
    archive = character_to_archive(character, tmp_path / "totally-unrelated-name.zip")

    index = index_archives_by_character_name(tmp_path)

    assert index == {"azella-du-lac": archive}


def test_review_round_trip_and_archive_patch_preserve_assets(tmp_path: Path) -> None:
    """A checked PDF value is parsed, core-validated, and leaves ZIP assets untouched."""

    current = Character(
        id="agaric",
        identity=SheetIdentity(nom="Agaric"),
        stats=SheetStats(force=8, agilite=9, esprit=10, social=11),
    )
    final_archive = character_to_archive(current, tmp_path / "different-file-name.zip")
    with zipfile.ZipFile(final_archive, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("assets/agaric/portrait.png", b"compressed-image")

    extracted = ExtractedCharacter.model_validate(
        {"identity": {"nom": "Agaric"}, "stats": {"force": 12}}
    )
    candidate = CharacterMapper(clock=lambda: datetime(2026, 1, 1, tzinfo=UTC)).map(
        extracted, Path("wrong-source-name.pdf")
    )
    issues = comparison_issues(
        extracted=extracted,
        candidate=candidate,
        current=current,
        source_pdf=Path("wrong-source-name.pdf"),
        target_archive=final_archive,
        candidate_archive=Path("Candidates/agaric.zip"),
    )
    assert [issue.json_path for issue in issues] == ["/stats/force"]

    report = render_review_report(issues, tmp_path / "INCOHERENCES.md")
    report.write_text(
        report.read_text(encoding="utf-8").replace("- [ ] B —", "- [x] B —", 1),
        encoding="utf-8",
    )
    decisions = parse_review_report(report)
    assert len(decisions) == 1
    assert decisions[0].choice == "B"

    patch_character_archive(
        final_archive,
        [(decisions[0].issue.json_path, decisions[0].issue.option_b_value)],
    )
    assert character_from_archive(final_archive).stats.force == 12
    with zipfile.ZipFile(final_archive) as archive:
        assert archive.read("assets/agaric/portrait.png") == b"compressed-image"


def test_unextracted_default_values_do_not_create_false_inconsistencies(tmp_path: Path) -> None:
    """Mapper defaults for absent PDF fields must never be proposed as corrections."""

    extracted = ExtractedCharacter.model_validate({"identity": {"nom": "Mimyr"}})
    candidate = CharacterMapper(clock=lambda: datetime(2026, 1, 1, tzinfo=UTC)).map(
        extracted, Path("mimyr.pdf")
    )
    current = Character(
        id="mimyr",
        identity=SheetIdentity(nom="Mimyr"),
        stats=SheetStats(force=17, agilite=15, esprit=13, social=11),
    )

    assert comparison_issues(
        extracted=extracted,
        candidate=candidate,
        current=current,
        source_pdf=Path("mimyr.pdf"),
        target_archive=tmp_path / "mimyr.zip",
        candidate_archive=Path("Candidates/mimyr.zip"),
    ) == []

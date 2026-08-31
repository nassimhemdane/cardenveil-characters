"""Regression tests for the deterministic two-page printable sheet export."""

from __future__ import annotations

import zipfile

import pytest

from cardenveil.domain import (
    AbilityCost,
    AbilityValue,
    Character,
    SheetCapacity,
    SheetIdentity,
    SheetNarrative,
    SheetStats,
    SheetTotem,
)
from cardenveil.exporters import character_archive_to_pdf
from cardenveil.serialization import character_to_json

pymupdf = pytest.importorskip("pymupdf")


def test_archive_export_is_complete_white_two_page_a4_pdf(tmp_path) -> None:
    """Keep all sheet content printable while excluding catalogue-only metadata."""

    character = Character(
        id="eclaireuse",
        identity=SheetIdentity(
            nom="Éclaireuse d'Été",
            joueur="Nassim",
            niveau=4,
            race="Humaine",
            alignement="Neutre bon",
        ),
        stats=SheetStats(12, 18, 14, 10),
        totem=SheetTotem("Renard solaire", "Guide ses alliés dans la brume."),
        narrative=SheetNarrative(
            background="Cartographe des frontières.",
            objectif="Retrouver la cité perdue.",
            traitsSpeciaux=["Vision nocturne", "Pas silencieux"],
        ),
        capacities=[
            SheetCapacity(
                name=f"Capacité exhaustive d’urgence {index}",
                prepared=index % 2 == 0,
                description=(
                    "Une description volontairement détaillée qui vérifie le retour à la ligne "
                    "et la présence de chaque capacité dans le document final."
                ),
                value=AbilityValue("2d8", "+2"),
                cost=AbilityCost("heart", 12, 2, 1, 1, 1, 7),
                incantation="Esprit",
                save="Résilience (moitié)",
                usage="Action / Concentration",
            )
            for index in range(1, 11)
        ],
        notes="MARQUEUR_FICHE_VISIBLE",
    )
    archive_path = tmp_path / "eclaireuse.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("eclaireuse.rpsheet.json", character_to_json(character))

    output = character_archive_to_pdf(archive_path, tmp_path / "eclaireuse.pdf")

    with pymupdf.open(output) as document:
        assert len(document) == 2
        assert all(page.rect.width == pytest.approx(595.276, abs=0.1) for page in document)
        assert all(page.rect.height == pytest.approx(841.89, abs=0.1) for page in document)
        text = "\n".join(page.get_text() for page in document).replace("\N{NO-BREAK SPACE}", " ")
        assert "Éclaireuse d'Été" in text
        assert "Renard solaire" in text
        assert "MARQUEUR_FICHE_VISIBLE" in text
        assert all(f"Capacité exhaustive d'urgence {index}" in text for index in range(1, 11))
        assert "loreSummary" not in text
        assert "gameplaySummary" not in text
        for page in document:
            corner = page.get_pixmap(clip=pymupdf.Rect(0, 0, 2, 2), alpha=False)
            assert set(corner.samples) == {255}

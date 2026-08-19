"""Offline tests for local PDF image extraction and compression."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from cardenveil.domain import CharacterSheet, SheetCapacity
from cardenveil.importers.pdf import PDFImageAssetExtractor
from cardenveil.serialization import character_from_archive, character_to_archive, character_to_json


def test_extracts_names_compresses_and_serializes_all_edmound_assets(tmp_path: Path) -> None:
    """Extract real embedded images using the exact asset paths expected by rpsheet JSON."""

    pytest.importorskip("pymupdf")
    image_module = pytest.importorskip("PIL.Image")
    pdf = Path(__file__).parents[1] / "References" / "Pdf" / "Fiche Edmound finale.pdf"
    sheet = CharacterSheet(
        id="edmound",
        capacities=[SheetCapacity(name=f"Capacity {index}") for index in range(1, 10)],
    )

    result = PDFImageAssetExtractor(tmp_path / "assets").extract(pdf, sheet)

    assert result.warnings == ()
    assert len(result.files) == 11
    assert sheet.portrait == "/assets/edmound/portrait.png"
    assert sheet.totem.image == "/assets/edmound/totem.png"
    assert [capacity.image for capacity in sheet.capacities] == [
        f"/assets/edmound/capacity-{index}.png" for index in range(1, 10)
    ]
    assert sum(path.stat().st_size for path in result.files) < 1_200_000

    for path in result.files:
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        with image_module.open(path) as image:
            limit = 512 if path.name == "portrait.png" else 384
            assert max(image.size) <= limit

    serialized = json.loads(character_to_json(sheet))
    assert serialized["portrait"] == "/assets/edmound/portrait.png"
    assert serialized["totem"]["image"] == "/assets/edmound/totem.png"
    assert serialized["capacities"][8]["image"] == "/assets/edmound/capacity-9.png"

    archive_path = character_to_archive(
        sheet,
        tmp_path / "edmound.zip",
        asset_root=tmp_path / "assets",
    )
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        assert names[0] == "edmound.rpsheet.json"
        assert "assets/edmound/portrait.png" in names
        assert "assets/edmound/totem.png" in names
        assert "assets/edmound/capacity-9.png" in names
        assert len([name for name in names if name.endswith(".png")]) == 11
    assert character_from_archive(archive_path) == sheet

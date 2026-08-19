"""Tests for the no-Gemini first-pass character archive normalizer."""

from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path

import pytest

from cardenveil.domain import CharacterSheet, SheetCapacity, SheetIdentity, SheetTotem
from cardenveil.importers.archive import normalize_character_archive
from cardenveil.serialization import character_from_archive, character_to_json


def _large_png() -> bytes:
    """Build deterministic noisy PNG bytes that benefit from migration compression."""

    image_module = pytest.importorskip("PIL.Image")
    image = image_module.effect_noise((800, 800), 96).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _source_archive(path: Path) -> None:
    """Create one legacy archive combining external assets and an embedded data URI."""

    image = _large_png()
    encoded = base64.b64encode(image).decode("ascii")
    character = CharacterSheet(
        id="nouveau-personnage-123",
        identity=SheetIdentity(nom="Éléonore du Val"),
        portrait="/assets/nouveau-personnage-123/portrait.png",
        totem=SheetTotem(image=f"data:application/octet-stream;base64,{encoded}"),
        capacities=[
            SheetCapacity(
                name="Capacité",
                image="/assets/nouveau-personnage-123/capacity-1.png",
            )
        ],
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("nouveau-personnage-123.rpsheet.json", character_to_json(character))
        archive.writestr("assets/nouveau-personnage-123/portrait.png", image)
        archive.writestr("assets/nouveau-personnage-123/capacity-1.png", image)


def test_normalizer_roundtrips_renames_externalizes_compresses_and_skips(tmp_path: Path) -> None:
    """Cover canonical roundtrip, image variants, naming, compression, skip, and overwrite."""

    source = tmp_path / "legacy.zip"
    output = tmp_path / "Final"
    _source_archive(source)

    created = normalize_character_archive(source, output)

    assert created.status == "created"
    assert created.destination.name == "eleonore-du-val.zip"
    assert created.image_count == 3
    assert created.normalized_bytes < created.original_bytes / 3
    normalized = character_from_archive(created.destination)
    assert normalized.id == "eleonore-du-val"
    assert normalized.portrait == "/assets/eleonore-du-val/portrait.png"
    assert normalized.totem.image == "/assets/eleonore-du-val/totem.png"
    assert normalized.capacities[0].image == "/assets/eleonore-du-val/capacity-1.png"
    with zipfile.ZipFile(created.destination) as archive:
        assert "eleonore-du-val.rpsheet.json" in archive.namelist()
        assert "assets/eleonore-du-val/portrait.png" in archive.namelist()
        assert "assets/eleonore-du-val/totem.png" in archive.namelist()
        assert "assets/eleonore-du-val/capacity-1.png" in archive.namelist()

    skipped = normalize_character_archive(source, output)
    assert skipped.status == "skipped"
    overwritten = normalize_character_archive(source, output, overwrite=True)
    assert overwritten.status == "overwritten"

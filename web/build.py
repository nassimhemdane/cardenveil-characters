"""Generate the static Cardenveil character catalogue from canonical archives."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from cardenveil.serialization import character_from_archive, character_to_dict

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "Final"
WEB = ROOT / "web"
PUBLIC = WEB / "public"
DATA = PUBLIC / "data"
ASSETS = PUBLIC / "assets"
DOWNLOADS = PUBLIC / "downloads"


def _copy_asset(archive: zipfile.ZipFile, reference: str) -> str:
    if not reference or not reference.startswith("/assets/"):
        return ""
    member = reference.lstrip("/")
    actual = {name.casefold(): name for name in archive.namelist()}.get(member.casefold())
    if actual is None:
        return ""
    target = PUBLIC / member
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(archive.read(actual))
    return "/" + member.replace("\\", "/")


def build() -> None:
    metadata_path = WEB / "catalog-metadata.json"
    metadata_document = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata = metadata_document.get("characters", {})
    allowed_classes = set(metadata_document.get("classVocabulary", []))
    DATA.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    characters: list[dict[str, object]] = []

    for source in sorted(FINAL.glob("*.zip")):
        character = character_from_archive(source)
        payload = character_to_dict(character)
        with zipfile.ZipFile(source) as archive:
            payload["portrait"] = _copy_asset(archive, character.portrait)
            payload["totem"]["image"] = _copy_asset(archive, character.totem.image)
            for capacity, original in zip(payload["capacities"], character.capacities, strict=True):
                capacity["image"] = _copy_asset(archive, original.image)
        catalog = metadata.get(character.id, {})
        character_classes = catalog.get("class", [])
        if isinstance(character_classes, str):
            character_classes = [character_classes] if character_classes else []
        if not isinstance(character_classes, list) or any(
            item not in allowed_classes for item in character_classes
        ):
            raise ValueError(
                f"Classe non normalisée pour {character.id}: {character_classes!r}"
            )
        payload["catalog"] = catalog
        payload["download"] = f"/downloads/{source.name}"
        characters.append(payload)
        shutil.copy2(source, DOWNLOADS / source.name)

    (DATA / "characters.json").write_text(
        json.dumps(characters, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    headers = WEB / "_headers"
    if headers.is_file():
        shutil.copy2(headers, PUBLIC / "_headers")
    print(f"Generated {len(characters)} characters in {PUBLIC}")


if __name__ == "__main__":
    build()

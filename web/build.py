"""Generate the static Cardenveil character catalogue from canonical archives."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

from rules_pages import build_rules
from static_pages import character_url, write_character, write_index

from cardenveil.serialization import character_from_archive, character_to_dict

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "Final"
WEB = ROOT / "web"
PUBLIC = WEB / "public"
DATA = PUBLIC / "data"
ASSETS = PUBLIC / "assets"
DOWNLOADS = PUBLIC / "downloads"


def _write_versioned_asset(member: str, content: bytes) -> str:
    """Give every image a content-derived URL so cached portraits never go stale."""
    path = Path(member)
    digest = hashlib.sha256(content).hexdigest()[:16]
    versioned = path.with_name(f"{path.stem}.{digest}{path.suffix}")
    target = PUBLIC / versioned
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return "/" + versioned.as_posix()


def _copy_asset(
    archive: zipfile.ZipFile,
    reference: str,
    fallback_member: str,
) -> str:
    if not reference:
        return ""
    if reference.startswith("data:"):
        header, separator, payload = reference.partition(",")
        if not separator or ";base64" not in header:
            raise ValueError(f"Image data URI non prise en charge: {header!r}")
        try:
            content = base64.b64decode(payload, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("Image base64 invalide dans une archive") from error
        return _write_versioned_asset(fallback_member, content)
    if not reference.startswith("/assets/"):
        return ""
    member = reference.lstrip("/")
    actual = {name.casefold(): name for name in archive.namelist()}.get(member.casefold())
    if actual is None:
        return ""
    return _write_versioned_asset(member, archive.read(actual))


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
            payload["portrait"] = _copy_asset(
                archive, character.portrait, f"assets/{character.id}/portrait.png"
            )
            payload["totem"]["image"] = _copy_asset(
                archive, character.totem.image, f"assets/{character.id}/totem.png"
            )
            for index, (capacity, original) in enumerate(
                zip(payload["capacities"], character.capacities, strict=True), start=1
            ):
                capacity["image"] = _copy_asset(
                    archive,
                    original.image,
                    f"assets/{character.id}/capacity-{index}.png",
                )
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
        payload["printUrl"] = f"/print.html?character={character.id}"
        payload["pageUrl"] = character_url(character.id)
        write_character(PUBLIC, payload)
        characters.append(payload)
        shutil.copy2(source, DOWNLOADS / source.name)

    (DATA / "characters.json").write_text(
        json.dumps(characters, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    # Small server-side recommendation context: no image data or full sheet parsing per request.
    recommendations = []
    for character in characters:
        catalog = character.get("catalog", {})
        facts = [catalog.get("gameplaySummary"), catalog.get("loreSummary"),
                 character.get("totem", {}).get("description"),
                 *[f"{a['name']}: {a['description']}" for a in character.get("capacities", [])]]
        recommendations.append({"id": character["id"], "name": character["identity"]["nom"],
            "difficulty": catalog.get("difficulty"), "classes": catalog.get("class", []),
            "facts": re.sub(r"\s+", " ", " | ".join(str(v) for v in facts if v))[:1100]})
    (DATA / "recommendation-catalog.json").write_text(
        json.dumps(recommendations, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    write_index(PUBLIC, characters)
    build_rules(ROOT, PUBLIC)
    headers = WEB / "_headers"
    if headers.is_file():
        shutil.copy2(headers, PUBLIC / "_headers")
    print(f"Generated {len(characters)} characters in {PUBLIC}")


if __name__ == "__main__":
    build()

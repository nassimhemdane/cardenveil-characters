"""Apply the October character assets and remove empty equipment labels with backups."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
import zipfile
from datetime import UTC, datetime
from html import unescape
from pathlib import Path

from cardenveil.importers.archive import normalize_character_archive
from cardenveil.serialization import character_from_archive, character_from_json

ROOT = Path(__file__).resolve().parents[1]


def text(value: object) -> str:
    """Compare names and empty rich text without changing stored descriptions."""
    return unescape(re.sub(r"<[^>]*>", "", str(value))).strip()


def clean_equipment(sheet: dict) -> int:
    """Remove slot labels; retain real properties and the original seven-slot schema."""
    count = 0
    for slot, item in sheet["equipment"].items():
        name = text(item["nom"])
        generic = name.casefold() == slot.casefold()
        if generic or not name:
            before = dict(item)
            item["nom"] = ""
            meaningful = any(text(v) not in {"", "0", "0.0"} for k, v in item.items() if k != "nom")
            if not meaningful:
                for key in item:
                    item[key] = ""
            count += before != item
    return count


def rewrite(
    path: Path,
    backup: Path,
    update,
    assets: dict[str, bytes] | None = None,
    obsolete: set[str] | None = None,
) -> bool:
    """Atomically rewrite the sheet and selected assets while preserving other ZIP members."""
    assets = assets or {}
    obsolete = obsolete or set()
    with zipfile.ZipFile(path) as source:
        members = [i for i in source.infolist() if i.filename.endswith(".rpsheet.json")]
        if len(members) != 1:
            raise ValueError(f"Expected exactly one sheet in {path}")
        member = members[0].filename
        sheet = json.loads(source.read(member).decode("utf-8-sig"))
        original = json.dumps(sheet, sort_keys=True)
        update(sheet)
        payload = json.dumps(sheet, ensure_ascii=False, indent=2) + "\n"
        character_from_json(payload)
        obsolete = {name for name in obsolete if name in source.namelist() and name not in payload}
        if json.dumps(sheet, sort_keys=True) == original and not assets and not obsolete:
            return False
        backup.mkdir(parents=True, exist_ok=True)
        if not (backup / path.name).exists():
            shutil.copy2(path, backup / path.name)
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".zip", delete=False) as tmp:
            temporary = Path(tmp.name)
        try:
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as out:
                for info in source.infolist():
                    if info.filename == member:
                        out.writestr(info, payload.encode("utf-8"))
                    elif info.filename not in assets and info.filename not in obsolete:
                        out.writestr(info, source.read(info.filename))
                for name, content in assets.items():
                    out.writestr(name, content)
            with zipfile.ZipFile(temporary) as check:
                if check.testzip() is not None:
                    raise ValueError(f"Invalid rewritten ZIP: {path}")
                for name, content in assets.items():
                    assert check.read(name) == content
            character_from_archive(temporary)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(path)
    return True


def main() -> None:
    """Apply reviewed updates to Final; Luna requires one explicit name per source ability."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--luna-names", nargs="+")
    args = parser.parse_args()
    final = ROOT / "Final"
    modifications = ROOT / "modif2octobre"
    backup = final / "Backups" / ("october-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    if args.luna_names:
        luna = character_from_archive(modifications / "lunaUpdated.zip")
        if len(args.luna_names) != len(luna.capacities):
            raise ValueError("Provide exactly one name for each Luna ability")
        stage = final / "Candidates/october"
        result = normalize_character_archive(
            modifications / "lunaUpdated.zip", stage, overwrite=True
        )
        for ability, name in zip(luna.capacities, args.luna_names, strict=True):
            print(f"Luna: {ability.name} -> {name}")

        def rename(sheet):
            """Change names in source order, retaining every other ability property."""
            for ability, name in zip(sheet["capacities"], args.luna_names, strict=True):
                ability["name"] = name

        rewrite(result.destination, backup / "staged", rename)
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(final / "luna.zip", backup / "luna.zip")
        shutil.copy2(result.destination, final / "luna.zip")
        metadata_path = ROOT / "web/catalog-metadata.json"
        document = json.loads(metadata_path.read_text("utf-8"))
        document["characters"]["luna"]["difficulty"] = 4.5
        metadata_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", "utf-8")
        with zipfile.ZipFile(final / "luna.zip", "a", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "metadata.json",
                json.dumps(document["characters"]["luna"], ensure_ascii=False, indent=2),
            )
        print(f"Luna compression: {result.original_bytes} -> {result.normalized_bytes} bytes")
    for identifier, image in [
        ("afreaux-shaufeois", "Affreaux Shaufeois.jpg"),
        ("anain-proviste", "AnainProviste.jpg"),
    ]:
        reference = f"assets/{identifier}/portrait.jpg"

        def portrait(sheet, ref=reference):
            """Reference the original JPEG directly, without resizing or recompression."""
            sheet["portrait"] = "/" + ref

        rewrite(
            final / (identifier + ".zip"),
            backup,
            portrait,
            {reference: (modifications / image).read_bytes()},
            obsolete={f"assets/{identifier}/portrait.png"},
        )
        print(f"Portrait replaced losslessly: {identifier}")
    changed = 0
    for path in sorted(final.glob("*.zip")):
        if rewrite(path, backup, clean_equipment):
            print(f"Equipment labels cleaned: {path.name}")
            changed += 1
    print(f"Equipment: {changed} archives updated. Backups: {backup}")


if __name__ == "__main__":
    main()

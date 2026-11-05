"""Snapshot only the seven player-facing Fragmented Markdown documents and their images."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

DOCUMENTS = {
    "reference-rapide": "⚙ CARDENVEIL — RÉFÉRENCE RAPIDE.md",
    "systeme-de-base": "Système de Base.md",
    "creation": "Personnage.md",
    "combat": "Action et Combat.md",
    "capacites": "Totem, Capacités & Cartes 2b01af51d01280ceaa0fdcf7544cf212.md",
    "narration": "Système Narratif.md",
    "progression": "Système de progression.md",
}
EMBEDS = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]|!\[[^\]]*\]\(([^)]+)\)")
ROOT = Path(__file__).resolve().parents[1]


def resolve_image(reference: str, document: Path, vault: Path, by_name: dict) -> Path | None:
    """Resolve explicit paths before unique attachment names; never guess ambiguous matches."""
    relative = Path(unquote(reference).replace("\\", "/"))
    candidates = [document.parent / relative, vault / relative,
                  document.parent / "Personnage" / relative.name]
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate.is_relative_to(vault) and candidate.is_file():
            return candidate
    matches = by_name.get(relative.name.casefold(), [])
    return matches[0] if len(matches) == 1 else None


def sync(source: Path, destination: Path) -> dict:
    """Preserve exact source text and generate small, content-versioned WebP illustrations."""
    from PIL import Image, ImageOps

    source = source.resolve()
    vault = source.parent
    by_name: dict = defaultdict(list)
    for path in vault.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            by_name[path.name.casefold()].append(path)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "assets").mkdir(exist_ok=True)
    manifest = {"edition": "Cardenveil Fragmented", "documents": {}, "images": {}, "missingImages": []}
    total_original = total_compressed = 0
    for key, filename in DOCUMENTS.items():
        document = source / filename
        content = document.read_bytes()
        shutil.copy2(document, destination / f"{key}.md")
        manifest["documents"][key] = {"source": filename, "file": f"{key}.md", "sha256": hashlib.sha256(content).hexdigest()}
        for match in EMBEDS.finditer(content.decode("utf-8-sig")):
            reference = match[1] or match[2]
            if reference in manifest["images"] or reference in manifest["missingImages"]:
                continue
            path = resolve_image(reference, document, vault, by_name)
            if path is None:
                manifest["missingImages"].append(reference)
                continue
            with Image.open(path) as original:
                image = ImageOps.exif_transpose(original)
                image.thumbnail((900, 900), Image.Resampling.LANCZOS)
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                import io
                buffer = io.BytesIO()
                image.save(buffer, format="WEBP", quality=78, method=6)
                payload = buffer.getvalue()
                width, height = image.size
            filename = hashlib.sha256(payload).hexdigest()[:20] + ".webp"
            (destination / "assets" / filename).write_bytes(payload)
            manifest["images"][reference] = {"url": f"/assets/rules/{filename}", "file": f"assets/{filename}",
                                               "width": width, "height": height,
                                               "source": path.relative_to(vault).as_posix()}
            total_original += path.stat().st_size
            total_compressed += len(payload)
    (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {len(DOCUMENTS)} player documents; {len(manifest['images'])} illustrations: {total_original} -> {total_compressed} bytes")
    if manifest["missingImages"]:
        print("Missing image references:", json.dumps(manifest["missingImages"], ensure_ascii=False))
    return manifest


def main() -> None:
    """Require an explicit external folder; production builds use the versioned snapshot only."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/rules/fragmented")
    args = parser.parse_args()
    sync(args.source, args.output)


if __name__ == "__main__":
    main()

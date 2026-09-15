"""Extract local rule PDFs into versionable text, keeping document and page provenance."""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "introduction": "Cardenveil Fragmanted.pdf",
    "reference-rapide": "Cardenveil résumé.pdf",
    "systeme-de-base": "Cardenveil Systeme de base.pdf",
    "creation": "Cardenveil Personnage.pdf",
    "combat": "Cardenveil Action et Combat.pdf",
    "capacites": "Cardenveil Totem Capacités Cartes.pdf",
    "narration": "Cardenveil Systeme Naratif.pdf",
    "progression": "Cardenveil Système de progression.pdf",
}


def extract() -> None:
    """Copy text blocks verbatim; do not reconcile rules, invoke AI, or embed large images."""
    output = ROOT / "docs/rules/sources"
    output.mkdir(parents=True, exist_ok=True)
    for slug, filename in SOURCES.items():
        with pymupdf.open(ROOT / "RulesCardenveil" / filename) as pdf:
            pages = []
            for number, page in enumerate(pdf, 1):
                blocks = [
                    b[4].strip()
                    for b in page.get_text("blocks", sort=True)
                    if b[6] == 0 and b[4].strip()
                ]
                if not blocks:
                    raise ValueError(f"No text on {filename}, page {number}; manual review needed")
                pages.append({"number": number, "blocks": blocks})
            document = {"source": filename, "pages": pages}
            (output / f"{slug}.json").write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(f"{slug}: {len(pages)} pages")


if __name__ == "__main__":
    extract()

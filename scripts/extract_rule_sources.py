"""Extract local rule PDFs into versionable text, keeping document and page provenance."""

from __future__ import annotations

import json
from collections import Counter
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


def structured_page(page, body_size: float) -> list[dict]:
    """Recover headings and table cells from PDF geometry, retaining readable paragraphs."""
    tables = page.find_tables().tables
    elements = []
    for table in tables:
        elements.append({"kind": "table", "rows": table.extract(), "y": table.bbox[1]})
    for block in page.get_text("dict", sort=True)["blocks"]:
        if "lines" not in block:
            continue
        bounds = pymupdf.Rect(block["bbox"])
        if any(
            bounds.intersects(pymupdf.Rect(t.bbox))
            and (bounds & pymupdf.Rect(t.bbox)).get_area() > bounds.get_area() * 0.5
            for t in tables
        ):
            continue
        spans = [s for line in block["lines"] for s in line["spans"] if s["text"].strip()]
        if not spans:
            continue
        size = max(s["size"] for s in spans)
        if size <= 8 and bounds.y0 > page.rect.height * 0.85:
            continue
        value = " ".join(
            "".join(s["text"] for s in line["spans"]).strip() for line in block["lines"]
        ).strip()
        heading = size >= body_size * 1.15 and len(value) < 200
        level = 2 if size >= body_size * 1.45 else 3
        element = {
            "kind": "heading" if heading else "paragraph",
            "text": value,
            "y": bounds.y0,
            "bottom": bounds.y1,
        }
        if heading:
            element["level"] = level
        elements.append(element)
    elements.sort(key=lambda e: e["y"])
    merged = []
    for element in elements:
        # Some PDFs export one body line per block. Merge only close consecutive body blocks.
        if (
            merged
            and element["kind"] == merged[-1]["kind"] == "paragraph"
            and element["y"] - merged[-1].get("bottom", 0) < 7
        ):
            merged[-1]["text"] += " " + element["text"]
            merged[-1]["bottom"] = element["bottom"]
        else:
            merged.append(element)
    return [{k: v for k, v in e.items() if k not in {"y", "bottom"}} for e in merged]


def extract() -> None:
    """Copy text blocks verbatim; do not reconcile rules, invoke AI, or embed large images."""
    output = ROOT / "docs/rules/sources"
    output.mkdir(parents=True, exist_ok=True)
    for slug, filename in SOURCES.items():
        with pymupdf.open(ROOT / "RulesCardenveil" / filename) as pdf:
            sizes = Counter()
            for page in pdf:
                for block in page.get_text("dict")["blocks"]:
                    for line in block.get("lines", []):
                        for span in line["spans"]:
                            sizes[round(span["size"], 1)] += len(span["text"])
            body_size = sizes.most_common(1)[0][0]
            pages = []
            for number, page in enumerate(pdf, 1):
                blocks = [
                    b[4].strip()
                    for b in page.get_text("blocks", sort=True)
                    if b[6] == 0 and b[4].strip()
                ]
                if not blocks:
                    raise ValueError(f"No text on {filename}, page {number}; manual review needed")
                pages.append(
                    {
                        "number": number,
                        "blocks": blocks,
                        "elements": structured_page(page, body_size),
                    }
                )
            document = {"source": filename, "pages": pages}
            (output / f"{slug}.json").write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(f"{slug}: {len(pages)} pages")


if __name__ == "__main__":
    extract()

"""Explicit archive maintenance helpers; normal loading remains lossless."""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser


class PlainSheetText(HTMLParser):
    """Read rich text as paragraphs, excluding active markup and formatting attributes."""

    blocks = {"p", "div", "li", "h1", "h2", "h3", "h4", "tr", "blockquote"}
    blocked_tags = {"script", "style", "iframe", "object", "svg", "math"}

    def __init__(self) -> None:
        """Initialize the text collector and suppressed-element depth."""
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Replace structural markup with line breaks and drop formatting markup."""
        if tag in self.blocked_tags:
            self.hidden += 1
        elif not self.hidden:
            if tag in self.blocks or tag == "br":
                self.parts.append("\n")
            elif tag in {"td", "th"}:
                self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        """End paragraphs without concatenating adjacent words."""
        if tag in self.blocked_tags:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in self.blocks:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        """Retain original words, numbers, punctuation and accents."""
        if not self.hidden:
            self.parts.append(data)


def plain_sheet_text(value: str) -> str:
    """Remove HTML and encoded HTML while preserving mathematical comparison signs."""
    decoded = value
    for _ in range(3):
        updated = unescape(decoded)
        if updated == decoded:
            break
        decoded = updated
    if not re.search(r"</?[A-Za-z][^>]*>|<!--", decoded):
        return decoded.replace("\xa0", " ")
    parser = PlainSheetText()
    parser.feed(decoded)
    parser.close()
    lines = [line.strip() for line in "".join(parser.parts).replace("\xa0", " ").splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def normalize_sheet_text(value: object, key: str = "") -> object:
    """Clean all text recursively, keeping asset references and the exact JSON key structure."""
    if isinstance(value, dict):
        return {k: normalize_sheet_text(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_sheet_text(v, key) for v in value]
    if isinstance(value, str) and key not in {"image", "portrait"}:
        return plain_sheet_text(value)
    return value


def empty_sheet_gear(sheet: dict) -> None:
    """Clear equipped weapons, equipment and inventory, keeping slots and unrelated mechanics."""
    sheet["weapons"] = []
    sheet["inventoryItems"] = []
    for piece in sheet["equipment"].values():
        for key in piece:
            piece[key] = ""
    sheet["inventory"]["equipement"] = ""
    sheet["inventory"]["inventaire"] = ""


def normalize_and_empty_gear(sheet: dict) -> None:
    """Apply the explicitly requested cleanup to a mutable canonical sheet dictionary."""
    normalized = normalize_sheet_text(sheet)
    sheet.clear()
    sheet.update(normalized)
    empty_sheet_gear(sheet)

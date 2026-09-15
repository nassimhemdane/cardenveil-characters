"""Render complete, script-independent character documents from catalogue payloads."""

from __future__ import annotations

import json
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote


class SheetText(HTMLParser):
    """Retain basic sheet formatting while discarding attributes and active markup."""

    allowed = {"p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "div"}

    def __init__(self) -> None:
        """Initialize a fresh sanitizer for one stored text value."""
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.blocked = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Ignore executable elements and allow only attribute-free formatting."""
        if tag in {"script", "style", "iframe", "object", "svg", "math"}:
            self.blocked += 1
        elif not self.blocked and tag in self.allowed:
            self.parts.append(f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        """Close allowed formatting or leave a suppressed element."""
        if tag in {"script", "style", "iframe", "object", "svg", "math"}:
            self.blocked = max(0, self.blocked - 1)
        elif not self.blocked and tag in self.allowed and tag != "br":
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        """Escape literal text so stored markup cannot create active content."""
        if not self.blocked:
            self.parts.append(escape(data))


def rich(value: object) -> str:
    """Sanitize text without losing paragraphs, line breaks or emphasis."""
    parser = SheetText()
    parser.feed(str(value))
    parser.close()
    return "".join(parser.parts)


LABELS = {
    "identity": "Identité",
    "stats": "Caractéristiques",
    "statBonuses": "Bonus",
    "derived": "Combat",
    "defense": "Défense",
    "skills": "Compétences",
    "totem": "Totem",
    "capacities": "Capacités",
    "weapons": "Armes",
    "equipment": "Équipement",
    "inventory": "Inventaire",
    "inventoryItems": "Objets",
    "narrative": "Narratif",
    "progression": "Progression",
    "resources": "Ressources",
    "abilityControls": "Contrôle des capacités",
    "weaponMasteries": "Maîtrises d’armes",
    "elementalMasteries": "Maîtrises élémentaires",
    "feats": "Dons",
    "catalog": "Informations du catalogue",
    "name": "Nom",
    "description": "Description",
    "cost": "Coût",
    "base": "Base",
    "total": "Total",
    "color": "Couleur",
    "trained": "Maîtrisée",
    "prepared": "Préparée",
    "value": "Valeur",
    "main": "Principale",
    "save": "Sauvegarde",
    "usage": "Utilisation",
    "difficulty": "Difficulté / 5",
    "class": "Classes",
    "creator": "Créateur",
    "loreSummary": "Résumé narratif",
    "gameplaySummary": "Style de jeu",
}


def label(key: str) -> str:
    """Name known sections and expand remaining canonical camel-case field names."""
    return LABELS.get(key, re.sub(r"([a-z])([A-Z])", r"\1 \2", key).capitalize())


def value_html(value: object) -> str:
    """Render every stored value recursively, preserving zeroes and false booleans."""
    if isinstance(value, dict):
        pairs = []
        for key, item in value.items():
            if item is None or item == "" or item == [] or item == {}:
                continue
            if key in {"image", "portrait"}:
                if isinstance(item, str) and item.startswith("/assets/"):
                    pairs.append(
                        f'<dt>{escape(label(key))}</dt><dd>'
                        f'<img class="static-image" src="{escape(item)}" '
                        'alt="Illustration de la fiche" loading="lazy"></dd>'
                    )
                continue
            pairs.append(f"<dt>{escape(label(key))}</dt><dd>{value_html(item)}</dd>")
        return "<dl>" + "".join(pairs) + "</dl>"
    if isinstance(value, list):
        return "<ul>" + "".join(f"<li>{value_html(v)}</li>" for v in value) + "</ul>"
    if isinstance(value, bool):
        return "Oui" if value else "Non"
    return rich(value)


def character_url(identifier: str) -> str:
    """Return a stable root-relative URL with one safe character-id path segment."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier):
        raise ValueError(f"Identifiant de personnage non sûr : {identifier!r}")
    return f"/personnages/{quote(identifier)}/"


def document(title: str, body: str, extra: str = "") -> str:
    """Wrap semantic content in the catalogue's shared visual shell."""
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} — Cardenveil</title>
<meta name="description" content="{escape(title)} — fiche de personnage Cardenveil">
<link rel="stylesheet" href="/styles.css">
<link rel="stylesheet" href="/static-sheet.css"></head><body>
<header class="site-header"><a class="brand" href="/">CARDENVEIL</a>
<nav><a href="/">Catalogue</a> <a href="/regles/">Règles & docs</a> <a href="/personnages/">Toutes les fiches</a></nav></header>
<main id="app">{body}</main>{extra}</body></html>'''


def write_character(public: Path, character: dict) -> None:
    """Publish full HTML and the same payload used by the interactive renderer."""
    url = character_url(character["id"])
    target = public / url.strip("/") / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    name = str(character["identity"]["nom"])
    body = f'<h1>{rich(name)}</h1><p class="actions">'
    body += f'<a class="button" href="{escape(character["printUrl"])}">Fiche A4 / Imprimer</a>'
    body += f'<a class="button" href="{escape(character["download"])}" download>Archive ZIP</a>'
    body += '</p><div class="static-sheet">'
    for key, value in character.items():
        if key in {"id", "download", "printUrl", "pageUrl"}:
            continue
        if value is None or value == "" or value == [] or value == {}:
            continue
        content = value_html({key: value}) if key == "portrait" else value_html(value)
        body += f'<section class="data-card"><h2>{escape(label(key))}</h2>{content}</section>'
    body += "</div>"
    # Escape script delimiters even though this is non-executable JSON.
    payload = json.dumps(character, ensure_ascii=False).replace("<", "\\u003c")
    extra = f'<script id="character-data" type="application/json">{payload}</script>'
    extra += '<script src="/app.js" defer></script>'
    target.write_text(document(name, body, extra), encoding="utf-8")


def write_index(public: Path, characters: list[dict]) -> None:
    """Expose crawlable links without requiring catalogue JavaScript execution."""
    directory = public / "personnages"
    directory.mkdir(parents=True, exist_ok=True)
    links = "".join(
        f'<li><a href="{escape(c["pageUrl"])}">{rich(c["identity"]["nom"])}</a></li>'
        for c in characters
    )
    (directory / "index.html").write_text(
        document("Fiches des personnages", f"<h1>Fiches des personnages</h1><ul>{links}</ul>"),
        encoding="utf-8",
    )

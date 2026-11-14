"""Build the public rules library from explicit local sources, without runtime dependencies."""

# HTML templates intentionally retain long lines for readable markup.
# ruff: noqa: E501

from __future__ import annotations

import re
import hashlib
import json
import unicodedata
from html import escape
from pathlib import Path

RULES_ROOT = Path(__file__).resolve().parents[1] / "docs/rules/fragmented"
DESCRIPTIONS = {
    "reference-rapide": "L’essentiel à garder sous les yeux pendant la partie.",
    "systeme-de-base": "Dés, cartes, tokens et principes du système.",
    "creation": "Identité, caractéristiques, compétences et aspects.",
    "races": "Les illustrations et les traits de chaque race.",
    "combat": "Rounds, initiative, déplacements, attaques et défense.",
    "capacites": "Activer ses pouvoirs et gérer ses cartes.",
    "narration": "Aspects, objectifs, interactions et flashbacks.",
    "progression": "Règles optionnelles de progression, d’XP et d’évolution du pool.",
}


def markdown_chapters(directory: Path = RULES_ROOT) -> list[tuple[str, str, str, str, str]]:
    """Build the public hierarchy from manifest order, Markdown paths and H1 titles."""
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    chapters = []
    for key, record in manifest["documents"].items():
        relative = Path(record["file"])
        source = (directory / relative).read_text(encoding="utf-8-sig")
        heading = re.search(r"^#\s+(.+?)\s*$", source, re.M)
        if not heading:
            raise ValueError(f"Missing H1 title in {relative.as_posix()}")
        title = re.sub(r"\*\*", "", heading.group(1)).strip()
        group = "Règles générales" if len(relative.parts) == 1 else relative.parts[0].replace("-", " ").title()
        if relative.parts[0].casefold() == "campagne":
            group = "Campagne — optionnel"
        chapters.append((group, key, title, DESCRIPTIONS.get(key, f"Consulter {title}."), relative.as_posix()))
        if key == "creation":
            chapters.append((group, "races", "Races jouables", DESCRIPTIONS["races"], relative.as_posix()))
    return chapters


CHAPTERS = markdown_chapters()
RULE_TITLES = {
    "character.stats.modifier": "Calculer un modificateur",
    "character.health.max": "Points de vie maximum",
    "character.stats.creation_pool": "Répartir les caractéristiques",
    "ability.save.aoe_acrobatics": "Sauvegarde contre un effet de zone",
    "ability.cost.stat_reduction": "Réduction du coût par la caractéristique",
    "ability.known.maximum": "Nombre de capacités connues",
    "combat.ranged.control_zone": "Capacité à distance en zone de contrôle",
    "combat.ranged.elevation_advantage": "Surplomb et avantage à distance",
    "combat.weapon.critical": "Critiques et relances",
    "condition.blinded.attack_outgoing": "Aveuglé : attaques de la créature",
    "condition.blinded.attack_incoming": "Aveuglé : attaques contre la créature",
    "condition.blinded.visual_perception": "Aveuglé : perception visuelle",
    **{
        f"weapon.property.{key}": title
        for key, title in {
            "guard": "Garde",
            "brutality": "Brutalité",
            "impact": "Impact",
            "fluid": "Fluide",
            "reach": "Allonge",
            "overhang": "Surplomb",
            "piercing": "Perforant",
            "bulwark": "Rempart",
        }.items()
    },
}


def slug(text: str) -> str:
    """Create readable, accent-independent section anchors."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-") or "section"


EMPHASIS = re.compile(
    r"(?<!\w)(?:"
    r"(?:\d+\s*)?d(?:4|6|8|10|12|20|100)\b"
    r"|[+-]?\d+(?:[,.]\d+)?\s*(?:%|XP\b|PV\b|mètres?\b|points?\b|actions?\b|réactions?\b|tours?\b|cartes?\b|niveaux?\b|dégâts\b)"
    r"|attaque d[’']opportunité|zone de contrôle|points de vie|valeur maximale"
    r"|réussite critique|échec critique|avantage|désavantage|parade|esquive|armure"
    r"|une seule fois|au maximum|au minimum|à l[’']entier inférieur|divisée? par deux"
    r")(?!\w)",
    re.IGNORECASE,
)


def emphasize(text: str) -> str:
    """Escape prose and emphasize up to four distinct mechanical cues per block."""
    parts, seen, start = [], set(), 0
    for match in EMPHASIS.finditer(text):
        key = match[0].casefold()
        if key in seen:
            continue
        parts.extend((escape(text[start:match.start()]), f"<strong>{escape(match[0])}</strong>"))
        start = match.end()
        seen.add(key)
        if len(seen) == 4:
            break
    parts.append(escape(text[start:]))
    return "".join(parts)


def inline(text: str, *, emphasis: bool = True) -> str:
    """Render the inline Markdown subset used by the allowlisted rule documents safely."""
    render = emphasize if emphasis else escape
    tokens = re.compile(r"`([^`]+)`|\*\*([^*]+)\*\*|\[([^\]]+)\]\((/regles/[a-z0-9/#-]+)\)")
    parts, start = [], 0
    for match in tokens.finditer(text):
        parts.append(render(text[start:match.start()]))
        if match[1] is not None:
            parts.append(f"<code>{escape(match[1])}</code>")
        elif match[2] is not None:
            parts.append(f"<strong>{escape(match[2])}</strong>")
        else:
            parts.append(f'<a href="{escape(match[4])}">{escape(match[3])}</a>')
        start = match.end()
    parts.append(render(text[start:]))
    return "".join(parts)


def markdown(source: str) -> tuple[str, list[tuple[str, str]]]:
    """Render headings, paragraphs, lists and pipe tables present in the curated Markdown."""
    lines = source.splitlines()
    result, toc = [], []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("# "):
            index += 1
            continue
        heading = re.match(r"(#{2,3}) (.+)", line)
        if heading:
            level, title = len(heading[1]), RULE_TITLES.get(heading[2], heading[2])
            anchor = f"{slug(title)}-{len(toc) + 1}"
            toc.append((anchor, title))
            result.append(f'<h{level} id="{anchor}">{inline(title, emphasis=False)}</h{level}>')
            index += 1
        elif line.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = lines[index].strip().strip("|").split("|")
                if not all(re.fullmatch(r"\s*:?-+:?\s*", cell) for cell in cells):
                    tag = "th" if not rows else "td"
                    rows.append(
                        "<tr>"
                        + "".join(f"<{tag}>{inline(c.strip())}</{tag}>" for c in cells)
                        + "</tr>"
                    )
                index += 1
            result.append(
                '<div class="table-scroll" tabindex="0" aria-label="Tableau des règles"><table><thead>'
                + rows[0]
                + "</thead><tbody>"
                + "".join(rows[1:])
                + "</tbody></table></div>"
            )
        elif line.startswith("- "):
            items = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                items.append("<li>" + inline(lines[index].strip()[2:]) + "</li>")
                index += 1
            result.append("<ul>" + "".join(items) + "</ul>")
        else:
            paragraph = [line]
            index += 1
            while (
                index < len(lines)
                and lines[index].strip()
                and not lines[index].startswith(("#", "- ", "|"))
            ):
                paragraph.append(lines[index].strip())
                index += 1
            result.append("<p>" + inline(" ".join(paragraph)) + "</p>")
    return "\n".join(result), toc


def navigation(current: str, chapter_sections: dict | None = None) -> str:
    """Render grouped, crawlable navigation with an explicit current-page marker."""

    def topics_html(key: str, topics: list, depth: int = 0) -> str:
        """Recursively preserve the heading hierarchy beneath any chapter."""
        css = 'chapter-sections' if depth == 0 else 'chapter-subsections'
        rows = []
        for topic in topics:
            row = f'<li><a href="/regles/{key}/#{escape(topic["anchor"])}">{escape(topic["label"])}</a>'
            if topic.get('children'):
                row += topics_html(key, topic['children'], depth + 1)
            rows.append(row + '</li>')
        return f'<ul class="{css}">' + ''.join(rows) + '</ul>'

    parts = ['<a class="library-home" href="/regles/">Bibliothèque des règles</a>']
    for group in dict.fromkeys(c[0] for c in CHAPTERS):
        parts.append(f"<h2>{group}</h2><ul>")
        for section, key, title, _, _ in CHAPTERS:
            if section == group:
                active = ' aria-current="page"' if key == current else ""
                topics = (chapter_sections or {}).get(key, [])
                if topics:
                    opened = ' open' if key == current else ''
                    parts.append(f'<li><details class="chapter-navigation" data-chapter="{key}"{opened}><summary><span class="chapter-heading"><span class="chapter-caret" aria-hidden="true">›</span><a href="/regles/{key}/"{active}>{escape(title)}</a></span></summary>')
                    parts.append(topics_html(key, topics) + '</details></li>')
                else:
                    parts.append(f'<li><a href="/regles/{key}/"{active}>{escape(title)}</a></li>')
        parts.append("</ul>")
    return "".join(parts)


def shell(
    title: str, description: str, content: str, current: str = "",
    *, featured: str = "", chapter_sections: dict | None = None,
) -> str:
    """Build a two-column reading layout with one unified desktop/mobile navigation."""
    # New HTML must never reuse a browser-cached stylesheet with the old summary layout.
    css_hash = hashlib.sha256((Path(__file__).parent / "public/rules.css").read_bytes()).hexdigest()[:12]
    search_box = '''<section class="docs-search" aria-label="Recherche de règles">
<label for="rule-search">Retrouver une règle</label><div class="search-field"><input id="rule-search" type="search" placeholder="Parade, cartes, flashback…" autocomplete="off" disabled><button id="clear-search" type="button" aria-label="Effacer la recherche" hidden>Effacer</button></div>
<p id="search-status" role="status">Chargement de la recherche…</p><noscript>Les chapitres restent accessibles sans JavaScript.</noscript><div id="search-results"></div></section>'''
    return f'''<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} — Règles Cardenveil</title><meta name="description" content="{escape(description)}">
<link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/rules.css?v={css_hash}">
<link rel="stylesheet" href="/rules-chat.css"><script src="/rules-chat.js" defer></script><script src="/gm.js" defer></script>
</head><body class="rules-site"><a class="skip-link" href="#reading">Aller au contenu</a>
<header class="site-header"><a class="brand" href="/">CARDENVEIL</a><nav><a href="/">Personnages</a><a href="/statistiques/">Statistiques</a><a href="/regles/" aria-current="page">Règles & docs</a><a href="/gm/">Agent MJ</a></nav></header>
<div class="docs-layout"><aside class="docs-nav"><details open><summary>Explorer les règles</summary><nav aria-label="Chapitres">{navigation(current, chapter_sections)}</nav></details></aside>
<main id="reading"><div class="breadcrumb"><a href="/">Cardenveil</a> / <a href="/regles/">Règles</a></div>
<h1>{escape(title)}</h1>
{featured}
{search_box}
{content}</main></div>
<footer>Cardenveil · Règles joueurs · <a href="/regles/reference-rapide/">Référence rapide</a></footer>
<script src="/rules.js" defer></script></body></html>'''


def build_rules(root: Path, public: Path) -> None:
    """Publish the player-only Fragmented snapshot instead of the legacy PDF edition."""
    from fragmented_rules import build

    build(root, public)

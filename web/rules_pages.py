"""Build the public rules library from explicit local sources, without runtime dependencies."""

# HTML templates intentionally retain long lines for readable markup.
# ruff: noqa: E501

from __future__ import annotations

import json
import re
import unicodedata
from html import escape
from pathlib import Path

# Explicit publication allowlist: internal engineering documents are never auto-published.
CHAPTERS = [
    (
        "Découvrir",
        "reference-rapide",
        "Référence rapide",
        "L'essentiel à retrouver pendant la partie.",
        "source",
    ),
    (
        "Découvrir",
        "introduction",
        "Bienvenue dans Cardenveil",
        "La philosophie et l'organisation du jeu.",
        "source",
    ),
    (
        "Découvrir",
        "systeme-de-base",
        "Dés, cartes & tokens",
        "Comprendre les ressources et les tests.",
        "source",
    ),
    (
        "Jouer",
        "creation",
        "Créer son personnage",
        "Identité, caractéristiques et construction du personnage.",
        "source",
    ),
    (
        "Jouer",
        "combat",
        "Actions & combat",
        "Tours, déplacements, attaques et réactions.",
        "source",
    ),
    (
        "Jouer",
        "capacites",
        "Totems, capacités & cartes",
        "Activer ses pouvoirs et gérer sa main.",
        "source",
    ),
    (
        "Jouer",
        "narration",
        "Aspects & narration",
        "Personnalité, relations et interactions narratives.",
        "source",
    ),
    (
        "Jouer",
        "progression",
        "Progression & expérience",
        "Dépenser ses XP et développer son personnage.",
        "source",
    ),
    (
        "Références",
        "personnage",
        "Caractéristiques & PV",
        "Synthèse des règles structurées du core.",
        "character.md",
    ),
    (
        "Références",
        "cartes",
        "Coûts & sauvegardes",
        "Synthèse : capacités, cartes et réductions.",
        "abilities.md",
    ),
    (
        "Références",
        "attaques",
        "Attaques & positionnement",
        "Synthèse : portée, surplomb et critiques.",
        "combat.md",
    ),
    (
        "Références",
        "conditions",
        "Conditions",
        "Effets documentés de la condition Aveuglé.",
        "conditions.md",
    ),
    (
        "Références",
        "armes",
        "Armes & propriétés",
        "Les familles et le tableau des armes.",
        "weapons.md",
    ),
    (
        "Références",
        "versions",
        "Sources & divergences",
        "Lire les différentes versions sans les confondre.",
        "reading-guide.md",
    ),
]

# Reading order follows the supplied manuals; older summaries remain separate references.
ORDER = [
    "introduction",
    "systeme-de-base",
    "creation",
    "progression",
    "narration",
    "combat",
    "capacites",
    "reference-rapide",
    "armes",
    "conditions",
    "personnage",
    "cartes",
    "attaques",
    "versions",
]
GROUPS = {
    "introduction": "Comprendre le jeu",
    "systeme-de-base": "Comprendre le jeu",
    "creation": "Créer et faire évoluer",
    "progression": "Créer et faire évoluer",
    "narration": "Jouer une partie",
    "combat": "Jouer une partie",
    "capacites": "Jouer une partie",
    "reference-rapide": "Aides de jeu",
}
CHAPTERS = sorted(
    [(GROUPS.get(c[1], "Références et versions"), *c[1:]) for c in CHAPTERS],
    key=lambda c: ORDER.index(c[1]),
)
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


def inline(text: str) -> str:
    """Render the inline Markdown subset used by the allowlisted rule documents safely."""
    safe = escape(text)
    safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
    safe = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"\[([^\]]+)\]\((/regles/[a-z0-9/#-]+)\)", r'<a href="\2">\1</a>', safe)
    return safe


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
            result.append(f'<h{level} id="{anchor}">{inline(title)}</h{level}>')
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


def navigation(current: str) -> str:
    """Render grouped, crawlable navigation with an explicit current-page marker."""
    parts = ['<a class="library-home" href="/regles/">Bibliothèque des règles</a>']
    for group in dict.fromkeys(c[0] for c in CHAPTERS):
        parts.append(f"<h2>{group}</h2><ul>")
        for section, key, title, _, _ in CHAPTERS:
            if section == group:
                active = ' aria-current="page"' if key == current else ""
                parts.append(f'<li><a href="/regles/{key}/"{active}>{escape(title)}</a></li>')
        parts.append("</ul>")
    return "".join(parts)


def shell(
    title: str, description: str, content: str, current: str = "", toc: list | None = None
) -> str:
    """Build a responsive reading layout with mobile navigation and per-page contents."""
    contents = "".join(f'<li><a href="#{a}">{escape(t)}</a></li>' for a, t in toc or [])
    return f'''<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} — Règles Cardenveil</title><meta name="description" content="{escape(description)}">
<link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/rules.css">
</head><body class="rules-site"><a class="skip-link" href="#reading">Aller au contenu</a>
<header class="site-header"><a class="brand" href="/">CARDENVEIL</a><nav><a href="/">Personnages</a><a href="/regles/" aria-current="page">Règles & docs</a></nav></header>
<div class="docs-layout"><aside class="docs-nav"><details open><summary>Explorer les règles</summary><nav aria-label="Chapitres">{navigation(current)}</nav></details></aside>
<main id="reading"><div class="breadcrumb"><a href="/">Cardenveil</a> / <a href="/regles/">Règles</a></div>
<p class="eyebrow">LE LIVRE DE RÈGLES</p><h1>{escape(title)}</h1><p class="docs-lede">{escape(description)}</p>
{content}</main><aside class="docs-toc"><nav aria-label="Sur cette page"><h2>Sur cette page</h2><ol>{contents}</ol></nav></aside></div>
<footer>Cardenveil · Sources conservées, divergences signalées · <a href="/regles/versions/">À propos des versions</a></footer>
<script src="/rules.js" defer></script></body></html>'''


def build_rules(root: Path, public: Path) -> None:
    """Generate all rules pages and the search index from repository-owned text sources."""
    output = public / "regles"
    output.mkdir(parents=True, exist_ok=True)
    search = []
    for position, (group, key, title, description, source) in enumerate(CHAPTERS):
        if source == "source":
            data = json.loads((root / f"docs/rules/sources/{key}.json").read_text("utf-8"))
            toc = []
            body = (
                '<div class="document-source">Source : <strong>'
                + escape(data["source"])
                + f'</strong> · {len(data["pages"])} pages <a href="/regles/versions/">Versions et divergences</a></div>'
            )
            topic = title
            headings = {}
            for page in data["pages"]:
                number = page["number"]
                body += f'<span class="page-anchor" id="page-{number}"></span>'
                chunks = []
                anchor = f"page-{number}"

                def index_section(
                    chunks,
                    topic,
                    anchor,
                    title=title,
                    key=key,
                    source_name=data["source"],
                    number=number,
                ):
                    """Index one topic rather than an arbitrary PDF page or footer."""
                    if chunks:
                        search.append(
                            {
                                "title": title,
                                "section": topic,
                                "url": f"/regles/{key}/#{anchor}",
                                "text": " ".join(chunks),
                                "source": source_name,
                                "page": number,
                            }
                        )

                for element in page.get("elements", []):
                    kind = element["kind"]
                    if kind == "heading":
                        if number == 1 and element["text"] == " ".join(page["blocks"][0].split()):
                            # The document title is already present in the page's h1.
                            continue
                        index_section(chunks, topic, anchor)
                        chunks = []
                        topic = element["text"]
                        base = slug(topic)
                        headings[base] = headings.get(base, 0) + 1
                        anchor = base if headings[base] == 1 else f"{base}-{headings[base]}"
                        level = element["level"]
                        toc.append((anchor, topic))
                        body += f'<h{level} class="rule-heading" id="{anchor}">{escape(topic)} <a class="source-cite" href="#source-page-{number}" aria-label="Source : {escape(data["source"])} page {number}">p. {number}</a></h{level}>'
                    elif kind == "table":
                        rows = element["rows"]
                        body += '<div class="table-scroll" tabindex="0" aria-label="Tableau de règles"><table>'
                        for i, row in enumerate(rows):
                            tag = "th" if i == 0 else "td"
                            body += (
                                "<tr>"
                                + "".join(
                                    f"<{tag}>{escape(cell or '').replace(chr(10), '<br>')}</{tag}>"
                                    for cell in row
                                )
                                + "</tr>"
                            )
                            chunks.extend(cell or "" for cell in row)
                        body += "</table></div>"
                    else:
                        value = element["text"]
                        css = (
                            "rule-example"
                            if value.startswith(("Exemple", "👉"))
                            else "rule-paragraph"
                        )
                        body += f'<p class="{css}">{escape(value)}</p>'
                        chunks.append(value)
                index_section(chunks, topic, anchor)
                body += f'<details class="original-page" id="source-page-{number}"><summary>Consulter la source · {escape(data["source"])} · page {number}</summary>'
                body += (
                    "".join(f'<p class="source-block">{escape(b)}</p>' for b in page["blocks"])
                    + "</details>"
                )
        else:
            raw = (root / "docs/rules" / source).read_text("utf-8")
            display = "\n".join(
                line
                for line in raw.splitlines()
                if not line.startswith(("- Concepts:", "- Implémentation:"))
            )
            body, toc = markdown(display)
            body = (
                '<div class="source-notice">Synthèse structurée du core : couverture partielle et versions parfois différentes des PDF. Un statut <code>unresolved</code> indique un point non arbitré.</div>'
                + body
            )
            search.append({"title": title, "section": group, "url": f"/regles/{key}/", "text": raw})
        adjacent = []
        for offset, caption in [(-1, "Précédent"), (1, "Suivant")]:
            if 0 <= position + offset < len(CHAPTERS):
                c = CHAPTERS[position + offset]
                adjacent.append(
                    f'<a href="/regles/{c[1]}/"><small>{caption}</small>{escape(c[2])}</a>'
                )
        body += (
            '<nav class="chapter-links" aria-label="Parcours de lecture">'
            + "".join(adjacent)
            + "</nav>"
        )
        directory = output / key
        directory.mkdir(exist_ok=True)
        (directory / "index.html").write_text(shell(title, description, body, key, toc), "utf-8")
    body = """<div class="docs-search"><label for="rule-search">Rechercher dans les règles</label><input id="rule-search" type="search" placeholder="Parade, totem, progression…" disabled><p id="search-status" role="status">Chargement de la recherche…</p><noscript>La recherche nécessite JavaScript ; tous les chapitres restent accessibles ci-dessous.</noscript><div id="search-results"></div></div><div class="source-notice">Une bibliothèque, plusieurs sources : les PDF et les synthèses du core restent distincts. Consultez les <a href="/regles/versions/">divergences connues</a> avant de trancher une règle.</div>"""
    toc = []
    for number, group in enumerate(dict.fromkeys(c[0] for c in CHAPTERS), 1):
        toc.append((slug(group), group))
        body += f'<section id="{slug(group)}"><h2 class="group-title"><span>0{number}</span>{group}</h2><div class="docs-cards">'
        for section, key, title, description, source in CHAPTERS:
            if section == group:
                kind = "Document source" if source == "source" else "Fiche de référence"
                body += f'<a class="docs-card" href="/regles/{key}/"><span class="eyebrow">{kind}</span><h3>{escape(title)} <span aria-hidden="true">↗</span></h3><p>{escape(description)}</p></a>'
        body += "</div></section>"
    (output / "index.html").write_text(
        shell(
            "Règles & documentation",
            "Comprendre le système. Créer un personnage. Retrouver une règle en pleine partie.",
            body,
            toc=toc,
        ),
        "utf-8",
    )
    (output / "search.json").write_text(json.dumps(search, ensure_ascii=False), "utf-8")

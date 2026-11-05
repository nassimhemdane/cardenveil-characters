"""Compute and publish descriptive catalogue statistics without modifying sheets."""

from __future__ import annotations

import json
import math
import re
import statistics
import unicodedata
from collections import Counter
from html import escape
from html.parser import HTMLParser
from pathlib import Path

from static_pages import document

COLORS = {"heart": "♥ Cœurs", "club": "♣ Trèfles", "spade": "♠ Piques", "diamond": "♦ Carreaux"}
STATS = {"force": "Force", "agilite": "Agilité", "esprit": "Esprit", "social": "Social"}


class PlainText(HTMLParser):
    """Extract text nodes from legacy formatted labels for grouping and display."""

    def __init__(self) -> None:
        """Initialize a separate text buffer for each label."""
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        """Collect text, never markup or attributes."""
        self.parts.append(data)


def plain(value: object) -> str:
    """Strip legacy HTML and collapse whitespace without guessing missing content."""
    parser = PlainText()
    parser.feed(str(value or ""))
    return " ".join(" ".join(parser.parts).split())


def normalized(value: object) -> str:
    """Make accent- and case-insensitive comparison keys, not new sheet values."""
    return "".join(c for c in unicodedata.normalize("NFKD", plain(value).casefold()) if not unicodedata.combining(c))


def number(value: object) -> float | None:
    """Accept finite scalar numbers, including zero, but never booleans or formulas."""
    if value is None or isinstance(value, bool) or isinstance(value, (list, dict)):
        return None
    try:
        result = float(str(value).strip().replace(",", "."))
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) else None


def summary(values: list[object]) -> dict:
    """Describe the complete observed population using population standard deviation."""
    observed = [n for value in values if (n := number(value)) is not None]
    return {"n": len(observed), "missing": len(values) - len(observed),
            "mean": statistics.mean(observed) if observed else None,
            "median": statistics.median(observed) if observed else None,
            "stddev": statistics.pstdev(observed) if observed else None,
            "min": min(observed) if observed else None, "max": max(observed) if observed else None,
            "zeros": observed.count(0)}


def usage_modes(value: object) -> list[str]:
    """Recognize explicit action modes without counting 'bonus action' as an action."""
    text = normalized(value)
    bonus = bool(re.search(r"\b(?:bonus[\s-]+action|action[\s-]+bonus)\b", text))
    remaining = re.sub(r"\b(?:bonus[\s-]+action|action[\s-]+bonus)\b", " ", text)
    return (["Action"] if re.search(r"\baction\b", remaining) else []) + (["Action bonus"] if bonus else []) + (["Réaction"] if re.search(r"\breaction\b", text) else [])


def analyze(characters: list[dict]) -> dict:
    """Aggregate every capacity once, reporting unknown labels instead of inferring them."""
    capacities = [a for c in characters for a in c.get("capacities", [])]
    race_labels: dict[str, str] = {}
    races: Counter = Counter()
    for c in characters:
        label = plain(c.get("identity", {}).get("race")) or "Non renseignée"
        key = normalized(label)
        race_labels.setdefault(key, label)
        races[race_labels[key]] += 1
    colors: Counter = Counter()
    modes = Counter({"Action": 0, "Action bonus": 0, "Réaction": 0})
    combinations: Counter = Counter()
    unknown_usages: Counter = Counter()
    concentration = 0
    for a in capacities:
        color = a.get("cost", {}).get("color")
        colors[color if color in COLORS else "unknown"] += 1
        found = usage_modes(a.get("usage"))
        modes.update(found)
        combinations[" + ".join(found) if found else "Non renseigné / non reconnu"] += 1
        if not found:
            unknown_usages[plain(a.get("usage")) or "Vide"] += 1
        concentration += bool(re.search(r"\bconcentration\b", normalized(a.get("usage"))))

    def costs(items: list[dict], field: str) -> list[float | None]:
        """Exclude negative or malformed costs without silently replacing them with zero."""
        values = [number(a.get("cost", {}).get(field)) for a in items]
        return [v if v is not None and v >= 0 else None for v in values]

    groups = {key: [a for a in capacities if a.get("cost", {}).get("color") == key] for key in COLORS}
    groups["unknown"] = [a for a in capacities if a.get("cost", {}).get("color") not in COLORS]
    stat_values = {key: [c.get("stats", {}).get(key) for c in characters] for key in STATS}
    return {"characters": len(characters), "capacities": len(capacities), "races": dict(races),
            "colors": dict(colors), "modes": dict(modes), "combinations": dict(combinations),
            "concentration": concentration, "unknownUsages": dict(unknown_usages),
            "costs": {"all": {f: summary(costs(capacities, f)) for f in ("base", "total")},
                      **{k: {f: summary(costs(items, f)) for f in ("base", "total")} for k, items in groups.items()}},
            "stats": {k: summary(values) for k, values in stat_values.items()},
            "histograms": {k: dict(sorted(Counter(number(v) for v in values if number(v) is not None).items())) for k, values in stat_values.items()},
            "perCharacter": summary([len(c.get("capacities", [])) for c in characters]),
            "hp": summary([c.get("derived", {}).get("pvMax") for c in characters]),
            "difficulty": summary([c.get("catalog", {}).get("difficulty") for c in characters]),
            "skills": summary([sum(s.get("trained") is True for s in c.get("skills", {}).values()) for c in characters])}


def fmt(value: float | None) -> str:
    """Format display numbers in French while leaving exported JSON unrounded."""
    return "—" if value is None else f"{value:,.2f}".replace(",", "\u202f").replace(".", ",").removesuffix(",00")


def bars(counts: dict, denominator: int, *, sort: bool = True) -> str:
    """Render accessible labelled bars with counts and explicit denominator percentages."""
    items = sorted(counts.items(), key=lambda row: (-row[1], str(row[0]))) if sort else counts.items()
    maximum = max(counts.values(), default=1) or 1
    rows = []
    for label, count in items:
        percentage = 100 * count / denominator if denominator else 0
        rows.append(f'<li><div class="bar-caption"><span>{escape(str(label))}</span><strong>{count} <small>· {fmt(percentage)} %</small></strong></div><div class="bar-track" aria-hidden="true"><span style="width:{100 * count / maximum:.3f}%"></span></div></li>')
    return '<ul class="stat-bars">' + "".join(rows) + '</ul>' if rows else '<p>Aucune donnée disponible.</p>'


def table(rows: list[tuple[str, dict]], caption: str) -> str:
    """Provide an accessible, horizontally scrollable descriptive-statistics table."""
    headers = ("Série", "Effectif", "Moyenne", "Médiane", "Écart type σ", "Min.", "Max.", "Absents / invalides")
    body = "".join('<tr><th scope="row">' + escape(label) + '</th>' + ''.join(f'<td>{fmt(s[key])}</td>' for key in ("n", "mean", "median", "stddev", "min", "max", "missing")) + '</tr>' for label, s in rows)
    return f'<div class="stat-table-scroll" tabindex="0" role="region" aria-label="{escape(caption)}"><table><caption>{escape(caption)}</caption><thead><tr>' + ''.join(f'<th scope="col">{h}</th>' for h in headers) + '</tr></thead><tbody>' + body + '</tbody></table></div>'


def write_statistics(public: Path, characters: list[dict]) -> dict:
    """Generate the script-independent dashboard and a downloadable audit-friendly dataset."""
    data = analyze(characters)
    destination = public / "statistiques"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "donnees.json").write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    cards = [("Personnages", data["characters"], "Fiches du catalogue"), ("Capacités", data["capacities"], "Totems exclus"),
             ("Capacités / personnage", data["perCharacter"]["mean"], "Moyenne du catalogue"),
             ("Coût final moyen", data["costs"]["all"]["total"]["mean"], "Après réductions · toutes couleurs"),
             ("Écart type des coûts", data["costs"]["all"]["total"]["stddev"], "σ · coûts finaux"),
             ("PV moyens", data["hp"]["mean"], "Valeurs enregistrées dans les fiches")]
    body = '<section class="stats-hero"><p class="eyebrow">Observatoire du catalogue</p><h1>Les personnages, en chiffres.</h1><p class="lede">Races, profils et économie des capacités : une lecture d’ensemble des fiches existantes.</p><a class="button" href="/statistiques/donnees.json" download>Télécharger les statistiques JSON</a></section>'
    body += '<nav class="stats-jump" aria-label="Sections du dashboard">' + ''.join(f'<a href="#{k}">{v}</a>' for k, v in [("races", "Races"), ("couts", "Coûts & couleurs"), ("caracteristiques", "Caractéristiques"), ("actions", "Actions"), ("methode", "Méthode & qualité")]) + '</nav>'
    body += '<div class="stat-kpis">' + ''.join(f'<article><p>{label}</p><strong>{fmt(value)}</strong><small>{note}</small></article>' for label, value, note in cards) + '</div>'
    body += '<div class="stats-grid"><section class="stat-panel" id="races"><h2>Races</h2><p>Nombre et part des personnages. Les races hybrides et variantes de libellé restent distinctes, sans réinterprétation.</p><div class="stat-chart-scroll">' + bars(data["races"], data["characters"]) + '</div></section>'
    color_counts = {COLORS.get(k, "Non renseignée / inconnue"): v for k, v in data["colors"].items()}
    body += '<section class="stat-panel" id="couts"><h2>Les quatre couleurs</h2><p>Chaque capacité compte une fois, quelle que soit sa préparation. Les couleurs sont celles enregistrées, sans classification automatique.</p>' + bars(color_counts, data["capacities"]) + '<h3>Coût final moyen par couleur</h3><div class="color-averages">'
    for key, label in COLORS.items():
        s = data["costs"][key]["total"]
        body += f'<div class="color-{key}"><span>{label}</span><strong>{fmt(s["mean"])}</strong><small>σ {fmt(s["stddev"])} · n = {s["n"]}</small></div>'
    body += '</div></section></div><section class="stat-panel stat-wide"><h2>Coûts des capacités</h2><p>Base : avant réductions. Final : coût total enregistré après réductions. Chaque capacité a le même poids ; les moyennes ne sont pas des moyennes de personnages.</p>'
    for field, caption in [("total", "Coûts finaux — après réductions"), ("base", "Coûts de base — avant réductions")]:
        rows = [("Toutes couleurs", data["costs"]["all"][field])] + [(label, data["costs"][key][field]) for key, label in COLORS.items()]
        if data["colors"].get("unknown"):
            rows.append(("Couleur inconnue", data["costs"]["unknown"][field]))
        body += table(rows, caption)
    body += '</section><section class="stat-panel stat-wide" id="caracteristiques"><h2>Répartition des caractéristiques</h2><p>Scores bruts Force, Agilité, Esprit et Social, sans bonus ni modificateurs. Pourcentages calculés sur les scores renseignés de chaque caractéristique.</p><div class="stat-histograms">'
    for key, label in STATS.items():
        body += f'<article data-stat="{key}"><h3>{label}</h3><p>Moyenne {fmt(data["stats"][key]["mean"])} · σ {fmt(data["stats"][key]["stddev"])}</p>' + bars({fmt(float(k)): v for k, v in data["histograms"][key].items()}, data["stats"][key]["n"], sort=False) + '</article>'
    body += '</div>' + table([(label, data["stats"][key]) for key, label in STATS.items()], "Caractéristiques — scores bruts") + '</section>'
    body += '<div class="stats-grid"><section class="stat-panel" id="actions"><h2>Actions, bonus et réactions</h2><p>Une capacité multimode compte dans chacun de ses modes : les pourcentages peuvent dépasser 100 % au total. « Action bonus » ne compte pas comme « Action ».</p>' + bars(data["modes"], data["capacities"], sort=False) + f'<p class="stat-callout">{data["concentration"]} capacités mentionnent la concentration.</p></section>'
    body += '<section class="stat-panel"><h2>Combinaisons de modes</h2><p>Répartition exclusive : chaque capacité compte une seule fois. La concentration est suivie séparément, car ce n’est pas un mode d’action.</p>' + bars(data["combinations"], data["capacities"]) + '</section></div>'
    body += '<section class="stat-panel stat-wide"><h2>Vue générale des fiches</h2>' + table([("Capacités par personnage", data["perCharacter"]), ("PV maximum", data["hp"]), ("Difficulté / 5", data["difficulty"]), ("Compétences maîtrisées", data["skills"])], "Indicateurs par personnage") + '<p>Les compétences non cochées ne sont pas considérées comme manquantes : ce tableau ne permet pas de distinguer une fiche non extraite d’un personnage sans maîtrise.</p></section>'
    total = data["costs"]["all"]["total"]
    body += f'<section class="stat-panel stat-wide" id="methode"><h2>Méthode & qualité des données</h2><ul><li>Source : les archives du dossier Final, passées par Cardenveil Core au build. Aucun appel à Gemini et aucune modification des personnages.</li><li>Écart type de population : σ = √(Σ(x − moyenne)² / N), et non une estimation d’échantillon. Une seule observation donne σ = 0 ; aucune observation donne « — ».</li><li>Coûts finaux : {total["n"]} valeurs exploitables, dont {total["zeros"]} à zéro ; {total["missing"]} absentes ou invalides. Les zéros sont inclus ; coûts négatifs, expressions non numériques et valeurs infinies sont exclus.</li><li>Races : espaces, balises, casse et accents sont normalisés pour le regroupement ; pas de fusion sémantique ou de correction des fiches.</li><li>{data["colors"].get("unknown", 0)} capacités ont une couleur absente ou inconnue ; {sum(data["unknownUsages"].values())} ont un mode absent ou non reconnu.</li></ul>'
    if data["unknownUsages"]:
        body += '<details><summary>Libellés d’utilisation à vérifier</summary>' + bars(data["unknownUsages"], data["capacities"]) + '</details>'
    body += '</section>'
    page = document("Statistiques du catalogue", body)
    page = page.replace('</head>', '<link rel="stylesheet" href="/statistics.css"></head>')
    page = page.replace('<main id="app">', '<main id="app" class="statistics-dashboard">')
    (destination / "index.html").write_text(page, encoding="utf-8")
    return data

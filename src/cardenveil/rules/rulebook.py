"""Natural-language rulebook with stable identifiers and explicit provenance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from cardenveil.content.catalog import Catalog
from cardenveil.domain import ContentId
from cardenveil.errors import ValidationError


class RuleStatus(StrEnum):
    """Lifecycle and certainty state of a natural rule."""

    CANONICAL = "canonical"
    UNRESOLVED = "unresolved"
    DEPRECATED = "deprecated"


@dataclass(frozen=True, slots=True)
class RuleSource:
    """Precise human-readable provenance for a rule."""

    document: str
    section: str
    page: int | None = None
    version: str | None = None

    def __post_init__(self) -> None:
        """Require a document and section for every rule source."""
        if not self.document.strip() or not self.section.strip():
            raise ValidationError("Rule source document and section are required")


@dataclass(frozen=True, slots=True)
class Rule:
    """Atomic, searchable natural-language rule with stable identity."""

    id: ContentId
    title: str
    category: str
    text: str
    source: RuleSource
    status: RuleStatus = RuleStatus.CANONICAL
    tags: frozenset[str] = frozenset()
    formula: str | None = None
    related_concepts: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate the fields required for reliable retrieval."""
        if not self.title.strip() or not self.text.strip() or not self.category.strip():
            raise ValidationError("Rule title, category and text are required")


rules = Catalog.from_items(
    [
        Rule(
            ContentId("character.stats.modifier"),
            "Modificateur de caractéristique",
            "character",
            "Le modificateur d'une caractéristique est la moitié de son écart à 10, "
            "arrondie à l'entier inférieur.",
            RuleSource("Cardenveil Systeme de base", "Caractéristiques"),
            formula="floor((score - 10) / 2)",
        ),
        Rule(
            ContentId("character.health.max"),
            "Points de vie maximum",
            "character",
            "Une source donne 35 + deux fois la Force; cette formule n'est pas canonisée "
            "car la fiche de Mimyr contient une valeur incompatible.",
            RuleSource("Compain rules (layer 5)", "Caractéristiques et leur rôle", 4),
            RuleStatus.UNRESOLVED,
            formula="35 + 2 * force",
            notes=("Mimyr: Force 16 et PV max 70; la formule produit 67.",),
        ),
        Rule(
            ContentId("combat.ranged.control_zone"),
            "Capacité à distance en zone de contrôle",
            "combat",
            "Lorsqu'un personnage lance une capacité ciblant une créature à plus de 2 mètres "
            "tout en étant dans la zone de contrôle d'un ennemi, cet ennemi peut effectuer "
            "une attaque d'opportunité.",
            RuleSource("Compain rules (layer 5)", "Cartes et capacités", 21),
        ),
        Rule(
            ContentId("combat.ranged.elevation_advantage"),
            "Avantage en hauteur",
            "combat",
            "Une attaque à distance effectuée depuis une position située au moins 5 mètres "
            "au-dessus de la cible gagne un avantage.",
            RuleSource("Cardenveil Action et Combat", "Avantages de position"),
        ),
        Rule(
            ContentId("ability.save.aoe_acrobatics"),
            "Sauvegarde contre une zone",
            "ability",
            "Une capacité à effet de zone se résiste par une sauvegarde d'Acrobaties "
            "associée à l'Agilité.",
            RuleSource("Compain rules (layer 5)", "Sauvegarde des capacités", 21),
        ),
        Rule(
            ContentId("condition.blinded.attack_outgoing"),
            "Aveuglé — attaques sortantes",
            "condition",
            "Une créature aveuglée subit un désavantage sur ses attaques.",
            RuleSource("Cardenveil Action et Combat", "Conditions — Aveuglé"),
        ),
        Rule(
            ContentId("condition.blinded.attack_incoming"),
            "Aveuglé — attaques entrantes",
            "condition",
            "Les attaques contre une créature aveuglée bénéficient d'un avantage.",
            RuleSource("Cardenveil Action et Combat", "Conditions — Aveuglé"),
        ),
        Rule(
            ContentId("condition.blinded.visual_perception"),
            "Aveuglé — perception",
            "condition",
            "Une créature aveuglée échoue aux tests qui nécessitent la vue.",
            RuleSource("Cardenveil Action et Combat", "Conditions — Aveuglé"),
        ),
    ]
)

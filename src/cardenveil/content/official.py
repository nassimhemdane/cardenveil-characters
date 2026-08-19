"""Curated V1 subset of official Cardenveil content."""

from dataclasses import dataclass

from cardenveil.content.catalog import Catalog
from cardenveil.domain import (
    ContentId,
    DamageCategory,
    DamageTypeId,
    RaceDefinition,
    SkillId,
    Stat,
    WeaponDefinition,
)


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    """Official display data and stat association for one skill."""

    id: ContentId
    skill: SkillId
    name: str
    associated_stat: Stat
    description: str


@dataclass(frozen=True, slots=True)
class DamageTypeDefinition:
    """Official display data and category for one damage type."""

    id: ContentId
    damage_type: DamageTypeId
    name: str
    category: DamageCategory


@dataclass(frozen=True, slots=True)
class ConditionDefinition:
    """Natural-language condition definition linked to atomic rules."""

    id: ContentId
    name: str
    description: str
    category: str
    source_rule_ids: tuple[str, ...] = ()


SKILLS = Catalog.from_items(
    [
        SkillDefinition(
            ContentId("athletics"),
            SkillId.ATHLETICS,
            "Athlétisme",
            Stat.FORCE,
            "Effort physique, saut et lutte.",
        ),
        SkillDefinition(
            ContentId("resilience"),
            SkillId.RESILIENCE,
            "Résilience",
            Stat.FORCE,
            "Endurance et résistance corporelle.",
        ),
        SkillDefinition(
            ContentId("acrobatics"),
            SkillId.ACROBATICS,
            "Acrobaties",
            Stat.AGILITY,
            "Équilibre, esquive et sauvegardes de zone.",
        ),
        SkillDefinition(
            ContentId("arcana"),
            SkillId.ARCANA,
            "Arcanes",
            Stat.SPIRIT,
            "Connaissance et contrôle de la magie.",
        ),
        SkillDefinition(
            ContentId("investigation"),
            SkillId.INVESTIGATION,
            "Investigation",
            Stat.SPIRIT,
            "Déduction et recherche d'indices.",
        ),
        SkillDefinition(
            ContentId("perception"),
            SkillId.PERCEPTION,
            "Perception",
            Stat.SPIRIT,
            "Détection et vigilance.",
        ),
        SkillDefinition(
            ContentId("insight"),
            SkillId.INSIGHT,
            "Perspicacité",
            Stat.SOCIAL,
            "Lire les intentions et contrôles psychiques.",
        ),
    ]
)

RACES = Catalog.from_items(
    [
        RaceDefinition(
            ContentId("aasimar"),
            "Aasimar",
            "Descendant marqué par une influence céleste.",
            ("Résistance aux dégâts radiants.",),
            official=True,
        ),
    ]
)

DAMAGE_TYPES = Catalog.from_items(
    [
        DamageTypeDefinition(ContentId(item.value), item, name, category)
        for item, name, category in [
            (DamageTypeId.BLUDGEONING, "Contondant", DamageCategory.PHYSICAL),
            (DamageTypeId.SLASHING, "Tranchant", DamageCategory.PHYSICAL),
            (DamageTypeId.PIERCING, "Perçant", DamageCategory.PHYSICAL),
            (DamageTypeId.RADIANT, "Radiant", DamageCategory.MAGICAL),
            (DamageTypeId.NECROTIC, "Nécrotique", DamageCategory.MAGICAL),
            (DamageTypeId.FIRE, "Feu", DamageCategory.ELEMENTAL),
            (DamageTypeId.ICE, "Glace", DamageCategory.ELEMENTAL),
            (DamageTypeId.LIGHTNING, "Foudre", DamageCategory.ELEMENTAL),
        ]
    ]
)

WEAPONS = Catalog.from_items(
    [
        WeaponDefinition(
            ContentId("longsword"),
            "Épée longue",
            "1d8",
            DamageTypeId.SLASHING,
            ContentId("straight_swords"),
            (ContentId("versatile"),),
        ),
        WeaponDefinition(
            ContentId("dagger"),
            "Dague",
            "1d4",
            DamageTypeId.PIERCING,
            ContentId("straight_swords"),
            (ContentId("finesse"), ContentId("light"), ContentId("thrown")),
        ),
        WeaponDefinition(
            ContentId("longbow"),
            "Arc long",
            "1d8",
            DamageTypeId.PIERCING,
            ContentId("bows"),
            (ContentId("ranged"), ContentId("two_handed")),
            30,
        ),
    ]
)

CONDITIONS = Catalog.from_items(
    [
        ConditionDefinition(
            ContentId("blinded"),
            "Aveuglé",
            "La créature ne voit pas; les conséquences sont atomisées dans le Rulebook.",
            "sensory",
            (
                "condition.blinded.attack_outgoing",
                "condition.blinded.attack_incoming",
                "condition.blinded.visual_perception",
            ),
        ),
        ConditionDefinition(
            ContentId("prone"), "À terre", "La créature est renversée au sol.", "position"
        ),
        ConditionDefinition(
            ContentId("charmed"),
            "Charmé",
            "La créature subit une influence sociale surnaturelle.",
            "mental",
        ),
    ]
)


def validate_official_content() -> None:
    """Traverse catalogs and validate the cross-references supported in V1."""
    for skill in SKILLS.all():
        assert skill.skill.value == skill.id.value
    for damage in DAMAGE_TYPES.all():
        assert damage.damage_type.value == damage.id.value
    rule_ids = {rule_id for condition in CONDITIONS.all() for rule_id in condition.source_rule_ids}
    from cardenveil.rules import rules

    missing = rule_ids - {str(rule.id) for rule in rules.all()}
    if missing:
        from cardenveil.errors import ValidationError

        raise ValidationError(f"Unknown condition rule references: {sorted(missing)}")

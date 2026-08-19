"""Persistent Cardenveil character model.

Definitions are immutable; a Character is an evolving aggregate. Runtime combat state is
deliberately absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from cardenveil.domain.common import ContentId
from cardenveil.errors import ValidationError


class Stat(StrEnum):
    """Closed set of Cardenveil primary statistics."""

    FORCE = "force"
    AGILITY = "agility"
    SPIRIT = "spirit"
    SOCIAL = "social"


class SkillId(StrEnum):
    """Stable IDs for the sixteen canonical skills."""

    ATHLETICS = "athletics"
    RESILIENCE = "resilience"
    ACROBATICS = "acrobatics"
    STEALTH = "stealth"
    SLEIGHT_OF_HAND = "sleight_of_hand"
    ARCANA = "arcana"
    INVESTIGATION = "investigation"
    PERCEPTION = "perception"
    CULTURE = "culture"
    SURVIVAL = "survival"
    PERSUASION = "persuasion"
    DECEPTION = "deception"
    INTIMIDATION = "intimidation"
    PERFORMANCE = "performance"
    INSIGHT = "insight"
    ANIMAL_HANDLING = "animal_handling"


class AspectType(StrEnum):
    """Stable IDs for the eight narrative aspect types."""

    SCAR = "scar"
    DRIVE = "drive"
    MANNERISMS = "mannerisms"
    INSTINCT = "instinct"
    BELIEFS = "beliefs"
    EDUCATION = "education"
    PERSONALITY = "personality"
    REPUTATION = "reputation"


class CardSuit(StrEnum):
    """Card suits used by capacity costs, plus neutral cards."""

    HEART = "heart"
    DIAMOND = "diamond"
    CLUB = "club"
    SPADE = "spade"
    NEUTRAL = "neutral"


class ActionType(StrEnum):
    """Action economy categories used by capacity definitions."""

    ACTION = "action"
    BONUS_ACTION = "bonus_action"
    REACTION = "reaction"
    PASSIVE = "passive"


class DamageCategory(StrEnum):
    """High-level grouping of damage types."""

    PHYSICAL = "physical"
    MAGICAL = "magical"
    ELEMENTAL = "elemental"


class DamageTypeId(StrEnum):
    """Stable identifiers for known damage types."""

    BLUDGEONING = "bludgeoning"
    SLASHING = "slashing"
    PIERCING = "piercing"
    PSYCHIC = "psychic"
    NECROTIC = "necrotic"
    RADIANT = "radiant"
    FORCE = "force"
    ARCANE = "arcane"
    FIRE = "fire"
    ICE = "ice"
    WATER = "water"
    LIGHTNING = "lightning"
    TOXIC = "toxic"


@dataclass(frozen=True, slots=True)
class Stats:
    """Validated value object for four primary stat scores."""

    force: int
    agility: int
    spirit: int
    social: int

    def __post_init__(self) -> None:
        """Enforce the documented zero-to-twenty score range."""
        if any(not 0 <= value <= 20 for value in self.values()):
            raise ValidationError("Each stat must be between 0 and 20")

    def values(self) -> tuple[int, int, int, int]:
        """Return scores in Force, Agility, Spirit, Social order."""
        return (self.force, self.agility, self.spirit, self.social)

    def get(self, stat: Stat) -> int:
        """Return a score selected by its stable enum."""
        return getattr(self, stat.value)


@dataclass(frozen=True, slots=True)
class Identity:
    """Format-independent identity value object retained for content services."""

    name: str
    alignment: str | None = None
    age: str | None = None
    height: str | None = None
    weight: str | None = None
    eyes: str | None = None
    hair: str | None = None
    skin: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        """Require a nonblank character name."""
        if not self.name.strip():
            raise ValidationError("Character name must not be empty")


@dataclass(frozen=True, slots=True)
class Narrative:
    """Format-independent narrative value object."""

    background: str = ""
    goal: str = ""
    bonds: tuple[str, ...] = ()
    aspects: dict[AspectType, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AbilityDefinition:
    """Reusable immutable definition of a capacity."""

    id: ContentId
    name: str
    description: str
    base_cost: int
    suit: CardSuit
    associated_stat: Stat
    action_type: ActionType
    value_text: str = ""
    save_skill: SkillId | None = None
    save_effect: str | None = None
    damage_type: DamageTypeId | None = None
    concentration: bool = False
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        """Validate required capacity text and nonnegative base cost."""
        if not self.name.strip() or not self.description.strip():
            raise ValidationError("Ability name and description must not be empty")
        if self.base_cost < 0:
            raise ValidationError("Ability base cost cannot be negative")


@dataclass(frozen=True, slots=True)
class CharacterAbility:
    """Durable relationship between a character and a capacity definition."""

    definition_id: ContentId
    instance_id: ContentId | None = None
    awakened: bool = False
    notes: str = ""


@dataclass(frozen=True, slots=True)
class FeatDefinition:
    """Extensible natural-language feat definition."""

    id: ContentId
    name: str
    description: str
    tags: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class RaceDefinition:
    """Extensible race definition for official and custom content."""

    id: ContentId
    name: str
    description: str
    traits: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    official: bool = False


@dataclass(frozen=True, slots=True)
class TotemDefinition:
    """Extensible totem definition linked to optional rule IDs."""

    id: ContentId
    name: str
    description: str
    rule_ids: tuple[str, ...] = ()
    tags: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class WeaponDefinition:
    """Structured weapon definition retained for domain consumers."""

    id: ContentId
    name: str
    damage_dice: str
    damage_type: DamageTypeId
    family_id: ContentId
    property_ids: tuple[ContentId, ...] = ()
    range_meters: int | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class Progression:
    """Format-independent durable progression counters."""

    level: int = 1
    xp_available: int = 0
    xp_spent: int = 0
    bonus_max_hp: int = 0
    weapon_family_xp: dict[ContentId, int] = field(default_factory=dict)
    elemental_mastery: dict[DamageTypeId, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Reject negative progression counters and levels below one."""
        if self.level < 1 or min(self.xp_available, self.xp_spent, self.bonus_max_hp) < 0:
            raise ValidationError("Progression values cannot be negative and level starts at 1")

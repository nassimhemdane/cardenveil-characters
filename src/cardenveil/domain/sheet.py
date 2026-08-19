"""Exact domain representation of the canonical ``rpsheet`` JSON format.

Every public dataclass mirrors one JSON object observed in the reference archives.  Field names
match JSON keys directly except :class:`Resources.gold`, whose JSON alias is ``or`` because
``or`` is a Python keyword.  Strings intentionally keep HTML and empty values: this layer is a
lossless representation, not a cleaning or rules-calculation layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

JsonScalar = str | int | float | bool | None


@dataclass(slots=True)
class SheetIdentity:
    """Identity block stored under ``identity``."""

    nom: str = ""
    joueur: str = ""
    niveau: int | str = ""
    race: str = ""
    alignement: str = ""
    age: str = ""
    taille: str = ""
    poids: str = ""
    yeux: str = ""
    peau: str = ""
    cheveux: str = ""


@dataclass(slots=True)
class SheetStats:
    """Four primary statistics using the exact French JSON keys."""

    force: int = 0
    agilite: int = 0
    esprit: int = 0
    social: int = 0


@dataclass(slots=True)
class StatBonuses:
    """Optional legacy per-stat bonuses preserved only when present in source JSON."""

    force: int | str | None = None
    agilite: int | str | None = None
    esprit: int | str | None = None
    social: int | str | None = None


@dataclass(slots=True)
class SheetProgression:
    """XP counters present in the default character format."""

    xpDepenses: int = 0
    xpDisponibles: int = 0


@dataclass(slots=True)
class DerivedValues:
    """Persisted derived/cache values as found in existing sheets.

    Values accepting ``str | int`` reflect the references, where blank inputs are serialized as
    empty strings and populated inputs as numbers.  They are never recomputed during loading.
    """

    pvMax: int | str = ""
    bonusPv: int | str | None = None
    pvActuels: int | str = ""
    pvTemporaires: int | str = ""
    mouvement: int | str = ""
    initiative: int | str = ""
    perceptionPassive: int | str = ""
    seuilSauvegarde: int | str = ""
    seuilMiss: int | str = ""
    canalisation: int | str = ""
    bonusAttaque: int | str = ""
    inspiration: int | str = ""
    fatigue: int | str = ""
    mort: int | str = ""
    volonte: int | str = ""
    initiativeBonus: int | str | None = None
    mouvementBonus: int | str | None = None


@dataclass(slots=True)
class Defense:
    """Defense block, preserving rich-text strings from the editor."""

    parade: int | str = ""
    armure: int | str = ""
    deflexion: int | str = ""
    gardeBonus: int | str = ""
    bonus: int | str = ""


@dataclass(slots=True)
class ResourceTokens:
    """Persistent token maxima grouped by primary statistic."""

    force: int = 0
    agilite: int = 0
    esprit: int = 0
    social: int = 0


@dataclass(slots=True)
class Resources:
    """Currency, rations, card notes, and token values."""

    gold: int | str = field(default="", metadata={"json_name": "or"})
    rations: int | str = ""
    cartesEtTokens: str = ""
    tokens: ResourceTokens = field(default_factory=ResourceTokens)


@dataclass(slots=True)
class SkillValue:
    """Mastery flag and stored bonus for one skill."""

    trained: bool = False
    bonus: int | str = 0


@dataclass(slots=True)
class SheetSkills:
    """Canonical skills plus the optional legacy ``nature`` entry."""

    athletisme: SkillValue = field(default_factory=SkillValue)
    resilience: SkillValue = field(default_factory=SkillValue)
    acrobaties: SkillValue = field(default_factory=SkillValue)
    discretion: SkillValue = field(default_factory=SkillValue)
    escamotage: SkillValue = field(default_factory=SkillValue)
    arcanes: SkillValue = field(default_factory=SkillValue)
    investigation: SkillValue = field(default_factory=SkillValue)
    perception: SkillValue = field(default_factory=SkillValue)
    culture: SkillValue = field(default_factory=SkillValue)
    survie: SkillValue = field(default_factory=SkillValue)
    persuasion: SkillValue = field(default_factory=SkillValue)
    tromperie: SkillValue = field(default_factory=SkillValue)
    intimidation: SkillValue = field(default_factory=SkillValue)
    representation: SkillValue = field(default_factory=SkillValue)
    perspicacite: SkillValue = field(default_factory=SkillValue)
    dressage: SkillValue = field(default_factory=SkillValue)
    nature: SkillValue | None = None


@dataclass(slots=True)
class SheetWeapon:
    """One of the compact weapon rows shown on the character sheet."""

    nom: str = ""
    de: str = ""
    forceAgi: int | str = ""
    critique: int | str = ""
    avantage: int | str = ""
    bonus: int | str = ""
    perfection: int | str = ""
    notes: str = ""


@dataclass(slots=True)
class InventoryText:
    """Legacy free-text inventory block retained by the default format."""

    equipement: str = ""
    inventaire: str = ""
    totem: str = ""


@dataclass(slots=True)
class SheetTotem:
    """Totem name, natural-language effect, and optional image reference."""

    nom: str = ""
    description: str = ""
    image: str = ""


@dataclass(slots=True)
class SheetNarrative:
    """Narrative fields and the eight stat-associated aspects."""

    background: str = ""
    objectif: str = ""
    liens: str = ""
    traitsSpeciaux: list[str] = field(default_factory=list)
    personnalite: str = ""
    reputation: str = ""
    education: str = ""
    croyances: str = ""
    cicatrices: str = ""
    pulsion: str = ""
    maniesEtTics: str = ""
    instinct: str = ""


@dataclass(slots=True)
class AbilityValue:
    """Primary and bonus value text of a capacity."""

    main: str = ""
    bonus: str = ""


@dataclass(slots=True)
class AbilityCost:
    """Persisted cost breakdown exactly as exported by the sheet editor."""

    color: str = ""
    base: int = 0
    incantationReduction: int = 0
    colorReduction: int = 0
    awakeningReduction: int = 0
    weaponMasteryReduction: int = 0
    total: int = 0


@dataclass(slots=True)
class SheetCapacity:
    """Complete capacity entry in the default JSON format."""

    name: str = ""
    prepared: bool = False
    image: str = ""
    description: str = ""
    value: AbilityValue = field(default_factory=AbilityValue)
    cost: AbilityCost = field(default_factory=AbilityCost)
    incantation: str = ""
    save: str = ""
    usage: str = ""


@dataclass(slots=True)
class ColorReductions:
    """Cost reductions stored for each card suit."""

    spade: int = 0
    heart: int = 0
    diamond: int = 0
    club: int = 0


@dataclass(slots=True)
class AbilityControls:
    """Sheet-level capacity and hand controls."""

    cardMin: int | str = ""
    cardMax: int | str = ""
    knownAbilities: int | str = ""
    maxPreparedAbilities: int | str = ""
    colorReductions: ColorReductions = field(default_factory=ColorReductions)


@dataclass(slots=True)
class WeaponMastery:
    """Progression record for one weapon family."""

    family: str = ""
    perfection: int = 0


@dataclass(slots=True)
class ElementalMastery:
    """Progression record for one element."""

    element: str = ""
    level: int = 0


@dataclass(slots=True)
class HeadEquipment:
    """Helmet slot fields."""

    nom: str = ""
    raretePrix: str = ""
    deflexion: int | str = ""
    volonte: int | str = ""
    enchantement: str = ""
    description: str = ""


@dataclass(slots=True)
class ChestEquipment:
    """Chest armor slot fields."""

    nom: str = ""
    raretePrix: str = ""
    deflexion: int | str = ""
    armure: int | str = ""
    enchantement: str = ""
    description: str = ""


@dataclass(slots=True)
class HandsEquipment:
    """Gauntlet slot fields."""

    nom: str = ""
    raretePrix: str = ""
    deflexion: int | str = ""
    initiative: int | str = ""
    enchantement: str = ""
    description: str = ""


@dataclass(slots=True)
class FeetEquipment:
    """Boot slot fields."""

    nom: str = ""
    raretePrix: str = ""
    deflexion: int | str = ""
    vitesse: int | str = ""
    enchantement: str = ""
    description: str = ""


@dataclass(slots=True)
class AccessoryEquipment:
    """Shared fields for ring, amulet, and cape slots."""

    nom: str = ""
    raretePrix: str = ""
    enchantement: str = ""
    description: str = ""


@dataclass(slots=True)
class SheetEquipment:
    """All seven named equipment slots from the reference format."""

    casque: HeadEquipment = field(default_factory=HeadEquipment)
    plastron: ChestEquipment = field(default_factory=ChestEquipment)
    gantelets: HandsEquipment = field(default_factory=HandsEquipment)
    bottes: FeetEquipment = field(default_factory=FeetEquipment)
    anneau: AccessoryEquipment = field(default_factory=AccessoryEquipment)
    amulette: AccessoryEquipment = field(default_factory=AccessoryEquipment)
    cape: AccessoryEquipment = field(default_factory=AccessoryEquipment)


@dataclass(slots=True)
class InventoryEquipmentData:
    """Embedded equipment snapshot observed inside inventory items.

    ``armure`` is optional because only chest-item snapshots contain it in the archives.
    """

    nom: str = ""
    raretePrix: str = ""
    deflexion: int | str = ""
    volonte: int | str | None = None
    enchantement: str = ""
    description: str = ""
    armure: int | str | None = None
    initiative: int | str | None = None
    vitesse: int | str | None = None


@dataclass(slots=True)
class InventoryItem:
    """Structured inventory item exported by the application."""

    type: str = ""
    slot: str = ""
    family: str = ""
    weaponName: str = ""
    name: str = ""
    raretePrix: str = ""
    description: str = ""
    degats: str = ""
    parade: int | str = ""
    attributs: str = ""
    familySummary: str = ""
    catalystColor: str = ""
    equipmentData: InventoryEquipmentData = field(default_factory=InventoryEquipmentData)


@dataclass(slots=True)
class SheetFeat:
    """Free-form feat entry observed in one reference archive."""

    title: str = ""
    description: str = ""


@dataclass(slots=True)
class Character:
    """Complete character entity with a one-to-one mapping to ``*.rpsheet.json``."""

    schemaVersion: int = 1
    id: str = ""
    templateId: str = "cardenveil-standard"
    createdAt: str = ""
    updatedAt: str = ""
    identity: SheetIdentity = field(default_factory=SheetIdentity)
    portrait: str = ""
    stats: SheetStats = field(default_factory=SheetStats)
    statBonuses: StatBonuses | None = None
    progression: SheetProgression = field(default_factory=SheetProgression)
    derived: DerivedValues = field(default_factory=DerivedValues)
    defense: Defense = field(default_factory=Defense)
    resources: Resources = field(default_factory=Resources)
    skills: SheetSkills = field(default_factory=SheetSkills)
    weapons: list[SheetWeapon] = field(default_factory=list)
    inventory: InventoryText = field(default_factory=InventoryText)
    totem: SheetTotem = field(default_factory=SheetTotem)
    narrative: SheetNarrative = field(default_factory=SheetNarrative)
    actions: list[JsonScalar] = field(default_factory=list)
    reactions: list[JsonScalar] = field(default_factory=list)
    tokens: list[JsonScalar] = field(default_factory=list)
    capacities: list[SheetCapacity] = field(default_factory=list)
    notes: str = ""
    abilityControls: AbilityControls = field(default_factory=AbilityControls)
    weaponMasteries: list[WeaponMastery] = field(default_factory=list)
    elementalMasteries: list[ElementalMastery] = field(default_factory=list)
    equipment: SheetEquipment = field(default_factory=SheetEquipment)
    inventoryItems: list[InventoryItem] = field(default_factory=list)
    feats: list[SheetFeat] = field(default_factory=list)


# Public semantic name used by importers and future applications.  It is an alias, not a second
# model: ``isinstance(character, CharacterSheet)`` and ``isinstance(character, Character)`` are
# therefore both true.
CharacterSheet = Character

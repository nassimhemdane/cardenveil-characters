"""Pydantic models containing only information reasonably extractable from a sheet PDF."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictExtractionModel(BaseModel):
    """Base model rejecting hallucinated fields not present in the extraction contract."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=False)


class ExtractedSkillId(StrEnum):
    """Skill IDs accepted from structured extraction."""

    ATHLETISME = "athletisme"
    RESILIENCE = "resilience"
    ACROBATIES = "acrobaties"
    DISCRETION = "discretion"
    ESCAMOTAGE = "escamotage"
    ARCANES = "arcanes"
    INVESTIGATION = "investigation"
    PERCEPTION = "perception"
    CULTURE = "culture"
    SURVIE = "survie"
    PERSUASION = "persuasion"
    TROMPERIE = "tromperie"
    INTIMIDATION = "intimidation"
    REPRESENTATION = "representation"
    PERSPICACITE = "perspicacite"
    DRESSAGE = "dressage"


class ExtractedCardSuit(StrEnum):
    """Canonical card-suit values requested from the provider."""

    HEART = "heart"
    DIAMOND = "diamond"
    CLUB = "club"
    SPADE = "spade"


class CatalogClass(StrEnum):
    """Closed editorial class vocabulary accepted by the web catalogue."""

    BARBARE = "Barbare"
    BARDE = "Barde"
    DRUIDE = "Druide"
    GUERRIER = "Guerrier"
    MAGE = "Mage"
    MOINE = "Moine"
    PALADIN = "Paladin"
    PRETRE = "Prêtre"
    RODEUR = "Rôdeur"
    ROUBLARD = "Roublard"
    SORCIER = "Sorcier"
    INVOCATEUR = "Invocateur"
    ARTIFICIER = "Artificier"
    AUTRE = "Autre"


class ExtractedIdentity(StrictExtractionModel):
    """Visible identity fields; every field may be missing or illegible."""

    nom: str | None = None
    joueur: str | None = None
    niveau: int | None = None
    race: str | None = None
    alignement: str | None = None
    age: str | None = None
    taille: str | None = None
    poids: str | None = None
    yeux: str | None = None
    peau: str | None = None
    cheveux: str | None = None


class ExtractedStats(StrictExtractionModel):
    """Primary stat scores as printed on the PDF."""

    force: int | None = Field(default=None, ge=0, le=20)
    agilite: int | None = Field(default=None, ge=0, le=20)
    esprit: int | None = Field(default=None, ge=0, le=20)
    social: int | None = Field(default=None, ge=0, le=20)


class ExtractedSkill(StrictExtractionModel):
    """One visibly mastered or printed skill entry."""

    id: ExtractedSkillId = Field(
        description="Canonical skill ID; the visual label Nature maps to survie"
    )
    trained: bool | None = Field(
        default=None,
        description="True for a filled black circle, false for an empty circle, null if illegible",
    )
    bonus: int | None = Field(
        default=None,
        description="Only a bonus printed specifically for this skill; otherwise null",
    )


class ExtractedWeapon(StrictExtractionModel):
    """Weapon row transcribed without interpreting its formulae."""

    nom: str | None = None
    de: str | None = Field(default=None, description="Damage die/formula exactly as printed")
    forceAgi: str | int | None = None
    critique: str | int | None = None
    avantage: str | int | None = None
    bonus: str | int | None = None
    perfection: str | int | None = None
    notes: str | None = None


class ExtractedAbility(StrictExtractionModel):
    """Semantic capacity fields visible on the character sheet."""

    name: str | None = None
    prepared: bool | None = None
    description: str | None = None
    value_main: str | None = None
    value_bonus: str | None = None
    color: ExtractedCardSuit | None = None
    base_cost: int | None = Field(default=None, ge=0)
    reduced_cost: int | None = Field(default=None, ge=0)
    incantation: str | None = None
    save: str | None = None
    usage: str | None = None


class ExtractedTotem(StrictExtractionModel):
    """Totem name and effect text, excluding image extraction."""

    nom: str | None = None
    description: str | None = None


class ExtractedNarrative(StrictExtractionModel):
    """Narrative blocks and aspects visible on the PDF."""

    background: str | None = None
    objectif: str | None = None
    liens: str | None = None
    traitsSpeciaux: list[str] = Field(
        default_factory=list,
        description=(
            "Lines inside the Traits spéciaux rectangle whose title is printed on its bottom border"
        ),
    )
    personnalite: str | None = None
    reputation: str | None = None
    education: str | None = None
    croyances: str | None = None
    cicatrices: str | None = None
    pulsion: str | None = None
    maniesEtTics: str | None = None
    instinct: str | None = None


class ExtractedDerivedValues(StrictExtractionModel):
    """Derived values copied only when explicitly printed on the PDF."""

    pvMax: int | str | None = None
    bonusPv: int | str | None = None
    pvActuels: int | str | None = None
    pvTemporaires: int | str | None = None
    mouvement: int | str | None = None
    initiative: int | str | None = None
    perceptionPassive: int | str | None = None
    seuilSauvegarde: int | str | None = None
    seuilMiss: int | str | None = None
    canalisation: int | str | None = None
    bonusAttaque: int | str | None = None
    inspiration: int | str | None = None
    fatigue: int | str | None = None
    mort: int | str | None = None
    volonte: int | str | None = None


class ExtractedDefense(StrictExtractionModel):
    """Defense values copied exactly when present."""

    parade: int | str | None = None
    armure: int | str | None = None
    deflexion: int | str | None = None
    gardeBonus: int | str | None = None
    bonus: int | str | None = None


class ExtractedResources(StrictExtractionModel):
    """Visible currency, ration, and free-form resource values."""

    or_: int | str | None = Field(default=None, alias="or")
    rations: int | str | None = None
    cartesEtTokens: str | None = None
    token_force: int | None = Field(default=None, ge=0)
    token_agilite: int | None = Field(default=None, ge=0)
    token_esprit: int | None = Field(default=None, ge=0)
    token_social: int | None = Field(default=None, ge=0)


class ExtractedProgression(StrictExtractionModel):
    """XP counters printed on a character sheet."""

    xpDepenses: int | None = Field(default=None, ge=0)
    xpDisponibles: int | None = Field(default=None, ge=0)


class ExtractedEquipmentPiece(StrictExtractionModel):
    """Union of fields visibly used by the seven equipment slots."""

    nom: str | None = None
    raretePrix: str | None = None
    deflexion: int | str | None = None
    volonte: int | str | None = None
    armure: int | str | None = None
    initiative: int | str | None = None
    vitesse: int | str | None = None
    enchantement: str | None = None
    description: str | None = None


class ExtractedEquipment(StrictExtractionModel):
    """Named equipment slots present on the sheet."""

    casque: ExtractedEquipmentPiece | None = None
    plastron: ExtractedEquipmentPiece | None = None
    gantelets: ExtractedEquipmentPiece | None = None
    bottes: ExtractedEquipmentPiece | None = None
    anneau: ExtractedEquipmentPiece | None = None
    amulette: ExtractedEquipmentPiece | None = None
    cape: ExtractedEquipmentPiece | None = None


class ExtractedWeaponMastery(StrictExtractionModel):
    """Weapon-family mastery explicitly printed on the sheet."""

    family: str
    perfection: int = Field(ge=0)


class ExtractedElementalMastery(StrictExtractionModel):
    """Elemental mastery explicitly printed on the sheet."""

    element: str
    level: int = Field(ge=0)


class ExtractedFeat(StrictExtractionModel):
    """Feat title and description explicitly present on a sheet."""

    title: str | None = None
    description: str | None = None


class ExtractedInconsistency(StrictExtractionModel):
    """One visible contradiction with two document-grounded scalar resolutions."""

    json_path: str = Field(
        pattern=r"^/",
        description="Canonical rpsheet JSON Pointer identifying the contradictory field",
    )
    description: str
    option_a_label: str
    option_a_value: str | int | float | bool | None
    option_b_label: str
    option_b_value: str | int | float | bool | None
    evidence_a: str
    evidence_b: str


class ExtractedTotemAndCapacities(StrictExtractionModel):
    """Focused repair result that prevents unrelated sheet fields from consuming the response."""

    totem: ExtractedTotem = Field(default_factory=ExtractedTotem)
    capacities: list[ExtractedAbility] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExtractedCatalogMetadata(StrictExtractionModel):
    """Concise, evidence-grounded catalogue metadata generated from one character sheet."""

    loreSummary: str = ""
    gameplaySummary: str = ""
    difficulty: float | None = Field(default=None, ge=0.5, le=5, multiple_of=0.5)
    creator: str = ""
    classes: list[CatalogClass] = Field(default_factory=list, alias="class")


class ExtractedCharacter(StrictExtractionModel):
    """Provider-neutral semantic extraction result before domain mapping."""

    identity: ExtractedIdentity = Field(default_factory=ExtractedIdentity)
    stats: ExtractedStats = Field(default_factory=ExtractedStats)
    skills: list[ExtractedSkill] = Field(
        default_factory=list,
        description="Best-effort skill rows; may be empty when visual circles are ambiguous",
    )
    weapons: list[ExtractedWeapon] = Field(default_factory=list)
    capacities: list[ExtractedAbility] = Field(default_factory=list)
    totem: ExtractedTotem = Field(default_factory=ExtractedTotem)
    narrative: ExtractedNarrative = Field(default_factory=ExtractedNarrative)
    derived: ExtractedDerivedValues = Field(default_factory=ExtractedDerivedValues)
    defense: ExtractedDefense = Field(default_factory=ExtractedDefense)
    resources: ExtractedResources = Field(default_factory=ExtractedResources)
    progression: ExtractedProgression = Field(default_factory=ExtractedProgression)
    equipment: ExtractedEquipment = Field(default_factory=ExtractedEquipment)
    weaponMasteries: list[ExtractedWeaponMastery] = Field(default_factory=list)
    elementalMasteries: list[ExtractedElementalMastery] = Field(default_factory=list)
    feats: list[ExtractedFeat] = Field(default_factory=list)
    notes: str | None = None
    inconsistencies: list[ExtractedInconsistency] = Field(
        default_factory=list,
        description=(
            "Visible contradictions for which the PDF itself supplies exactly two possible values"
        ),
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Extraction uncertainties grounded in the document, never invented facts",
    )

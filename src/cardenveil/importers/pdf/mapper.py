"""Explicit mapping from extracted document data to the canonical character sheet."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from cardenveil.domain import (
    AccessoryEquipment,
    CharacterSheet,
    ChestEquipment,
    Defense,
    DerivedValues,
    ElementalMastery,
    FeetEquipment,
    HandsEquipment,
    HeadEquipment,
    Resources,
    ResourceTokens,
    SheetCapacity,
    SheetEquipment,
    SheetFeat,
    SheetIdentity,
    SheetNarrative,
    SheetProgression,
    SheetSkills,
    SheetStats,
    SheetTotem,
    SheetWeapon,
    SkillValue,
    WeaponMastery,
)
from cardenveil.importers.pdf.errors import CharacterMappingError
from cardenveil.importers.pdf.models import (
    ExtractedAbility,
    ExtractedCharacter,
    ExtractedEquipment,
    ExtractedEquipmentPiece,
    ExtractedWeapon,
)
from cardenveil.naming import slugify_character_id


class CharacterMapper:
    """Map semantic extraction data into the exact persistent sheet model."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        """Accept an injectable clock so technical timestamps remain deterministic in tests."""

        self._clock = clock or (lambda: datetime.now(UTC))

    def map(self, extracted: ExtractedCharacter, source_path: Path) -> CharacterSheet:
        """Create a complete sheet without recalculating or inventing semantic values."""

        name = extracted.identity.nom or source_path.stem
        character_id = slugify_character_id(name) or slugify_character_id(source_path.stem)
        if not character_id:
            raise CharacterMappingError("Cannot derive a stable character ID from the PDF")
        timestamp = self._clock().isoformat()
        skills = SheetSkills()
        seen_skills: set[str] = set()
        for extracted_skill in extracted.skills:
            skill_id = extracted_skill.id.value
            if skill_id in seen_skills:
                raise CharacterMappingError(f"Duplicate extracted skill: {skill_id}")
            seen_skills.add(skill_id)
            setattr(
                skills,
                skill_id,
                SkillValue(bool(extracted_skill.trained), extracted_skill.bonus or 0),
            )

        return CharacterSheet(
            id=character_id,
            createdAt=timestamp,
            updatedAt=timestamp,
            identity=SheetIdentity(
                nom=_text(extracted.identity.nom),
                joueur=_text(extracted.identity.joueur),
                niveau=extracted.identity.niveau if extracted.identity.niveau is not None else "",
                race=_text(extracted.identity.race),
                alignement=_text(extracted.identity.alignement),
                age=_text(extracted.identity.age),
                taille=_text(extracted.identity.taille),
                poids=_text(extracted.identity.poids),
                yeux=_text(extracted.identity.yeux),
                peau=_text(extracted.identity.peau),
                cheveux=_text(extracted.identity.cheveux),
            ),
            stats=SheetStats(
                force=extracted.stats.force or 0,
                agilite=extracted.stats.agilite or 0,
                esprit=extracted.stats.esprit or 0,
                social=extracted.stats.social or 0,
            ),
            progression=SheetProgression(
                xpDepenses=extracted.progression.xpDepenses or 0,
                xpDisponibles=extracted.progression.xpDisponibles or 0,
            ),
            derived=DerivedValues(
                **{
                    key: value if value is not None else (None if key == "bonusPv" else "")
                    for key, value in extracted.derived.model_dump().items()
                }
            ),
            defense=Defense(
                **{
                    key: value if value is not None else ""
                    for key, value in extracted.defense.model_dump().items()
                }
            ),
            resources=Resources(
                gold=extracted.resources.or_ if extracted.resources.or_ is not None else "",
                rations=(
                    extracted.resources.rations if extracted.resources.rations is not None else ""
                ),
                cartesEtTokens=_text(extracted.resources.cartesEtTokens),
                tokens=ResourceTokens(
                    force=extracted.resources.token_force or 0,
                    agilite=extracted.resources.token_agilite or 0,
                    esprit=extracted.resources.token_esprit or 0,
                    social=extracted.resources.token_social or 0,
                ),
            ),
            skills=skills,
            weapons=[_map_weapon(weapon) for weapon in extracted.weapons],
            totem=SheetTotem(
                nom=_text(extracted.totem.nom),
                description=_text(extracted.totem.description),
            ),
            narrative=SheetNarrative(
                **{
                    key: value if value is not None else ""
                    for key, value in extracted.narrative.model_dump().items()
                }
            ),
            capacities=[_map_ability(ability) for ability in extracted.capacities],
            notes=_text(extracted.notes),
            weaponMasteries=[
                WeaponMastery(item.family, item.perfection) for item in extracted.weaponMasteries
            ],
            elementalMasteries=[
                ElementalMastery(item.element, item.level) for item in extracted.elementalMasteries
            ],
            equipment=_map_equipment(extracted.equipment),
            feats=[
                SheetFeat(_text(item.title), _text(item.description)) for item in extracted.feats
            ],
        )


def _map_weapon(weapon: ExtractedWeapon) -> SheetWeapon:
    """Map one validated extracted weapon while preserving formula strings."""

    return SheetWeapon(
        **{key: value if value is not None else "" for key, value in weapon.model_dump().items()}
    )


def _map_ability(ability: ExtractedAbility) -> SheetCapacity:
    """Map semantic ability fields into the persistent cost breakdown."""

    from cardenveil.domain import AbilityCost, AbilityValue

    base_cost = ability.base_cost or 0
    total = ability.reduced_cost if ability.reduced_cost is not None else base_cost
    return SheetCapacity(
        name=_text(ability.name),
        prepared=bool(ability.prepared),
        description=_text(ability.description),
        value=AbilityValue(_text(ability.value_main), _text(ability.value_bonus)),
        cost=AbilityCost(
            color=ability.color.value if ability.color is not None else "",
            base=base_cost,
            incantationReduction=max(base_cost - total, 0),
            total=total,
        ),
        incantation=_text(ability.incantation),
        save=_text(ability.save),
        usage=_text(ability.usage),
    )


def _map_equipment(extracted: ExtractedEquipment) -> SheetEquipment:
    """Map each extracted equipment slot to its exact persistent subtype."""

    return SheetEquipment(
        casque=_piece(HeadEquipment, extracted.casque),
        plastron=_piece(ChestEquipment, extracted.plastron),
        gantelets=_piece(HandsEquipment, extracted.gantelets),
        bottes=_piece(FeetEquipment, extracted.bottes),
        anneau=_piece(AccessoryEquipment, extracted.anneau),
        amulette=_piece(AccessoryEquipment, extracted.amulette),
        cape=_piece(AccessoryEquipment, extracted.cape),
    )


def _piece(cls: type, extracted: ExtractedEquipmentPiece | None) -> object:
    """Select only fields supported by a concrete equipment-slot class."""

    if extracted is None:
        return cls()
    accepted = cls.__dataclass_fields__
    values = {
        key: value if value is not None else ""
        for key, value in extracted.model_dump().items()
        if key in accepted
    }
    return cls(**values)


def _text(value: str | None) -> str:
    """Represent an unknown optional text as the sheet format's empty string."""

    return value if value is not None else ""

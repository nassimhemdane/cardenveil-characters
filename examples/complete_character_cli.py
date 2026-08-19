"""Create a complete rpsheet character and display/save its canonical JSON.

Run with ``py -3.11 examples/complete_character_cli.py --output character.rpsheet.json``.
The example is deliberately explicit: each constructor corresponds to one JSON object, making the
class-to-JSON matching easy to audit without hidden form or framework behavior.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cardenveil.domain import (
    AbilityControls,
    AbilityCost,
    AbilityValue,
    Character,
    ColorReductions,
    Defense,
    DerivedValues,
    ElementalMastery,
    InventoryEquipmentData,
    InventoryItem,
    InventoryText,
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
from cardenveil.serialization import character_to_json


def build_character() -> Character:
    """Fill every top-level section of a character from A to Z."""

    # Each skill is an object with the exact JSON keys ``trained`` and ``bonus``.
    skills = SheetSkills()
    skills.athletisme = SkillValue(True, 2)
    skills.acrobaties = SkillValue(True, 1)
    skills.arcanes = SkillValue(True, 3)
    skills.perception = SkillValue(True, 3)

    # A capacity keeps both its displayed values and every persisted cost component.
    capacity = SheetCapacity(
        name="Trait de lumière",
        prepared=True,
        image="/assets/demo/capacity-1.png",
        description="Projette un trait lumineux.",
        value=AbilityValue(main="2d8 radiant", bonus=""),
        cost=AbilityCost(
            color="heart",
            base=12,
            incantationReduction=6,
            colorReduction=1,
            awakeningReduction=0,
            weaponMasteryReduction=0,
            total=5,
        ),
        incantation="Esprit",
        save="Acrobaties (moitié dégâts)",
        usage="Action",
    )

    # The root object follows the same order and names as the rpsheet JSON contract.
    return Character(
        schemaVersion=1,
        id="demo-complet",
        templateId="cardenveil-standard",
        createdAt="2026-08-18T12:00:00+02:00",
        updatedAt="2026-08-18T12:00:00+02:00",
        identity=SheetIdentity(
            nom="Personnage Démonstration",
            joueur="Joueur",
            niveau=1,
            race="Humain",
            alignement="Neutre Bon",
            age="30",
            taille="1m75",
            poids="70kg",
            yeux="Verts",
            peau="Mate",
            cheveux="Noirs",
        ),
        portrait="/assets/demo/portrait.png",
        stats=SheetStats(force=14, agilite=12, esprit=16, social=10),
        progression=SheetProgression(xpDepenses=0, xpDisponibles=0),
        derived=DerivedValues(
            pvMax=100,
            bonusPv="",
            pvActuels=100,
            pvTemporaires=0,
            mouvement=11,
            initiative=2,
            perceptionPassive=13,
            seuilSauvegarde="",
            seuilMiss=1,
            canalisation=3,
            bonusAttaque="",
            inspiration="",
            fatigue="",
            mort="",
            volonte=1,
        ),
        defense=Defense(parade="7", armure="2", deflexion=1, gardeBonus="2", bonus="1"),
        resources=Resources(
            gold="100",
            rations="3",
            cartesEtTokens="",
            tokens=ResourceTokens(force=3, agilite=2, esprit=4, social=1),
        ),
        skills=skills,
        weapons=[SheetWeapon("Épée longue", "1d8", "2", "0", "0", "", "", "Garde")],
        inventory=InventoryText("Plastron", "Corde et torches", "Description du totem"),
        totem=SheetTotem("Totem solaire", "Effet du totem.", "/assets/demo/totem.png"),
        narrative=SheetNarrative(
            background="Archiviste itinérant.",
            objectif="Préserver un savoir perdu.",
            liens="Son ancienne académie.",
            traitsSpeciaux=["Résistance radiante."],
            personnalite="Méthodique.",
            reputation="Savant fiable.",
            education="Académie.",
            croyances="Le savoir doit circuler.",
            cicatrices="Une expédition perdue.",
            pulsion="Tout documenter.",
            maniesEtTics="Classe ses notes.",
            instinct="Observer.",
        ),
        actions=[],
        reactions=[],
        tokens=[],
        capacities=[capacity],
        notes="Personnage créé par l'exemple CLI.",
        abilityControls=AbilityControls(
            cardMin="",
            cardMax="",
            knownAbilities="1",
            maxPreparedAbilities="1",
            colorReductions=ColorReductions(spade=0, heart=1, diamond=0, club=0),
        ),
        weaponMasteries=[WeaponMastery("Épées droites", 1)],
        elementalMasteries=[ElementalMastery("Radiant", 1)],
        equipment=SheetEquipment(),
        inventoryItems=[
            InventoryItem(
                type="Arme",
                slot="main",
                family="Épées droites",
                weaponName="Épée longue",
                name="Épée longue",
                raretePrix="Commune",
                description="",
                degats="1d8",
                parade="4",
                attributs="Polyvalente (1d10), Garde",
                familySummary="Parade versatile.",
                catalystColor="",
                equipmentData=InventoryEquipmentData(),
            )
        ],
        feats=[SheetFeat("Lecteur assidu", "Retient les informations importantes.")],
    )


def main() -> None:
    """Print the complete JSON and optionally save exactly the same text to disk."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional .rpsheet.json destination")
    arguments = parser.parse_args()
    json_text = character_to_json(build_character())
    print(json_text)
    if arguments.output is not None:
        arguments.output.write_text(json_text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

"""End-to-end coverage of the full character format and file persistence."""

from cardenveil import CardenveilCore, FileCharacterRepository
from cardenveil.domain import (
    AbilityControls,
    AbilityCost,
    AbilityValue,
    Character,
    ChestEquipment,
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
from cardenveil.serialization import character_from_json, character_to_json


def _complete_character() -> Character:
    """Build a character exercising every populated branch of the canonical schema."""

    skills = SheetSkills()
    for skill_name in skills.__dataclass_fields__:
        setattr(skills, skill_name, SkillValue(trained=True, bonus=3))
    return Character(
        id="integration-hero",
        createdAt="2026-08-18T10:00:00+02:00",
        updatedAt="2026-08-18T11:00:00+02:00",
        identity=SheetIdentity(
            "Intégration",
            "Testeur",
            5,
            "Humain",
            "Neutre Bon",
            "31",
            "1m75",
            "70kg",
            "Verts",
            "Mate",
            "Noirs",
        ),
        portrait="/assets/integration-hero/portrait.png",
        stats=SheetStats(14, 12, 16, 10),
        progression=SheetProgression(12, 8),
        derived=DerivedValues(110, 10, 92, 5, 11, 2, 13, 16, 1, 3, 2, "oui", 0, 0, 1),
        defense=Defense("8", "3", 2, "1", "2"),
        resources=Resources("125", "4", "main complète", ResourceTokens(3, 2, 4, 1)),
        skills=skills,
        weapons=[SheetWeapon("Épée longue", "1d8", "2", "0", "1", "+1", "2", "Garde")],
        inventory=InventoryText("Armure", "Corde", "Totem décrit"),
        totem=SheetTotem("Totem complet", "Effet naturel complet.", "/assets/totem.png"),
        narrative=SheetNarrative(
            "Archiviste",
            "Préserver les règles",
            "Compagnons",
            ["Trait A", "Trait B"],
            "Patient",
            "Fiable",
            "Académie",
            "La mémoire compte",
            "Ancienne blessure",
            "Tout consigner",
            "Prend des notes",
            "Vérifier les sources",
        ),
        actions=["action personnalisée"],
        reactions=["réaction personnalisée"],
        tokens=[1, "token narratif"],
        capacities=[
            SheetCapacity(
                "Archive parfaite",
                True,
                "/assets/capacity.png",
                "Préserve chaque donnée.",
                AbilityValue("2d8", "+1"),
                AbilityCost("heart", 14, 6, 1, 1, 1, 5),
                "Esprit",
                "Acrobaties (moitié)",
                "Action / Concentration",
            )
        ],
        notes="Toutes les branches sont remplies.",
        abilityControls=AbilityControls(1, 13, 8, 4, ColorReductions(1, 2, 3, 4)),
        weaponMasteries=[WeaponMastery("Épées droites", 3)],
        elementalMasteries=[ElementalMastery("Feu", 2)],
        equipment=SheetEquipment(plastron=ChestEquipment("Plastron", "Rare", 2, 3, "+1", "Solide")),
        inventoryItems=[
            InventoryItem(
                "Arme",
                "main",
                "Épées droites",
                "Épée longue",
                "Épée longue",
                "Rare",
                "Arme de test",
                "1d8, tranchant/perçant",
                "4",
                "Polyvalente (1d10), Garde",
                "Parade versatile.",
                "",
                InventoryEquipmentData("", "", "", "", "", ""),
            )
        ],
        feats=[SheetFeat("Mémoire absolue", "N'oublie aucune clé JSON.")],
    )


def test_complete_character_json_and_persistence_roundtrip(tmp_path) -> None:
    """Exercise construction, JSON, save, get, list, overwrite, and rich nested values."""

    original = _complete_character()
    json_text = character_to_json(original)
    assert character_from_json(json_text) == original

    core = CardenveilCore(FileCharacterRepository(tmp_path))
    saved_path = core.save_character(original)
    assert saved_path.name == "integration-hero.rpsheet.json"
    assert core.load_character("integration-hero") == original
    assert core.load_all_characters() == [original]

    original.notes = "Sauvegarde remplacée atomiquement."
    core.save_character(original)
    assert core.load_character("integration-hero").notes == original.notes

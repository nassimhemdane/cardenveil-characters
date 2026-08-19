"""Complete weapon table transcribed from pages 28–30 of the consolidated rules."""

from __future__ import annotations

from dataclasses import dataclass

from cardenveil.content.catalog import Catalog
from cardenveil.domain import ContentId


@dataclass(frozen=True, slots=True)
class WeaponPropertyDefinition:
    """Natural-language definition of a weapon property."""

    id: ContentId
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class WeaponFamilyDefinition:
    """Weapon family and the property inherited by its members."""

    id: ContentId
    name: str
    property_id: ContentId


@dataclass(frozen=True, slots=True)
class OfficialWeapon:
    """One row of the canonical weapon table.

    ``damage`` and ``properties`` deliberately retain the textual precision of the source and map
    directly to the sheet JSON fields ``degats`` and ``attributs``.
    """

    id: ContentId
    name: str
    damage: str
    properties: tuple[str, ...]
    family: str

    @property
    def attributs(self) -> str:
        """Return the comma-separated value expected by inventory-item JSON."""

        return ", ".join(self.properties)


WEAPON_PROPERTIES = Catalog.from_items(
    [
        WeaponPropertyDefinition(ContentId(key), name, description)
        for key, name, description in [
            ("finesse", "Finesse", "Utilise Force ou Agilité pour attaque et dégâts."),
            ("light", "Légère", "Peut être utilisée pour une attaque à deux armes."),
            ("versatile", "Polyvalente", "Une ou deux mains; le dé augmenté est indiqué."),
            ("two_handed", "Deux mains", "Doit être maniée à deux mains."),
            ("thrown", "Lancer", "Peut être lancée à la portée indiquée."),
            ("ranged", "Distance", "Arme de tir utilisant l'Agilité."),
            ("improvised", "Improvisée", "Arme de fortune."),
            ("brute", "Brute", "Ne peut pas infliger de coups critiques."),
            ("light_shot", "Tir léger", "Tire en action ou bonus action, mais pas les deux."),
            ("reload", "Recharge", "Une bonus action recharge l'arme avant le tir."),
            (
                "secondary",
                "Secondaire",
                "Peut occuper la main secondaire avec une arme non légère.",
            ),
            (
                "guard",
                "Garde",
                "Parade d'épée droite à dé/2, versatile, donnant avantage après réussite.",
            ),
            (
                "brutality",
                "Brutalité",
                "Les critiques de hache lancent deux dés et peuvent se propager sur une paire.",
            ),
            (
                "impact",
                "Impact",
                "Ignore l'armure, réduit la parade et peut repousser sur critique.",
            ),
            (
                "fluid",
                "Fluide",
                "Échange désavantage présent contre avantage et gêne les opportunités.",
            ),
            ("reach", "Allonge", "Frappe à 3 m et étend les déclencheurs d'opportunité."),
            ("overhang", "Surplomb", "Avantage à au moins 5 m au-dessus de la cible."),
            ("piercing", "Perforant", "Ignore l'armure passive et divise la parade par deux."),
            ("bulwark", "Rempart", "Confère armure et parade propres au bouclier."),
            ("catalyst", "Catalyseur", "Canalise une couleur et utilise l'Esprit."),
            (
                "double_strike",
                "Double Frappe",
                "Action et bonus action pour une attaque combinée de Twinblade.",
            ),
            (
                "counter_thrust",
                "Contre d'Estoc",
                "Accorde avantage à l'assaillant puis permet parade et contre gratuit.",
            ),
            ("entangle", "Entrave", "Une opportunité réussie peut mettre la cible à terre."),
            (
                "unarmed",
                "Comme mains nues",
                "Bénéficie des effets améliorant les attaques à mains nues.",
            ),
            (
                "destabilization",
                "Déstabilisation",
                "Un critique donne désavantage à la prochaine attaque de la cible.",
            ),
        ]
    ]
)

WEAPON_FAMILIES = Catalog.from_items(
    [
        WeaponFamilyDefinition(ContentId(key), name, ContentId(prop))
        for key, name, prop in [
            ("straight_swords", "Épées droites", "guard"),
            ("curved_swords", "Épées courbes", "fluid"),
            ("axes", "Haches", "brutality"),
            ("clubs_hammers", "Massues et marteaux", "impact"),
            ("reach_weapons", "Armes d'allonge", "reach"),
            ("bows", "Arcs", "overhang"),
            ("crossbows", "Arbalètes", "piercing"),
            ("catalysts", "Catalyseurs", "catalyst"),
            ("shields", "Boucliers", "bulwark"),
            ("unique_weapons", "Armes uniques", "destabilization"),
        ]
    ]
)


def _weapon(
    identifier: str, name: str, damage: str, properties: str, family: str
) -> OfficialWeapon:
    """Build a weapon row while keeping the source table readable."""

    return OfficialWeapon(
        ContentId(identifier),
        name,
        damage,
        tuple(item.strip() for item in properties.split(",")),
        family,
    )


WEAPONS = Catalog.from_items(
    [
        _weapon(
            "dagger",
            "Dague",
            "1d4, tranchant/perçant",
            "Finesse, Légère, Lancer (10m), Garde",
            "Épées droites",
        ),
        _weapon(
            "shortsword", "Épée courte", "1d6, tranchant/perçant", "Finesse, Garde", "Épées droites"
        ),
        _weapon(
            "longsword",
            "Épée longue",
            "1d8, tranchant/perçant",
            "Polyvalente (1d10), Garde",
            "Épées droites",
        ),
        _weapon(
            "greatsword", "Espadon", "1d12, tranchant/perçant", "Deux mains, Garde", "Épées droites"
        ),
        _weapon("sickle", "Serpe", "1d4, tranchant", "Légère, Fluide", "Épées courbes"),
        _weapon(
            "scimitar",
            "Épée courbe (cimeterre)",
            "1d6, tranchant",
            "Finesse, Légère, Fluide",
            "Épées courbes",
        ),
        _weapon(
            "katana", "Katana", "1d10, tranchant", "Finesse, Deux mains, Fluide", "Épées courbes"
        ),
        _weapon(
            "great_saber", "Grand sabre", "1d12, tranchant", "Deux mains, Fluide", "Épées courbes"
        ),
        _weapon(
            "hatchet", "Hachette", "1d6, tranchant", "Légère, Lancer (10m), Brutalité", "Haches"
        ),
        _weapon(
            "battleaxe",
            "Hache d'armes",
            "1d8, tranchant",
            "Polyvalente (1d10), Brutalité",
            "Haches",
        ),
        _weapon("greataxe", "Grande hache", "1d12, tranchant", "Deux mains, Brutalité", "Haches"),
        _weapon(
            "club", "Gourdin", "1d4, contondant", "Improvisée, Brute, Impact", "Massues et marteaux"
        ),
        _weapon(
            "warhammer",
            "Marteau de guerre",
            "1d8, contondant",
            "Polyvalente (1d10), Impact",
            "Massues et marteaux",
        ),
        _weapon(
            "maul", "Grand marteau", "1d12, contondant", "Deux mains, Impact", "Massues et marteaux"
        ),
        _weapon("quarterstaff", "Bâton long", "1d6, contondant", "Allonge", "Armes d'allonge"),
        _weapon("spear", "Lance", "1d8, perçant", "Polyvalente (1d10), Allonge", "Armes d'allonge"),
        _weapon(
            "halberd", "Hallebarde", "1d12, tranchant", "Deux mains, Allonge", "Armes d'allonge"
        ),
        _weapon(
            "scythe", "Faux", "1d10, tranchant", "Deux mains, Fluide, Allonge", "Armes d'allonge"
        ),
        _weapon(
            "twinblade", "Twinblade", "1d8, tranchant", "Deux mains, Double Frappe", "Armes uniques"
        ),
        _weapon("rapier", "Rapière", "1d8, perçant", "Finesse, Contre d'Estoc", "Armes uniques"),
        _weapon("whip", "Fouet", "1d6, tranchant", "Finesse, Entrave", "Armes uniques"),
        _weapon(
            "fist_weapons",
            "Fist weapons",
            "1d4, contondant",
            "Comme mains nues, Brute",
            "Armes uniques",
        ),
        _weapon("flail", "Fléau", "1d8, perçant", "Déstabilisation", "Armes uniques"),
        _weapon("shortbow", "Arc court", "1d6, perçant", "Distance, Deux mains, Surplomb", "Arcs"),
        _weapon("longbow", "Arc long", "1d8, perçant", "Distance, Deux mains, Surplomb", "Arcs"),
        _weapon(
            "hand_crossbow",
            "Arbalète de poing",
            "1d4, perçant",
            "Distance, Brute, Tir léger, Secondaire, Perforant",
            "Arbalètes",
        ),
        _weapon(
            "crossbow", "Arbalète", "1d8, perçant", "Distance, Deux mains, Perforant", "Arbalètes"
        ),
        _weapon(
            "heavy_crossbow",
            "Arbalète lourde",
            "1d12, perçant",
            "Distance, Deux mains, Recharge, Perforant",
            "Arbalètes",
        ),
        _weapon(
            "focus",
            "Focus",
            "1d4, magique/élémentaire",
            "Distance, Brute, Tir léger, Secondaire, Catalyseur",
            "Catalyseurs",
        ),
        _weapon(
            "magic_staff",
            "Bâton",
            "1d8, magique/élémentaire",
            "Distance, Deux mains, Catalyseur",
            "Catalyseurs",
        ),
        _weapon("shield", "Bouclier", "1d4, contondant", "Brute, Secondaire, Rempart", "Boucliers"),
    ]
)

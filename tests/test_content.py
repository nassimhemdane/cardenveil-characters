from cardenveil.content import CONDITIONS, DAMAGE_TYPES, RACES, SKILLS, WEAPONS
from cardenveil.content.official import validate_official_content
from cardenveil.domain import DamageCategory, Stat


def test_official_catalogs_load_and_resolve() -> None:
    assert RACES.get("aasimar").official
    assert SKILLS.get("arcana").associated_stat is Stat.SPIRIT
    assert DAMAGE_TYPES.get("fire").category is DamageCategory.ELEMENTAL
    assert WEAPONS.get("longsword").damage == "1d8, tranchant/perçant"
    assert CONDITIONS.get("blinded").source_rule_ids


def test_all_official_content_is_valid() -> None:
    validate_official_content()

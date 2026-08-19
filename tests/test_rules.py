import pytest

from cardenveil.content.catalog import Catalog
from cardenveil.domain import ContentId
from cardenveil.errors import ValidationError
from cardenveil.rules import Rule, RuleSource, RuleStatus, rules


def test_rulebook_queries_and_unresolved_status() -> None:
    assert rules.get("character.stats.modifier").formula
    assert rules.get("character.health.max").status is RuleStatus.UNRESOLVED
    assert len({str(rule.id) for rule in rules.all()}) == len(rules.all())


def test_duplicate_rule_ids_are_rejected() -> None:
    rule = Rule(
        ContentId("test.rule"), "Test", "test", "Texte autonome.", RuleSource("test", "test")
    )
    with pytest.raises(ValidationError):
        Catalog.from_items([rule, rule])

"""Pure derived calculations backed by canonical rule IDs."""

from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def implements_rule(rule_id: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Attach the implemented natural-rule ID to a derived function."""

    def decorate(function: Callable[P, R]) -> Callable[P, R]:
        """Annotate and return the original derived function."""
        function.__rule_id__ = rule_id  # type: ignore[attr-defined]
        return function

    return decorate


@implements_rule("character.stats.modifier")
def modifier(score: int) -> int:
    """Return floor((score - 10) / 2); valid for the domain score range."""
    if not 0 <= score <= 20:
        raise ValueError("score must be between 0 and 20")
    return (score - 10) // 2

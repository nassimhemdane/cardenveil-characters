"""Structured validation beyond constructor-level invariants."""

from dataclasses import dataclass
from enum import StrEnum

from cardenveil.domain import Character


class Severity(StrEnum):
    """Severity attached to a structured validation issue."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One validation diagnostic with a stable code and object path."""

    code: str
    path: str
    message: str
    severity: Severity


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Collection of diagnostics returned by character validation."""

    issues: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        """Return whether the result contains no error-level issue."""
        return not any(issue.severity is Severity.ERROR for issue in self.issues)


def validate_character(character: Character) -> ValidationResult:
    """Validate stable V1 constraints without applying disputed game rules."""
    issues: list[ValidationIssue] = []
    stat_total = (
        character.stats.force
        + character.stats.agilite
        + character.stats.esprit
        + character.stats.social
    )
    if stat_total != 52:
        issues.append(
            ValidationIssue(
                "stats.total.nonstandard",
                "stats",
                "The creation baseline is 52 points; evolved or imported characters may differ.",
                Severity.WARNING,
            )
        )
    return ValidationResult(tuple(issues))

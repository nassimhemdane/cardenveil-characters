"""Review and apply binary decisions between PDF candidates and final character archives."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

from cardenveil.domain import Character
from cardenveil.importers.pdf.models import ExtractedCharacter
from cardenveil.naming import slugify_character_id
from cardenveil.serialization import (
    character_from_archive,
    character_from_dict,
    character_to_dict,
    character_to_json,
)

JsonValue = str | int | float | bool | None | list[object] | dict[str, object]
_MARKER = re.compile(r"<!-- CARDENVEIL_ISSUE ([A-Za-z0-9_=-]+) -->")


@dataclass(frozen=True, slots=True)
class ReviewIssue:
    """One machine-readable review item rendered as exactly two Markdown choices."""

    id: str
    kind: str
    character_name: str
    source_pdf: str
    target_archive: str
    candidate_archive: str
    description: str
    json_path: str = ""
    option_a_label: str = ""
    option_a_value: JsonValue = None
    option_b_label: str = ""
    option_b_value: JsonValue = None
    evidence_a: str = ""
    evidence_b: str = ""


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    """A parsed issue together with the user's checked option, or no valid choice yet."""

    issue: ReviewIssue
    choice: str | None
    error: str = ""


def index_archives_by_character_name(directory: str | Path) -> dict[str, Path]:
    """Index ZIPs by normalized ``identity.nom`` and reject ambiguous duplicate identities."""

    result: dict[str, Path] = {}
    for archive in sorted(Path(directory).glob("*.zip")):
        character = character_from_archive(archive)
        key = slugify_character_id(character.identity.nom)
        if not key:
            raise ValueError(f"Character has no usable identity.nom: {archive}")
        if key in result:
            raise ValueError(
                f"Duplicate character name {character.identity.nom!r}: "
                f"{result[key].name} and {archive.name}"
            )
        result[key] = archive
    return result


def make_issue(**values: object) -> ReviewIssue:
    """Create a stable issue ID from its semantic content rather than processing order."""

    identity = json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)
    issue_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return ReviewIssue(id=issue_id, **values)  # type: ignore[arg-type]


def extracted_character_proposals(
    extracted: ExtractedCharacter,
    candidate: Character,
) -> list[tuple[str, JsonValue]]:
    """Return only canonical values explicitly grounded in Gemini's sparse extraction."""

    mapped = character_to_dict(candidate)
    paths: list[str] = []
    _add_model_paths(paths, "/identity", extracted.identity, exclude={"nom"})
    _add_model_paths(paths, "/stats", extracted.stats)
    _add_model_paths(paths, "/progression", extracted.progression)
    _add_model_paths(paths, "/derived", extracted.derived)
    _add_model_paths(paths, "/defense", extracted.defense)
    _add_model_paths(
        paths,
        "/resources",
        extracted.resources,
        aliases={"or_": "or"},
        exclude={"token_force", "token_agilite", "token_esprit", "token_social"},
    )
    for stat in ("force", "agilite", "esprit", "social"):
        if getattr(extracted.resources, f"token_{stat}") is not None:
            paths.append(f"/resources/tokens/{stat}")
    _add_model_paths(paths, "/totem", extracted.totem)
    _add_model_paths(paths, "/narrative", extracted.narrative)
    _add_model_paths(paths, "/equipment", extracted.equipment)
    if extracted.weapons:
        paths.append("/weapons")
    if extracted.capacities:
        paths.append("/capacities")
    if extracted.weaponMasteries:
        paths.append("/weaponMasteries")
    if extracted.elementalMasteries:
        paths.append("/elementalMasteries")
    if extracted.feats:
        paths.append("/feats")
    if extracted.notes is not None:
        paths.append("/notes")

    proposals: list[tuple[str, JsonValue]] = []
    for path in sorted(set(paths)):
        try:
            value = json_pointer_get(mapped, path)
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        proposals.append((path, value))  # type: ignore[arg-type]
    return proposals


def comparison_issues(
    *,
    extracted: ExtractedCharacter,
    candidate: Character,
    current: Character,
    source_pdf: Path,
    target_archive: Path,
    candidate_archive: Path,
) -> list[ReviewIssue]:
    """Build field-level current-versus-PDF choices without treating absent data as empty."""

    current_data = character_to_dict(current)
    issues: list[ReviewIssue] = []
    for path, proposed in extracted_character_proposals(extracted, candidate):
        try:
            existing = json_pointer_get(current_data, path)
        except (KeyError, IndexError, TypeError, ValueError):
            existing = None
        if path == "/capacities" and isinstance(proposed, list):
            proposed = _preserve_capacity_images(proposed, existing)
        if existing == proposed:
            continue
        issues.append(
            make_issue(
                kind="field",
                character_name=candidate.identity.nom,
                source_pdf=source_pdf.name,
                target_archive=target_archive.name,
                candidate_archive=candidate_archive.as_posix(),
                description=(
                    "La valeur finale et la valeur visible dans le PDF diffèrent "
                    f"pour {path}."
                ),
                json_path=path,
                option_a_label="Conserver la valeur de l'archive Final",
                option_a_value=existing,
                option_b_label="Appliquer la valeur extraite du PDF",
                option_b_value=proposed,
                evidence_a=f"Archive {target_archive.name}",
                evidence_b=f"PDF {source_pdf.name}",
            )
        )
    return issues


def internal_inconsistency_issues(
    *,
    extracted: ExtractedCharacter,
    character_name: str,
    source_pdf: Path,
    target_archive: Path,
    candidate_archive: Path,
) -> list[ReviewIssue]:
    """Translate Gemini's two-valued visible contradictions into review issues."""

    return [
        make_issue(
            kind="internal",
            character_name=character_name,
            source_pdf=source_pdf.name,
            target_archive=target_archive.name,
            candidate_archive=candidate_archive.as_posix(),
            description=item.description,
            json_path=item.json_path,
            option_a_label=item.option_a_label,
            option_a_value=item.option_a_value,
            option_b_label=item.option_b_label,
            option_b_value=item.option_b_value,
            evidence_a=item.evidence_a,
            evidence_b=item.evidence_b,
        )
        for item in extracted.inconsistencies
    ]


def render_review_report(
    issues: list[ReviewIssue],
    destination: str | Path,
    *,
    warnings: list[str] | None = None,
) -> Path:
    """Write the editable Markdown protocol while embedding immutable issue metadata."""

    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Incohérences des fiches Cardenveil",
        "",
        "Cochez exactement un choix (`A` ou `B`) pour chaque incohérence à traiter.",
        "Laissez les deux cases vides pour reporter une décision. Ne modifiez pas les commentaires",
        "`CARDENVEIL_ISSUE` : ils permettent au script de correction de relire vos choix.",
        "",
        f"Nombre d'incohérences : **{len(issues)}**",
        "",
    ]
    grouped: dict[str, list[ReviewIssue]] = {}
    for issue in issues:
        grouped.setdefault(issue.character_name, []).append(issue)
    for character_name, character_issues in grouped.items():
        lines.extend([f"## {character_name}", ""])
        for number, issue in enumerate(character_issues, start=1):
            payload = json.dumps(asdict(issue), ensure_ascii=False, separators=(",", ":"))
            marker = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
            lines.extend(
                [
                    f"### {number}. {issue.description}",
                    "",
                    f"Source : `{issue.source_pdf}`  ",
                    f"Champ : `{issue.json_path or '(personnage complet)'}`",
                    "",
                    f"<!-- CARDENVEIL_ISSUE {marker} -->",
                    f"- [ ] A — {issue.option_a_label} : `{_display(issue.option_a_value)}`",
                    "",
                    f"- [ ] B — {issue.option_b_label} : `{_display(issue.option_b_value)}`",
                    "",
                    f"Preuve A : {issue.evidence_a or 'sans objet'}  ",
                    f"Preuve B : {issue.evidence_b or 'sans objet'}",
                    "",
                ]
            )
    if warnings:
        lines.extend(["## Avertissements sans correction automatique", ""])
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def parse_review_report(path: str | Path) -> list[ReviewDecision]:
    """Parse checked choices from a report and reject missing or double selections per issue."""

    content = Path(path).read_text(encoding="utf-8")
    matches = list(_MARKER.finditer(content))
    decisions: list[ReviewDecision] = []
    for index, match in enumerate(matches):
        encoded = match.group(1)
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding).decode("utf-8"))
        issue = ReviewIssue(**payload)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        block = content[match.end() : end]
        checked_a = bool(re.search(r"^- \[[xX]\] A\s", block, flags=re.MULTILINE))
        checked_b = bool(re.search(r"^- \[[xX]\] B\s", block, flags=re.MULTILINE))
        if checked_a and checked_b:
            decisions.append(ReviewDecision(issue, None, "A et B sont cochés"))
        elif not checked_a and not checked_b:
            decisions.append(ReviewDecision(issue, None, "aucun choix coché"))
        else:
            decisions.append(ReviewDecision(issue, "A" if checked_a else "B"))
    return decisions


def json_pointer_get(document: object, pointer: str) -> object:
    """Read a value using RFC 6901 object keys and numeric list indexes."""

    current = document
    for token in _pointer_tokens(pointer):
        if isinstance(current, dict):
            current = current[token]
        elif isinstance(current, list):
            current = current[int(token)]
        else:
            raise TypeError(f"Cannot traverse {pointer!r} through a scalar")
    return current


def json_pointer_set(document: object, pointer: str, value: object) -> None:
    """Replace an existing value through a JSON Pointer without creating schema fields."""

    tokens = _pointer_tokens(pointer)
    if not tokens:
        raise ValueError("The root character object cannot be replaced")
    parent = document
    for token in tokens[:-1]:
        if isinstance(parent, dict):
            parent = parent[token]
        elif isinstance(parent, list):
            parent = parent[int(token)]
        else:
            raise TypeError(f"Cannot traverse {pointer!r} through a scalar")
    final = tokens[-1]
    if isinstance(parent, dict):
        if final not in parent:
            raise KeyError(f"Unknown field in JSON Pointer: {pointer}")
        parent[final] = value
    elif isinstance(parent, list):
        parent[int(final)] = value
    else:
        raise TypeError(f"Cannot set {pointer!r} on a scalar")


def patch_character_archive(
    archive_path: str | Path,
    changes: list[tuple[str, JsonValue]],
) -> Character:
    """Validate patches through the core and atomically replace only the archive JSON member."""

    path = Path(archive_path)
    character = character_from_archive(path)
    payload = character_to_dict(character)
    for pointer, value in changes:
        json_pointer_set(payload, pointer, value)
    updated = character_from_dict(payload)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as target:
            for info in source.infolist():
                if not info.filename.endswith(".rpsheet.json"):
                    target.writestr(info, source.read(info.filename))
            target.writestr(f"{updated.id}.rpsheet.json", character_to_json(updated) + "\n")
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return updated


def _add_model_paths(
    paths: list[str],
    prefix: str,
    model: object,
    *,
    aliases: dict[str, str] | None = None,
    exclude: set[str] | None = None,
) -> None:
    """Collect leaf paths whose extracted Pydantic values are genuinely present."""

    aliases = aliases or {}
    exclude = exclude or set()
    for name in model.__class__.model_fields:  # type: ignore[attr-defined]
        if name in exclude:
            continue
        value = getattr(model, name)
        if value is None or value == []:
            continue
        key = aliases.get(name, name)
        if hasattr(value, "__class__") and hasattr(value.__class__, "model_fields"):
            _add_model_paths(paths, f"{prefix}/{key}", value)
        else:
            paths.append(f"{prefix}/{key}")


def _pointer_tokens(pointer: str) -> list[str]:
    """Decode a canonical JSON Pointer into unescaped path tokens."""

    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError(f"Invalid JSON Pointer: {pointer!r}")
    return [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]


def _display(value: object) -> str:
    """Render JSON values compactly without exposing Markdown control characters."""

    rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    rendered = rendered.replace("`", "'").replace("\n", " ")
    return rendered if len(rendered) <= 500 else rendered[:497] + "..."


def _preserve_capacity_images(proposed: list[object], existing: object) -> list[object]:
    """Keep Final image references when comparing semantic capacity data from a PDF."""

    result = copy.deepcopy(proposed)
    current_items = existing if isinstance(existing, list) else []
    for index, item in enumerate(result):
        if not isinstance(item, dict):
            continue
        current = current_items[index] if index < len(current_items) else None
        current_image = current.get("image", "") if isinstance(current, dict) else ""
        item["image"] = current_image
    return result

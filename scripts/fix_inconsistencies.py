"""Apply checked choices from ``Final/INCOHERENCES.md`` to validated character archives."""

from __future__ import annotations

import argparse
import shutil
from datetime import UTC, datetime
from pathlib import Path

from cardenveil.reconciliation import (
    json_pointer_get,
    json_pointer_set,
    parse_review_report,
    patch_character_archive,
)
from cardenveil.serialization import character_from_archive, character_to_dict


def build_parser() -> argparse.ArgumentParser:
    """Create report, Final directory, and explicit replacement-policy arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("Final"))
    parser.add_argument("--report", type=Path, default=Path("Final/INCOHERENCES.md"))
    parser.add_argument(
        "--overwrite-new",
        action="store_true",
        help="Allow a checked creation choice to replace a target created since analysis",
    )
    parser.add_argument(
        "--default-a",
        action="store_true",
        help="Interpret every issue with no checked box as choice A",
    )
    return parser


def main() -> int:
    """Validate decisions, patch selected fields, and create only explicitly approved sheets."""

    arguments = build_parser().parse_args()
    if not arguments.report.is_file():
        print(f"[STOPPED] Review report does not exist: {arguments.report}")
        return 2

    decisions = parse_review_report(arguments.report)
    ambiguous = [decision for decision in decisions if decision.error == "A et B sont cochés"]
    if ambiguous:
        for decision in ambiguous:
            print(
                f"[INVALID] {decision.issue.character_name} / {decision.issue.id}: "
                f"{decision.error}"
            )
        print("[STOPPED] Uncheck one option in every invalid issue before applying changes.")
        return 2

    output = arguments.output.resolve()
    backups = output / "Backups"
    modifications: dict[Path, list[tuple[str, object]]] = {}
    payloads: dict[Path, dict[str, object]] = {}
    creations = []
    pending = 0
    defaulted = 0
    already_satisfied = 0

    for decision in decisions:
        issue = decision.issue
        choice = decision.choice
        if choice is None:
            if not arguments.default_a:
                pending += 1
                continue
            choice = "A"
            defaulted += 1
        if issue.kind == "create":
            if choice == "B":
                creations.append(issue)
            continue
        if issue.kind not in {"field", "internal"}:
            print(f"[STOPPED] Unsupported issue kind: {issue.kind!r}")
            return 2
        if not issue.json_path:
            print(f"[STOPPED] Issue has no JSON path: {issue.id}")
            return 2

        final_target = _safe_child(output, Path(issue.target_archive))
        candidate = _safe_child(output, Path(issue.candidate_archive))
        archive = final_target if final_target.is_file() else candidate
        if not archive.is_file():
            print(f"[STOPPED] Archive required by issue {issue.id} is missing: {archive}")
            return 2
        value = issue.option_a_value if choice == "A" else issue.option_b_value
        if archive not in payloads:
            payloads[archive] = character_to_dict(character_from_archive(archive))
        payload = payloads[archive]
        try:
            current = json_pointer_get(payload, issue.json_path)
        except Exception as error:
            print(f"[STOPPED] Invalid path in issue {issue.id}: {error}")
            return 2
        if current == value:
            already_satisfied += 1
            continue
        json_pointer_set(payload, issue.json_path, value)
        modifications.setdefault(archive, []).append((issue.json_path, value))

    modified = 0
    for archive, changes in modifications.items():
        try:
            if archive.parent == output:
                backups.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                backup = backups / f"{archive.stem}.before-fix-{stamp}.zip"
                shutil.copy2(archive, backup)
            patch_character_archive(archive, changes)  # validates via cardenveil-core
            modified += 1
            print(f"[PATCHED] {archive} ({len(changes)} choice(s))")
        except Exception as error:
            print(f"[FAILED] {archive}: {type(error).__name__}: {error}")
            return 1

    created = 0
    skipped = 0
    for issue in creations:
        source = _safe_child(output, Path(issue.candidate_archive))
        target = _safe_child(output, Path(issue.target_archive))
        if not source.is_file():
            print(f"[FAILED] Missing candidate for {issue.character_name}: {source}")
            return 1
        if target.exists() and not arguments.overwrite_new:
            skipped += 1
            print(f"[SKIPPED] Target already exists and was not overwritten: {target.name}")
            continue
        if target.exists():
            backups.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            shutil.copy2(target, backups / f"{target.stem}.before-create-{stamp}.zip")
        shutil.copy2(source, target)
        created += 1
        print(f"[CREATED] {target.name} from {source.relative_to(output)}")

    print(
        f"Summary: modified={modified} created={created} skipped={skipped} "
        f"already_satisfied={already_satisfied} defaulted_to_a={defaulted} "
        f"pending={pending} total={len(decisions)}"
    )
    return 0


def _safe_child(root: Path, relative: Path) -> Path:
    """Resolve an issue path and reject absolute or parent-traversal targets."""

    if relative.is_absolute():
        raise ValueError(f"Absolute review path is forbidden: {relative}")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"Review path escapes Final: {relative}")
    return resolved


if __name__ == "__main__":
    raise SystemExit(main())

"""Repair zero ability costs from formulas already transcribed from the source PDFs."""

from __future__ import annotations

import re
import shutil
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from cardenveil.reconciliation import patch_character_archive
from cardenveil.serialization import character_from_archive

FORMULA = re.compile(r"^\s*(\d+)\s*[-−–]\s*(\d+)\s*=\s*(\d+)\s*$")


def main() -> int:
    """Back up affected archives, apply proven costs, and reject ambiguous expressions."""

    final = Path("Final").resolve()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_root = final / "Problematiques" / "costs" / "originals" / stamp
    changes_by_archive: dict[Path, list[tuple[str, object]]] = defaultdict(list)
    unresolved: list[str] = []

    for archive in sorted(final.glob("*.zip")):
        character = character_from_archive(archive)
        for index, ability in enumerate(character.capacities):
            if ability.cost.total != 0:
                continue
            printed = ability.value.bonus.strip()
            match = FORMULA.fullmatch(printed)
            if match:
                base, reduction, total = (int(value) for value in match.groups())
                if base - reduction != total or total <= 0:
                    unresolved.append(
                        f"{character.identity.nom} / {ability.name}: "
                        f"formule incohérente {printed!r}"
                    )
                    continue
            elif printed.isdigit() and int(printed) > 0:
                base = total = int(printed)
                reduction = 0
            else:
                unresolved.append(
                    f"{character.identity.nom} / {ability.name}: coût illisible {printed!r}"
                )
                continue
            prefix = f"/capacities/{index}"
            changes_by_archive[archive].extend(
                [
                    (f"{prefix}/cost/base", base),
                    (f"{prefix}/cost/incantationReduction", reduction),
                    (f"{prefix}/cost/total", total),
                    (f"{prefix}/value/bonus", ""),
                ]
            )

    if unresolved:
        print("[STOPPED] Ambiguous costs remain; no archive was modified:")
        for item in unresolved:
            print(f"- {item}")
        return 2
    if not changes_by_archive:
        print("No zero total ability cost requires repair.")
        return 0

    backup_root.mkdir(parents=True, exist_ok=True)
    abilities = 0
    for archive, changes in changes_by_archive.items():
        shutil.copy2(archive, backup_root / archive.name)
        patch_character_archive(archive, changes)
        repaired_count = len(changes) // 4
        abilities += repaired_count
        print(f"[REPAIRED] {archive.name}: {repaired_count} ability cost(s)")

    remaining = []
    for archive in sorted(final.glob("*.zip")):
        character = character_from_archive(archive)
        remaining.extend(
            f"{character.identity.nom} / {ability.name}"
            for ability in character.capacities
            if ability.cost.total == 0
        )
    if remaining:
        print(f"[FAILED] {len(remaining)} zero costs remain after repair")
        return 1
    print(
        f"Summary: characters={len(changes_by_archive)} abilities={abilities} "
        f"remaining=0 backups={backup_root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

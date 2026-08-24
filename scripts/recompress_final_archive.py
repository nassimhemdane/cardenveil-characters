"""Recompress one Final character archive and quarantine its original ZIP."""

from __future__ import annotations

import argparse
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from cardenveil.importers.archive import normalize_character_archive
from cardenveil.serialization import character_from_archive


def build_parser() -> argparse.ArgumentParser:
    """Create the targeted archive and Final-directory arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="ZIP filename or path inside Final")
    parser.add_argument("--final", type=Path, default=Path("Final"))
    return parser


def main() -> int:
    """Stage, validate, quarantine, and install one compressed archive with rollback."""

    arguments = build_parser().parse_args()
    final = arguments.final.resolve()
    source = arguments.archive
    if not source.is_absolute():
        source = final / source
    source = source.resolve()
    if source.parent != final or not source.is_file() or source.suffix.lower() != ".zip":
        print(f"[STOPPED] Expected one existing ZIP directly inside Final: {source}")
        return 2

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    problem_root = final / "Problematiques" / "compression"
    work = problem_root / "work" / stamp
    originals = problem_root / "originals" / stamp
    work.mkdir(parents=True, exist_ok=True)
    originals.mkdir(parents=True, exist_ok=True)

    original_bytes = source.stat().st_size
    extras = _read_extra_members(source)
    result = normalize_character_archive(source, work, overwrite=True)
    staged = result.destination
    _append_extra_members(staged, extras)
    character = character_from_archive(staged)
    target = final / staged.name
    if target.exists() and target.resolve() != source:
        print(f"[STOPPED] Refusing to overwrite another Final archive: {target}")
        return 2

    quarantined = originals / source.name
    shutil.move(source, quarantined)
    try:
        shutil.move(staged, target)
        installed = character_from_archive(target)
        if installed.id != character.id:
            raise ValueError("Installed character ID changed during move")
    except Exception:
        target.unlink(missing_ok=True)
        if quarantined.exists():
            shutil.move(quarantined, source)
        raise

    compressed_bytes = target.stat().st_size
    reduction = 100 * (1 - compressed_bytes / original_bytes)
    print(
        f"[COMPRESSED] {source.name} -> {target.name}; images={result.image_count}; "
        f"{original_bytes / 1_048_576:.2f} MiB -> "
        f"{compressed_bytes / 1_048_576:.2f} MiB ({reduction:.1f}% reduction)"
    )
    print(f"[ORIGINAL] {quarantined}")
    return 0


def _read_extra_members(path: Path) -> list[tuple[str, bytes]]:
    """Preserve non-character, non-asset members such as optional metadata.json."""

    with zipfile.ZipFile(path) as archive:
        return [
            (name, archive.read(name))
            for name in archive.namelist()
            if not name.endswith("/")
            and not name.endswith(".rpsheet.json")
            and not name.startswith("assets/")
        ]


def _append_extra_members(path: Path, members: list[tuple[str, bytes]]) -> None:
    """Restore preserved auxiliary files after canonical archive normalization."""

    if not members:
        return
    with zipfile.ZipFile(path, "a", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in members:
            archive.writestr(name, payload)


if __name__ == "__main__":
    raise SystemExit(main())

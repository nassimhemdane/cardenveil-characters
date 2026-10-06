"""Normalize Final's text and empty its gear, preserving assets and backing up changed archives."""

from __future__ import annotations

from datetime import UTC, datetime

from apply_october_updates import ROOT, rewrite

from cardenveil.importers.sheet_cleanup import normalize_and_empty_gear


def main() -> None:
    """Run the explicit archive migration; the lossless serializer itself is unchanged."""
    backup = ROOT / "Final/Backups" / ("plain-text-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    changed = 0
    for archive in sorted((ROOT / "Final").glob("*.zip")):
        if rewrite(archive, backup, normalize_and_empty_gear):
            changed += 1
            print(f"[NORMALIZED] {archive.name}")
    print(f"Updated {changed} archives. Originals: {backup}")


if __name__ == "__main__":
    main()

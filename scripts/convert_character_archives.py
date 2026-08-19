"""Normalize every existing character ZIP without invoking Gemini.

Run from the project root:
``py -3.11 scripts/convert_character_archives.py``
Use ``--overwrite`` to rebuild characters already present in ``Final``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cardenveil.importers.archive import normalize_character_archive


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for source, destination, and overwrite policy."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("Toconvert"))
    parser.add_argument("--output", type=Path, default=Path("Final"))
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing Final/<character-id>.zip archive",
    )
    return parser


def main() -> int:
    """Convert archives sequentially, continue after errors, and print a useful summary."""

    arguments = build_parser().parse_args()
    sources = sorted(arguments.source.glob("*.zip"))
    if not sources:
        print(f"No ZIP archive found in {arguments.source}")
        return 1

    counters = {"created": 0, "overwritten": 0, "skipped": 0, "failed": 0}
    original_total = 0
    normalized_total = 0
    for source in sources:
        try:
            result = normalize_character_archive(
                source,
                arguments.output,
                overwrite=arguments.overwrite,
            )
        except Exception as error:
            counters["failed"] += 1
            print(f"[FAILED] {source.name}: {type(error).__name__}: {error}")
            continue
        counters[result.status] += 1
        original_total += result.original_bytes
        normalized_total += result.normalized_bytes
        print(
            f"[{result.status.upper()}] {source.name} -> {result.destination.name} "
            f"({result.image_count} images, "
            f"{result.original_bytes / 1_048_576:.2f} MiB -> "
            f"{result.normalized_bytes / 1_048_576:.2f} MiB)"
        )

    print(
        "Summary: "
        f"created={counters['created']} overwritten={counters['overwritten']} "
        f"skipped={counters['skipped']} failed={counters['failed']} "
        f"size={original_total / 1_048_576:.2f} MiB -> "
        f"{normalized_total / 1_048_576:.2f} MiB"
    )
    return 1 if counters["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

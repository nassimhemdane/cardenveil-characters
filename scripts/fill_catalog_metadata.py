"""Fill catalogue metadata with constrained, non-inventive Gemini structured output."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from cardenveil.importers.pdf import GeminiCharacterDocumentExtractor, GeminiConfig
from cardenveil.naming import slugify_character_id
from cardenveil.reconciliation import parse_review_report
from cardenveil.serialization import character_from_archive, character_to_json


def build_parser() -> argparse.ArgumentParser:
    """Create safe paths, resume policy, quota limit, and bounded request arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final", type=Path, default=Path("Final"))
    parser.add_argument("--source", type=Path, default=Path("Toconvert"))
    parser.add_argument("--review", type=Path, default=Path("Final/INCOHERENCES.md"))
    parser.add_argument("--metadata", type=Path, default=Path("web/catalog-metadata.json"))
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate entries that already contain at least one metadata value",
    )
    return parser


def main() -> int:
    """Process characters sequentially and persist each validated response for safe resume."""

    arguments = build_parser().parse_args()
    document = json.loads(arguments.metadata.read_text(encoding="utf-8"))
    entries = document.setdefault("characters", {})
    for metadata in entries.values():
        if isinstance(metadata, dict) and metadata.get("class") == "":
            metadata["class"] = []
    _write_document(arguments.metadata, document)
    pdf_by_name = _source_pdf_index(arguments.review, arguments.source)
    archives = sorted(arguments.final.glob("*.zip"))
    if arguments.limit is not None:
        if arguments.limit < 1:
            print("[STOPPED] --limit must be at least 1")
            return 2
        archives = archives[: arguments.limit]

    base_config = GeminiConfig.from_env(arguments.env_file)
    extractor = GeminiCharacterDocumentExtractor(
        replace(
            base_config,
            request_timeout_seconds=arguments.timeout,
            max_attempts=arguments.max_attempts,
        )
    )
    completed = 0
    skipped = 0
    failed = 0
    for position, archive in enumerate(archives, start=1):
        character = character_from_archive(archive)
        current = entries.setdefault(character.id, _empty_metadata())
        if not arguments.overwrite and _has_metadata(current):
            skipped += 1
            print(f"[{position}/{len(archives)}] [SKIPPED] {character.identity.nom}", flush=True)
            continue
        pdfs = pdf_by_name.get(slugify_character_id(character.identity.nom), [])
        print(
            f"[{position}/{len(archives)}] Gemini: {character.identity.nom} "
            f"({'PDF' if len(pdfs) == 1 else 'JSON'})",
            flush=True,
        )
        try:
            if len(pdfs) == 1:
                extracted = extractor.extract_catalog_metadata(pdfs[0])
            else:
                extracted = extractor.extract_catalog_metadata_from_json(
                    character_to_json(character, indent=None)
                )
                extracted.creator = ""
            metadata = extracted.model_dump(mode="json", by_alias=True)
            metadata["loreSummary"] = _one_line(metadata["loreSummary"])
            metadata["gameplaySummary"] = _one_line(metadata["gameplaySummary"])
            metadata["creator"] = _one_line(metadata["creator"])
            entries[character.id] = metadata
            _write_document(arguments.metadata, document)
            completed += 1
            print(
                f"  [OK] class={metadata['class']} difficulty={metadata['difficulty']} "
                f"creator={metadata['creator']!r}",
                flush=True,
            )
        except Exception as error:
            failed += 1
            cause = error.__cause__
            detail = f"; cause={type(cause).__name__}: {cause}" if cause else ""
            print(f"  [FAILED] {type(error).__name__}: {error}{detail}", flush=True)

    print(
        f"Summary: completed={completed} skipped={skipped} failed={failed} "
        f"metadata={arguments.metadata}",
        flush=True,
    )
    return 1 if failed else 0


def _source_pdf_index(review: Path, source: Path) -> dict[str, list[Path]]:
    """Map internal character names to real ToConvert PDFs through immutable report metadata."""

    names: dict[str, set[str]] = defaultdict(set)
    for decision in parse_review_report(review):
        names[slugify_character_id(decision.issue.character_name)].add(
            decision.issue.source_pdf
        )
    return {
        key: [source / name for name in sorted(values) if (source / name).is_file()]
        for key, values in names.items()
    }


def _empty_metadata() -> dict[str, object]:
    """Return the exact empty editorial shape used when no information is available."""

    return {
        "loreSummary": "",
        "gameplaySummary": "",
        "difficulty": None,
        "creator": "",
        "class": [],
    }


def _has_metadata(metadata: object) -> bool:
    """Detect a previous response so interrupted batches can resume without spending quota."""

    return isinstance(metadata, dict) and any(
        value not in ("", None, []) for value in metadata.values()
    )


def _one_line(value: object) -> str:
    """Collapse provider whitespace so every textual field occupies at most one JSON line."""

    return " ".join(str(value).split()) if value else ""


def _write_document(path: Path, document: dict[str, object]) -> None:
    """Atomically persist validated progress after every character."""

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())

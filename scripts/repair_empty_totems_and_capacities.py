"""Re-extract PDF sections when a Final character has an empty totem or no capacities."""

from __future__ import annotations

import argparse
import shutil
from collections import defaultdict
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from cardenveil.importers.pdf import (
    CharacterMapper,
    ExtractedCharacter,
    GeminiCharacterDocumentExtractor,
    GeminiConfig,
    PDFImageAssetExtractor,
)
from cardenveil.naming import slugify_character_id
from cardenveil.reconciliation import parse_review_report
from cardenveil.serialization import (
    character_from_archive,
    character_to_archive,
    character_to_json,
)


def build_parser() -> argparse.ArgumentParser:
    """Create paths and bounded Gemini request options for the repair pass."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("Toconvert"))
    parser.add_argument("--output", type=Path, default=Path("Final"))
    parser.add_argument("--report", type=Path, default=Path("Final/INCOHERENCES.md"))
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--limit", type=int)
    return parser


def main() -> int:
    """Quarantine each bad archive only after a replacement passes semantic validation."""

    arguments = build_parser().parse_args()
    output = arguments.output.resolve()
    source = arguments.source.resolve()
    source_by_name = _source_pdf_index(arguments.report, source)
    problematic = []
    for archive in sorted(output.glob("*.zip")):
        character = character_from_archive(archive)
        empty_totem = _empty_totem(character)
        no_capacities = not character.capacities
        if empty_totem or no_capacities:
            problematic.append((archive, character, empty_totem, no_capacities))
    if arguments.limit is not None:
        if arguments.limit < 1:
            print("[STOPPED] --limit must be at least 1")
            return 2
        problematic = problematic[: arguments.limit]
    if not problematic:
        print("No character has an empty totem or an empty capacity list.")
        return 0

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    problem_root = output / "Problematiques"
    run_root = problem_root / "work" / stamp
    staged_root = problem_root / "reextracted" / stamp
    originals_root = problem_root / "originals"
    debug_root = problem_root / "debug" / stamp
    for directory in (run_root, staged_root, originals_root, debug_root):
        directory.mkdir(parents=True, exist_ok=True)

    base_config = GeminiConfig.from_env(arguments.env_file)
    extractor = GeminiCharacterDocumentExtractor(
        replace(
            base_config,
            request_timeout_seconds=arguments.timeout,
            max_attempts=arguments.max_attempts,
        )
    )
    mapper = CharacterMapper()
    results: list[str] = []
    repaired = 0
    failed = 0
    skipped = 0

    for position, (archive, current, empty_totem, no_capacities) in enumerate(
        problematic, start=1
    ):
        key = slugify_character_id(current.identity.nom)
        pdfs = source_by_name.get(key, [])
        reasons = ", ".join(
            item
            for item, active in (("totem vide", empty_totem), ("capacités vides", no_capacities))
            if active
        )
        print(
            f"[{position}/{len(problematic)}] {current.identity.nom}: {reasons}",
            flush=True,
        )
        if len(pdfs) != 1:
            skipped += 1
            message = f"SKIPPED — PDF source non unique ({[path.name for path in pdfs]})"
            results.append(f"- **{current.identity.nom}** — {message}")
            print(f"  [{message}]", flush=True)
            continue
        pdf_path = pdfs[0]
        try:
            sections = extractor.extract_totem_and_capacities(pdf_path)
            extracted = ExtractedCharacter(
                totem=sections.totem,
                capacities=sections.capacities,
                warnings=sections.warnings,
            )
            fresh = mapper.map(extracted, pdf_path)
            repaired_character = deepcopy(current)
            if empty_totem:
                repaired_character.totem.nom = fresh.totem.nom
                repaired_character.totem.description = fresh.totem.description
            if no_capacities:
                repaired_character.capacities = fresh.capacities
            repaired_character.updatedAt = datetime.now(UTC).isoformat()

            asset_root = run_root / current.id / "assets"
            asset_result = PDFImageAssetExtractor(asset_root).extract(
                pdf_path, repaired_character
            )
            remaining = []
            if empty_totem and _empty_totem(repaired_character):
                remaining.append("totem toujours vide")
            if no_capacities and not repaired_character.capacities:
                remaining.append("capacités toujours vides")
            if remaining:
                raise ValueError("; ".join(remaining))

            staged = staged_root / archive.name
            character_to_archive(repaired_character, staged, asset_root=asset_root)
            validated = character_from_archive(staged)
            if _empty_totem(validated) and empty_totem:
                raise ValueError("archive staged with an empty totem")
            if not validated.capacities and no_capacities:
                raise ValueError("archive staged without capacities")

            debug_directory = debug_root / current.id
            debug_directory.mkdir(parents=True, exist_ok=True)
            (debug_directory / "extracted_character.json").write_text(
                extracted.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8"
            )
            (debug_directory / "repaired_character.json").write_text(
                character_to_json(validated) + "\n", encoding="utf-8"
            )

            quarantined = originals_root / f"{archive.stem}.before-repair-{stamp}.zip"
            shutil.move(archive, quarantined)
            try:
                shutil.copy2(staged, archive)
            except Exception:
                if not archive.exists() and quarantined.exists():
                    shutil.move(quarantined, archive)
                raise
            repaired += 1
            warning_text = (
                f"; avertissements images={len(asset_result.warnings)}"
                if asset_result.warnings
                else ""
            )
            results.append(
                f"- **{current.identity.nom}** — réparé depuis `{pdf_path.name}`; "
                f"capacités={len(validated.capacities)}{warning_text}"
            )
            print(
                f"  [REPAIRED] totem={validated.totem.nom!r} "
                f"capacities={len(validated.capacities)}",
                flush=True,
            )
        except Exception as error:
            failed += 1
            cause = error.__cause__
            detail = f"; cause={type(cause).__name__}: {cause}" if cause else ""
            message = f"{type(error).__name__}: {error}{detail}"
            results.append(f"- **{current.identity.nom}** — ÉCHEC : {message}")
            print(f"  [FAILED] {message}", flush=True)

    report = problem_root / f"REEXTRACTION-{stamp}.md"
    report.write_text(
        "# Réextraction des fiches problématiques\n\n"
        f"- Réparées : {repaired}\n"
        f"- Échecs : {failed}\n"
        f"- Ignorées : {skipped}\n\n"
        + "\n".join(results)
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Summary: repaired={repaired} failed={failed} skipped={skipped} report={report}",
        flush=True,
    )
    return 1 if failed else 0


def _empty_totem(character: object) -> bool:
    """Treat a totem as empty when both semantic text fields are blank."""

    return not (
        str(character.totem.nom).strip() or str(character.totem.description).strip()  # type: ignore[attr-defined]
    )


def _source_pdf_index(report: Path, source: Path) -> dict[str, list[Path]]:
    """Map normalized character names to existing PDF files through the review manifest."""

    names: dict[str, set[str]] = defaultdict(set)
    for decision in parse_review_report(report):
        names[slugify_character_id(decision.issue.character_name)].add(
            decision.issue.source_pdf
        )
    return {
        key: [source / filename for filename in sorted(filenames) if (source / filename).is_file()]
        for key, filenames in names.items()
    }


if __name__ == "__main__":
    raise SystemExit(main())

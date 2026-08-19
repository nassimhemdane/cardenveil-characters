"""Extract PDFs with Gemini and create candidates plus a binary review report.

The analysis never modifies an existing ZIP directly in ``Final``. Character identity matching is
based exclusively on the normalized ``identity.nom`` stored inside archives and extracted PDFs.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from cardenveil.importers.pdf import (
    CharacterMapper,
    GeminiCharacterDocumentExtractor,
    GeminiConfig,
    PDFImageAssetExtractor,
)
from cardenveil.naming import slugify_character_id
from cardenveil.reconciliation import (
    comparison_issues,
    index_archives_by_character_name,
    internal_inconsistency_issues,
    make_issue,
    render_review_report,
)
from cardenveil.serialization import (
    character_from_archive,
    character_to_archive,
    character_to_json,
)


def build_parser() -> argparse.ArgumentParser:
    """Create safe source, output, overwrite, and quota-control arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("Toconvert"))
    parser.add_argument("--output", type=Path, default=Path("Final"))
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Maximum duration in seconds for one Gemini HTTP request",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=1,
        help="Provider attempts per operation; defaults to one to protect batch quota",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Analyze only the first N PDFs (useful for a low-quota validation run)",
    )
    parser.add_argument(
        "--overwrite-candidates",
        action="store_true",
        help="Rebuild existing ZIPs inside Final/Candidates; never overwrites Final/*.zip",
    )
    parser.add_argument(
        "--overwrite-report",
        action="store_true",
        help="Replace INCOHERENCES.md, including any choices already checked there",
    )
    return parser


def main() -> int:
    """Analyze every requested PDF, stage candidates, and document all review decisions."""

    arguments = build_parser().parse_args()
    report_path = arguments.output / "INCOHERENCES.md"
    if report_path.exists() and not arguments.overwrite_report:
        print(
            f"[STOPPED] {report_path} already exists. Preserve your choices or use "
            "--overwrite-report explicitly."
        )
        return 2

    pdfs = sorted(arguments.source.glob("*.pdf"))
    if arguments.limit is not None:
        if arguments.limit < 1:
            print("[STOPPED] --limit must be at least 1")
            return 2
        pdfs = pdfs[: arguments.limit]
    if not pdfs:
        print(f"No PDF found in {arguments.source}")
        return 1

    arguments.output.mkdir(parents=True, exist_ok=True)
    candidates_directory = arguments.output / "Candidates"
    assets_directory = candidates_directory / "assets"
    debug_directory = candidates_directory / "debug"
    candidates_directory.mkdir(parents=True, exist_ok=True)

    final_by_name = index_archives_by_character_name(arguments.output)
    base_config = GeminiConfig.from_env(arguments.env_file)
    extractor = GeminiCharacterDocumentExtractor(
        replace(
            base_config,
            max_attempts=arguments.max_attempts,
            request_timeout_seconds=arguments.timeout,
        )
    )
    mapper = CharacterMapper()
    asset_extractor = PDFImageAssetExtractor(assets_directory)
    issues = []
    warnings: list[str] = []
    failed = 0

    for position, pdf_path in enumerate(pdfs, start=1):
        print(f"[{position}/{len(pdfs)}] Gemini: {pdf_path.name}")
        try:
            extracted = extractor.extract(pdf_path)
            candidate = mapper.map(extracted, pdf_path)
            name_key = slugify_character_id(candidate.identity.nom)
            if not name_key:
                raise ValueError("Gemini did not extract a usable character name")

            candidate_path = candidates_directory / f"{candidate.id}.zip"
            if not candidate_path.exists() or arguments.overwrite_candidates:
                asset_result = asset_extractor.extract(pdf_path, candidate)
                warnings.extend(
                    f"{pdf_path.name}: image: {warning}" for warning in asset_result.warnings
                )
                character_to_archive(candidate, candidate_path, asset_root=assets_directory)
            else:
                candidate = character_from_archive(candidate_path)
                warnings.append(
                    f"{pdf_path.name}: candidat existant conservé ({candidate_path.name})."
                )

            character_debug = debug_directory / candidate.id
            character_debug.mkdir(parents=True, exist_ok=True)
            (character_debug / "extracted_character.json").write_text(
                extracted.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8"
            )
            (character_debug / "character_sheet.json").write_text(
                character_to_json(candidate) + "\n", encoding="utf-8"
            )

            existing_path = final_by_name.get(name_key)
            target_path = existing_path or (arguments.output / f"{candidate.id}.zip")
            relative_candidate = candidate_path.relative_to(arguments.output)
            issues.extend(
                internal_inconsistency_issues(
                    extracted=extracted,
                    character_name=candidate.identity.nom,
                    source_pdf=pdf_path,
                    target_archive=target_path,
                    candidate_archive=relative_candidate,
                )
            )
            if existing_path is not None:
                current = character_from_archive(existing_path)
                issues.extend(
                    comparison_issues(
                        extracted=extracted,
                        candidate=candidate,
                        current=current,
                        source_pdf=pdf_path,
                        target_archive=existing_path,
                        candidate_archive=relative_candidate,
                    )
                )
            else:
                issues.append(
                    make_issue(
                        kind="create",
                        character_name=candidate.identity.nom,
                        source_pdf=pdf_path.name,
                        target_archive=target_path.name,
                        candidate_archive=relative_candidate.as_posix(),
                        description="Aucune archive Final ne porte ce nom de personnage.",
                        option_a_label="Ignorer ce nouveau personnage",
                        option_a_value=False,
                        option_b_label="Créer l'archive Final depuis le candidat PDF",
                        option_b_value=True,
                        evidence_a="Aucune création",
                        evidence_b=f"Candidat {relative_candidate.as_posix()}",
                    )
                )
            warnings.extend(f"{pdf_path.name}: {warning}" for warning in extracted.warnings)
            print(
                f"  [OK] {candidate.identity.nom} -> {relative_candidate} "
                f"({'existant' if existing_path else 'nouveau'})"
            )
        except Exception as error:
            failed += 1
            cause = error.__cause__
            detail = (
                f"; cause={type(cause).__name__}: {cause}" if cause is not None else ""
            )
            failure = f"{type(error).__name__}: {error}{detail}"
            warnings.append(f"ÉCHEC {pdf_path.name}: {failure}")
            print(f"  [FAILED] {failure}")

    render_review_report(issues, report_path, warnings=warnings)
    print(
        f"Report: {report_path} | PDFs={len(pdfs)} failed={failed} "
        f"issues={len(issues)} warnings={len(warnings)}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

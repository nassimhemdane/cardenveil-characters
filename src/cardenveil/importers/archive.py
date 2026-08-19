"""First-pass normalization of existing character archives without any LLM dependency."""

from __future__ import annotations

import base64
import binascii
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from cardenveil.domain import Character
from cardenveil.errors import SerializationError
from cardenveil.importers.pdf.assets import ImageCompressionConfig, compress_image_to_png
from cardenveil.naming import slugify_character_id
from cardenveil.serialization import character_from_json, character_to_archive


@dataclass(frozen=True, slots=True)
class ArchiveNormalizationResult:
    """Outcome and size statistics for one source character archive."""

    source: Path
    destination: Path
    status: str
    original_id: str
    character_id: str
    image_count: int
    original_bytes: int
    normalized_bytes: int


def normalize_character_archive(
    source: str | Path,
    output_directory: str | Path,
    *,
    overwrite: bool = False,
    compression: ImageCompressionConfig | None = None,
) -> ArchiveNormalizationResult:
    """Roundtrip one archive through the core, rename it, externalize images, and compress them."""

    source_path = Path(source)
    destination_root = Path(output_directory)
    compression_config = compression or ImageCompressionConfig()
    try:
        with zipfile.ZipFile(source_path) as source_archive:
            json_members = [
                name for name in source_archive.namelist() if name.endswith(".rpsheet.json")
            ]
            if len(json_members) != 1:
                raise SerializationError(
                    f"{source_path.name} must contain exactly one .rpsheet.json file"
                )
            character = character_from_json(
                source_archive.read(json_members[0]).decode("utf-8-sig")
            )
            original_id = character.id
            character.id = slugify_character_id(str(character.identity.nom)) or original_id
            destination = destination_root / f"{character.id}.zip"
            destination_existed = destination.exists()
            if destination_existed and not overwrite:
                return ArchiveNormalizationResult(
                    source_path,
                    destination,
                    "skipped",
                    original_id,
                    character.id,
                    0,
                    source_path.stat().st_size,
                    destination.stat().st_size,
                )

            destination_root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(
                prefix=f".{character.id}-",
                dir=destination_root,
            ) as temporary:
                asset_root = Path(temporary) / "assets"
                image_count = _normalize_character_images(
                    source_archive,
                    character,
                    asset_root,
                    compression_config,
                )
                character_to_archive(character, destination, asset_root=asset_root)
    except zipfile.BadZipFile as error:
        raise SerializationError(f"Invalid ZIP archive: {source_path}") from error

    return ArchiveNormalizationResult(
        source_path,
        destination,
        "overwritten" if destination_existed else "created",
        original_id,
        character.id,
        image_count,
        source_path.stat().st_size,
        destination.stat().st_size,
    )


def _normalize_character_images(
    archive: zipfile.ZipFile,
    character: Character,
    asset_root: Path,
    compression: ImageCompressionConfig,
) -> int:
    """Externalize and compress every image reference while preserving its semantic position."""

    targets: list[tuple[object, str, str, int]] = [
        (character, "portrait", "portrait.png", compression.portrait_max_pixels),
        (character.totem, "image", "totem.png", compression.other_max_pixels),
    ]
    targets.extend(
        (capacity, "image", f"capacity-{index}.png", compression.other_max_pixels)
        for index, capacity in enumerate(character.capacities, start=1)
    )
    count = 0
    for owner, attribute, filename, max_pixels in targets:
        reference = getattr(owner, attribute)
        if not reference:
            continue
        source_bytes = _read_archive_image(archive, reference)
        output = asset_root / character.id / filename
        compress_image_to_png(
            source_bytes,
            output,
            max_pixels=max_pixels,
            palette_colors=compression.palette_colors,
        )
        setattr(owner, attribute, f"/assets/{character.id}/{filename}")
        count += 1
    return count


def _read_archive_image(archive: zipfile.ZipFile, reference: str) -> bytes:
    """Read either a base64 data URI or an asset member from the source archive."""

    if reference.startswith("data:"):
        header, separator, payload = reference.partition(",")
        if not separator or ";base64" not in header:
            raise SerializationError("Unsupported non-base64 image data URI")
        try:
            return base64.b64decode(payload)
        except (ValueError, binascii.Error) as error:
            raise SerializationError("Invalid base64 image data URI") from error
    if reference.startswith("/assets/"):
        member = reference.lstrip("/")
        names = {name.casefold(): name for name in archive.namelist()}
        actual = names.get(member.casefold())
        if actual is None:
            raise SerializationError(f"Referenced image is missing from archive: {reference}")
        return archive.read(actual)
    raise SerializationError(f"Unsupported image reference: {reference[:80]!r}")

"""Local extraction and aggressive PNG compression of images embedded in character PDFs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from cardenveil.domain import CharacterSheet
from cardenveil.importers.pdf.errors import CharacterExtractionError, MissingPDFDependencyError

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ImageCompressionConfig:
    """Size and palette limits used to reduce photographic PNG assets drastically."""

    portrait_max_pixels: int = 512
    other_max_pixels: int = 384
    palette_colors: int = 128

    def __post_init__(self) -> None:
        """Reject compression settings that would produce unusable image assets."""

        if self.portrait_max_pixels < 64 or self.other_max_pixels < 64:
            raise ValueError("Image dimensions must be at least 64 pixels")
        if not 2 <= self.palette_colors <= 256:
            raise ValueError("palette_colors must be between 2 and 256")


@dataclass(frozen=True, slots=True)
class ImageAssetExtractionResult:
    """Files written locally and public references injected into a character sheet."""

    files: tuple[Path, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _EmbeddedImage:
    """One embedded PDF image selected from its visual placement on a page."""

    xref: int
    x: float
    y: float


class PDFImageAssetExtractor:
    """Extract portrait, totem, and ordered capacity images from Cardenveil PDF templates."""

    def __init__(
        self,
        asset_root: str | Path,
        *,
        public_prefix: str = "/assets",
        compression: ImageCompressionConfig | None = None,
    ) -> None:
        """Configure the physical asset root and JSON-compatible public path prefix."""

        self.asset_root = Path(asset_root)
        self.public_prefix = "/" + public_prefix.strip("/")
        self.compression = compression or ImageCompressionConfig()

    def extract(
        self,
        pdf_path: str | Path,
        sheet: CharacterSheet,
    ) -> ImageAssetExtractionResult:
        """Write compressed assets and update only existing image fields on ``sheet``."""

        pymupdf, image_module = _load_image_dependencies()
        path = Path(pdf_path)
        character_directory = self.asset_root / sheet.id
        character_directory.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        warnings: list[str] = []

        try:
            document = pymupdf.open(path)
            if len(document) < 1:
                raise CharacterExtractionError(f"PDF contains no page: {path}")

            first_page = document[0]
            portrait = _find_portrait(first_page)
            totem = _find_totem(first_page)
            capacities = _find_capacity_images(document[1]) if len(document) > 1 else []

            if portrait is not None:
                output = character_directory / "portrait.png"
                _write_compressed_png(
                    document.extract_image(portrait.xref)["image"],
                    output,
                    self.compression.portrait_max_pixels,
                    self.compression.palette_colors,
                    image_module,
                )
                sheet.portrait = self._public_reference(sheet.id, output.name)
                written.append(output)
            else:
                warnings.append("No portrait image found on page 1")

            if totem is not None:
                output = character_directory / "totem.png"
                _write_compressed_png(
                    document.extract_image(totem.xref)["image"],
                    output,
                    self.compression.other_max_pixels,
                    self.compression.palette_colors,
                    image_module,
                )
                sheet.totem.image = self._public_reference(sheet.id, output.name)
                written.append(output)
            else:
                warnings.append("No totem image found on page 1")

            for index, embedded in enumerate(capacities, start=1):
                output = character_directory / f"capacity-{index}.png"
                _write_compressed_png(
                    document.extract_image(embedded.xref)["image"],
                    output,
                    self.compression.other_max_pixels,
                    self.compression.palette_colors,
                    image_module,
                )
                if index <= len(sheet.capacities):
                    sheet.capacities[index - 1].image = self._public_reference(
                        sheet.id, output.name
                    )
                written.append(output)
            if len(capacities) != len(sheet.capacities):
                warnings.append(
                    "Capacity image count differs from extracted capacity count: "
                    f"images={len(capacities)} capacities={len(sheet.capacities)}"
                )
        except CharacterExtractionError:
            raise
        except Exception as error:
            raise CharacterExtractionError(f"Cannot extract PDF image assets: {path}") from error
        finally:
            if "document" in locals():
                document.close()

        LOGGER.info(
            "PDF image assets extracted: file=%s assets=%d bytes=%d warnings=%d",
            path,
            len(written),
            sum(item.stat().st_size for item in written),
            len(warnings),
        )
        return ImageAssetExtractionResult(tuple(written), tuple(warnings))

    def _public_reference(self, character_id: str, filename: str) -> str:
        """Build the exact ``/assets/{character-id}/{filename}`` reference used by examples."""

        return f"{self.public_prefix}/{character_id}/{filename}"


def _load_image_dependencies() -> tuple[object, object]:
    """Load heavy image libraries lazily so ordinary core imports remain dependency-free."""

    try:
        import pymupdf
        from PIL import Image
    except ImportError as error:
        raise MissingPDFDependencyError(
            "Install cardenveil-core[pdf-assets] to extract PDF image assets"
        ) from error
    return pymupdf, Image


def _device_rgb_images(page: object) -> list[_EmbeddedImage]:
    """Return unique RGB images together with their first visible placement rectangle."""

    images: list[_EmbeddedImage] = []
    seen: set[int] = set()
    for metadata in page.get_images(full=True):  # type: ignore[attr-defined]
        xref = metadata[0]
        if xref in seen or metadata[5] != "DeviceRGB":
            continue
        rectangles = page.get_image_rects(xref)  # type: ignore[attr-defined]
        if not rectangles:
            continue
        seen.add(xref)
        rectangle = rectangles[0]
        images.append(_EmbeddedImage(xref, rectangle.x0, rectangle.y0))
    return images


def _find_portrait(page: object) -> _EmbeddedImage | None:
    """Find the large RGB image occupying the upper-left portrait rectangle."""

    width = page.rect.width  # type: ignore[attr-defined]
    height = page.rect.height  # type: ignore[attr-defined]
    candidates = [
        image
        for image in _device_rgb_images(page)
        if image.x < width * 0.35 and image.y < height * 0.25
    ]
    return min(candidates, key=lambda image: image.x + image.y) if candidates else None


def _find_totem(page: object) -> _EmbeddedImage | None:
    """Find the RGB thumbnail nearest the template's lower-left totem position."""

    width = page.rect.width  # type: ignore[attr-defined]
    height = page.rect.height  # type: ignore[attr-defined]
    candidates = [
        image
        for image in _device_rgb_images(page)
        if image.x < width * 0.12 and height * 0.5 < image.y < height * 0.72
    ]
    target_y = height * 0.63
    return min(candidates, key=lambda image: abs(image.y - target_y)) if candidates else None


def _find_capacity_images(page: object) -> list[_EmbeddedImage]:
    """Find capacity thumbnails in top-to-bottom order on the second page."""

    width = page.rect.width  # type: ignore[attr-defined]
    height = page.rect.height  # type: ignore[attr-defined]
    return sorted(
        (
            image
            for image in _device_rgb_images(page)
            if image.x < width * 0.12 and height * 0.05 < image.y < height * 0.72
        ),
        key=lambda image: image.y,
    )


def _write_compressed_png(
    source: bytes,
    destination: Path,
    max_pixels: int,
    palette_colors: int,
    image_module: object,
) -> None:
    """Resize and palette-quantize an image before writing an optimized PNG."""

    with image_module.open(BytesIO(source)) as image:  # type: ignore[attr-defined]
        image.thumbnail((max_pixels, max_pixels), image_module.Resampling.LANCZOS)  # type: ignore[attr-defined]
        rgb = image.convert("RGB")
        compressed = rgb.quantize(
            colors=palette_colors,
            method=image_module.Quantize.MEDIANCUT,  # type: ignore[attr-defined]
            dither=image_module.Dither.FLOYDSTEINBERG,  # type: ignore[attr-defined]
        )
        buffer = BytesIO()
        compressed.save(buffer, format="PNG", optimize=True, compress_level=9)
    destination.write_bytes(buffer.getvalue())


def compress_image_to_png(
    source: bytes,
    destination: str | Path,
    *,
    max_pixels: int = 384,
    palette_colors: int = 128,
) -> Path:
    """Compress arbitrary supported image bytes into the canonical optimized PNG format."""

    _, image_module = _load_image_dependencies()
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_compressed_png(source, output, max_pixels, palette_colors, image_module)
    return output

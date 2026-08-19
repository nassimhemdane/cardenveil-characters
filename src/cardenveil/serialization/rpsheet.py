"""Lossless serializer for the canonical Cardenveil ``rpsheet`` JSON format."""

from __future__ import annotations

import json
import types
import zipfile
from dataclasses import MISSING, fields, is_dataclass
from pathlib import Path
from typing import get_args, get_origin, get_type_hints

from cardenveil.domain.sheet import Character
from cardenveil.errors import SerializationError


def character_to_dict(character: Character) -> dict[str, object]:
    """Serialize a character into the exact object shape used by ``rpsheet`` files.

    Optional fields whose value is ``None`` are omitted because archive comparison identified them
    as absent keys, not JSON ``null`` values. No derived value is recalculated.
    """

    result = _to_json_value(character)
    if not isinstance(result, dict):  # pragma: no cover - protected by the public type
        raise SerializationError("A Character must serialize to a JSON object")
    return result


def character_from_dict(payload: dict[str, object]) -> Character:
    """Deserialize a ``rpsheet`` object and reject every unrecognized field."""

    try:
        character = _from_json_value(Character, payload, "character")
    except SerializationError:
        raise
    except (TypeError, ValueError) as error:
        raise SerializationError(f"Invalid rpsheet payload: {error}") from error
    if not isinstance(character, Character):  # pragma: no cover - decoder invariant
        raise SerializationError("Root object is not a Character")
    return character


def character_to_json(character: Character, *, indent: int | None = 2) -> str:
    """Serialize a character as readable UTF-8-compatible JSON text."""

    return json.dumps(character_to_dict(character), ensure_ascii=False, indent=indent)


def character_from_json(value: str) -> Character:
    """Deserialize JSON text using the strict canonical mapping."""

    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise SerializationError(f"Invalid JSON: {error.msg}") from error
    if not isinstance(payload, dict):
        raise SerializationError("A character document must be a JSON object")
    return character_from_dict(payload)


def character_from_archive(path: str | Path) -> Character:
    """Read the single ``*.rpsheet.json`` character in a reference ZIP archive."""

    archive_path = Path(path)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            candidates = [name for name in archive.namelist() if name.endswith(".rpsheet.json")]
            if len(candidates) != 1:
                raise SerializationError(
                    f"{archive_path.name} must contain exactly one .rpsheet.json file"
                )
            return character_from_json(archive.read(candidates[0]).decode("utf-8-sig"))
    except zipfile.BadZipFile as error:
        raise SerializationError(f"Invalid ZIP archive: {archive_path}") from error


def character_to_archive(
    character: Character,
    path: str | Path,
    *,
    asset_root: str | Path | None = None,
) -> Path:
    """Write canonical JSON and local character assets into an atomic ZIP archive."""

    archive_path = Path(path)
    if archive_path.suffix.lower() != ".zip":
        raise SerializationError(f"Character archive must use a .zip extension: {archive_path}")
    if not character.id or Path(character.id).name != character.id:
        raise SerializationError(f"Unsafe character ID for archive export: {character.id!r}")

    assets_directory = Path(asset_root) / character.id if asset_root is not None else None
    _validate_archive_asset_references(character, assets_directory)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = archive_path.with_suffix(archive_path.suffix + ".tmp")
    try:
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            archive.writestr(f"{character.id}.rpsheet.json", character_to_json(character) + "\n")
            if assets_directory is not None and assets_directory.is_dir():
                archive.writestr("assets/", b"")
                archive.writestr(f"assets/{character.id}/", b"")
                for asset in sorted(item for item in assets_directory.rglob("*") if item.is_file()):
                    relative = asset.relative_to(assets_directory)
                    archive.write(asset, (Path("assets") / character.id / relative).as_posix())
        temporary.replace(archive_path)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise SerializationError(f"Cannot write character archive: {archive_path}") from error
    return archive_path


def _validate_archive_asset_references(
    character: Character,
    assets_directory: Path | None,
) -> None:
    """Ensure every non-empty JSON image reference resolves inside its character asset folder."""

    references = [
        character.portrait,
        character.totem.image,
        *(capacity.image for capacity in character.capacities),
    ]
    expected_prefix = f"/assets/{character.id}/"
    for reference in (item for item in references if item):
        if not reference.startswith(expected_prefix):
            raise SerializationError(
                f"Image reference must start with {expected_prefix!r}: {reference!r}"
            )
        if assets_directory is None:
            raise SerializationError("asset_root is required when character images are referenced")
        filename = reference.removeprefix(expected_prefix)
        relative = Path(filename.replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts:
            raise SerializationError(f"Unsafe image reference: {reference!r}")
        local_path = assets_directory / relative
        if not local_path.is_file():
            raise SerializationError(f"Referenced image does not exist: {local_path}")


def _to_json_value(value: object) -> object:
    """Recursively convert exact-format dataclasses without adding absent optional keys."""

    if is_dataclass(value) and not isinstance(value, type):
        output: dict[str, object] = {}
        for item in fields(value):
            current = getattr(value, item.name)
            if current is None:
                continue
            json_name = item.metadata.get("json_name", item.name)
            output[json_name] = _to_json_value(current)
        return output
    if isinstance(value, list):
        return [_to_json_value(item) for item in value]
    return value


def _from_json_value(annotation: object, value: object, path: str) -> object:
    """Recursively instantiate the annotated dataclass tree."""

    origin = get_origin(annotation)
    if origin is list:
        if not isinstance(value, list):
            raise SerializationError(f"{path} must be an array")
        item_type = get_args(annotation)[0]
        return [_from_json_value(item_type, item, f"{path}[]") for item in value]
    if origin is types.UnionType:
        return _decode_union(get_args(annotation), value, path)
    if annotation is object:
        return value
    if isinstance(annotation, type) and is_dataclass(annotation):
        if not isinstance(value, dict):
            raise SerializationError(f"{path} must be an object")
        hints = get_type_hints(annotation)
        field_by_json = {
            item.metadata.get("json_name", item.name): item for item in fields(annotation)
        }
        unknown = set(value) - set(field_by_json)
        if unknown:
            raise SerializationError(f"Unknown field(s) at {path}: {sorted(unknown)}")
        kwargs: dict[str, object] = {}
        for json_name, item in field_by_json.items():
            if json_name in value:
                kwargs[item.name] = _from_json_value(
                    hints[item.name], value[json_name], f"{path}.{json_name}"
                )
            elif item.default is MISSING and item.default_factory is MISSING:
                raise SerializationError(f"Missing field: {path}.{json_name}")
        return annotation(**kwargs)
    if annotation in (str, int, float, bool, type(None)) and type(value) is not annotation:
        raise SerializationError(
            f"{path} must be {annotation.__name__}, got {type(value).__name__}"
        )
    return value


def _decode_union(choices: tuple[object, ...], value: object, path: str) -> object:
    """Select the union member matching the JSON scalar's exact Python type."""

    for choice in choices:
        if choice is type(None) and value is None:
            return None
        if choice in (str, int, float, bool) and type(value) is choice:
            return value
        if isinstance(choice, type) and is_dataclass(choice) and isinstance(value, dict):
            return _from_json_value(choice, value, path)
    allowed = ", ".join(getattr(choice, "__name__", str(choice)) for choice in choices)
    raise SerializationError(f"{path} must be one of: {allowed}")

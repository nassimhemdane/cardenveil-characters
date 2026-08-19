"""Simple JSON-file persistence for canonical Cardenveil characters."""

from __future__ import annotations

from pathlib import Path

from cardenveil.domain.sheet import Character
from cardenveil.errors import UnknownContentError, ValidationError
from cardenveil.serialization import character_from_json, character_to_json


class FileCharacterRepository:
    """Store one character per ``<id>.rpsheet.json`` file in a directory."""

    def __init__(self, directory: str | Path) -> None:
        """Create a repository rooted at ``directory`` without creating it yet."""

        self.directory = Path(directory)

    def save(self, character: Character) -> Path:
        """Atomically replace the JSON file for ``character`` and return its path."""

        path = self._path_for(character.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(character_to_json(character) + "\n", encoding="utf-8")
        temporary.replace(path)
        return path

    def get(self, character_id: str) -> Character:
        """Load one character or raise ``UnknownContentError`` when absent."""

        path = self._path_for(character_id)
        if not path.is_file():
            raise UnknownContentError(character_id)
        return character_from_json(path.read_text(encoding="utf-8"))

    def all(self) -> list[Character]:
        """Load every character file in deterministic filename order."""

        if not self.directory.exists():
            return []
        return [
            character_from_json(path.read_text(encoding="utf-8"))
            for path in sorted(self.directory.glob("*.rpsheet.json"))
        ]

    def _path_for(self, character_id: str) -> Path:
        """Resolve a safe filename for a persistent character ID."""

        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        if not character_id or any(character not in allowed for character in character_id):
            raise ValidationError(f"Unsafe character ID: {character_id!r}")
        return self.directory / f"{character_id}.rpsheet.json"


class CardenveilCore:
    """Application-facing facade around the configured persistence layer."""

    def __init__(self, characters: FileCharacterRepository) -> None:
        """Bind the core facade to a character repository."""

        self.characters = characters

    def load_character(self, character_id: str) -> Character:
        """Load a character by stable ID."""

        return self.characters.get(character_id)

    def save_character(self, character: Character) -> Path:
        """Persist a complete character in the default JSON format."""

        return self.characters.save(character)

    def load_all_characters(self) -> list[Character]:
        """Load all persisted characters in deterministic order."""

        return self.characters.all()

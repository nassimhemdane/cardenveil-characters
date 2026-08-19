"""Stable technical naming helpers shared by import and migration workflows."""

from __future__ import annotations

import re
import unicodedata


def slugify_character_id(value: str) -> str:
    """Convert a display name into the lowercase ASCII ID used by character archives."""

    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")

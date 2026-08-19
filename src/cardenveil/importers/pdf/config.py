"""Centralized Gemini configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from cardenveil.importers.pdf.errors import LLMAuthenticationError, MissingPDFDependencyError

DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"
DEFAULT_MEDIA_RESOLUTION = "MEDIA_RESOLUTION_HIGH"
SUPPORTED_MEDIA_RESOLUTIONS = {
    "MEDIA_RESOLUTION_LOW",
    "MEDIA_RESOLUTION_MEDIUM",
    "MEDIA_RESOLUTION_HIGH",
}


@dataclass(frozen=True, slots=True)
class GeminiConfig:
    """Credentials and retry policy required by the Gemini provider."""

    api_key: str
    model: str = DEFAULT_GEMINI_MODEL
    media_resolution: str = DEFAULT_MEDIA_RESOLUTION
    max_attempts: int = 3
    initial_backoff_seconds: float = 1.0
    request_timeout_seconds: int = 180

    def __post_init__(self) -> None:
        """Validate configuration without ever exposing the secret value."""

        if not self.api_key.strip():
            raise LLMAuthenticationError("GEMINI_API_KEY is missing or empty")
        if not self.model.strip():
            raise ValueError("GEMINI_MODEL must not be empty")
        if self.media_resolution not in SUPPORTED_MEDIA_RESOLUTIONS:
            raise ValueError(
                "media_resolution must be MEDIA_RESOLUTION_LOW, "
                "MEDIA_RESOLUTION_MEDIUM, or MEDIA_RESOLUTION_HIGH"
            )
        if not 1 <= self.max_attempts <= 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if self.initial_backoff_seconds < 0:
            raise ValueError("initial_backoff_seconds cannot be negative")
        if not 10 <= self.request_timeout_seconds <= 600:
            raise ValueError("request_timeout_seconds must be between 10 and 600")

    @classmethod
    def from_env(cls, env_file: str | Path | None = ".env") -> GeminiConfig:
        """Load an optional dotenv file, then read centralized environment variables."""

        if env_file is not None:
            try:
                from dotenv import load_dotenv
            except ImportError as error:
                raise MissingPDFDependencyError(
                    "Install cardenveil-core[pdf-gemini] to load Gemini configuration"
                ) from error
            load_dotenv(Path(env_file), override=False)
        return cls(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model=os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
            media_resolution=os.getenv("GEMINI_MEDIA_RESOLUTION", DEFAULT_MEDIA_RESOLUTION),
        )

"""Optional Gemini implementation of the character-document extractor protocol."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from cardenveil.importers.pdf.config import GeminiConfig
from cardenveil.importers.pdf.errors import (
    InvalidExtractionError,
    LLMAuthenticationError,
    LLMProviderError,
    LLMQuotaError,
    MissingPDFDependencyError,
)
from cardenveil.importers.pdf.models import (
    ExtractedCatalogMetadata,
    ExtractedCharacter,
    ExtractedTotemAndCapacities,
)

LOGGER = logging.getLogger(__name__)
ExtractionModel = TypeVar("ExtractionModel", bound=BaseModel)


class GeminiCharacterDocumentExtractor:
    """Send complete PDFs to Gemini and validate its Structured Output with Pydantic."""

    def __init__(
        self,
        config: GeminiConfig,
        *,
        client: object | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        """Create the provider; an injected client/sleeper keeps unit tests offline."""

        self.config = config
        self._client = client or self._create_client(
            config.api_key, config.request_timeout_seconds
        )
        self._sleeper = sleeper

    @classmethod
    def from_env(cls, env_file: str | Path | None = ".env") -> GeminiCharacterDocumentExtractor:
        """Create the provider from centralized environment configuration."""

        return cls(GeminiConfig.from_env(env_file))

    def extract(self, pdf_path: Path) -> ExtractedCharacter:
        """Upload a PDF natively, request JSON Schema output, and validate the response."""

        prompt = (
            files("cardenveil.importers.pdf.prompts")
            .joinpath("extract_character.md")
            .read_text(encoding="utf-8")
        )
        return self._extract_structured(pdf_path, prompt, ExtractedCharacter)

    def extract_totem_and_capacities(self, pdf_path: Path) -> ExtractedTotemAndCapacities:
        """Run a smaller repair request focused only on the two commonly omitted sections."""

        prompt = (
            files("cardenveil.importers.pdf.prompts")
            .joinpath("extract_totem_capacities.md")
            .read_text(encoding="utf-8")
        )
        return self._extract_structured(pdf_path, prompt, ExtractedTotemAndCapacities)

    def extract_catalog_metadata(self, pdf_path: Path) -> ExtractedCatalogMetadata:
        """Derive concise catalogue fields from a PDF without inventing missing information."""

        prompt = self._catalog_prompt()
        return self._extract_structured(pdf_path, prompt, ExtractedCatalogMetadata)

    def extract_catalog_metadata_from_json(self, character_json: str) -> ExtractedCatalogMetadata:
        """Derive catalogue fields from canonical JSON when no original PDF is available."""

        prompt = f"{self._catalog_prompt()}\n\nFiche JSON canonique :\n{character_json}"
        response = self._retry(
            lambda: self._client.models.generate_content(  # type: ignore[attr-defined]
                model=self.config.model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": ExtractedCatalogMetadata.model_json_schema(),
                    "temperature": 0,
                },
            )
        )
        response_text = getattr(response, "text", None)
        if not isinstance(response_text, str) or not response_text.strip():
            raise InvalidExtractionError("Gemini returned no catalogue metadata")
        try:
            return ExtractedCatalogMetadata.model_validate_json(response_text)
        except PydanticValidationError as error:
            raise InvalidExtractionError("Gemini catalogue metadata failed validation") from error

    @staticmethod
    def _catalog_prompt() -> str:
        """Load the single anti-invention prompt shared by PDF and JSON metadata extraction."""

        return (
            files("cardenveil.importers.pdf.prompts")
            .joinpath("extract_catalog_metadata.md")
            .read_text(encoding="utf-8")
        )

    def _extract_structured(
        self,
        pdf_path: Path,
        prompt: str,
        response_model: type[ExtractionModel],
    ) -> ExtractionModel:
        """Upload once and validate one provider response against the requested Pydantic model."""

        started = time.monotonic()
        LOGGER.debug(
            "Calling Gemini: file=%s model=%s bytes=%d",
            pdf_path,
            self.config.model,
            pdf_path.stat().st_size,
        )
        uploaded = None
        try:
            uploaded = self._retry(lambda: self._client.files.upload(file=pdf_path))  # type: ignore[attr-defined]
            document_part = self._document_part(uploaded)
            response = self._retry(
                lambda: self._client.models.generate_content(  # type: ignore[attr-defined]
                    model=self.config.model,
                    contents=[document_part, prompt],
                    config={
                        "response_mime_type": "application/json",
                        "response_json_schema": response_model.model_json_schema(),
                        "temperature": 0,
                    },
                )
            )
            response_text = getattr(response, "text", None)
            if not isinstance(response_text, str) or not response_text.strip():
                raise InvalidExtractionError("Gemini returned no structured response text")
            try:
                extracted = response_model.model_validate_json(response_text)
            except PydanticValidationError as error:
                raise InvalidExtractionError(
                    "Gemini output failed extraction validation"
                ) from error
            LOGGER.debug(
                "Gemini extraction validated: file=%s model=%s duration_seconds=%.3f warnings=%d",
                pdf_path,
                self.config.model,
                time.monotonic() - started,
                len(getattr(extracted, "warnings", [])),
            )
            return extracted
        finally:
            if uploaded is not None:
                name = getattr(uploaded, "name", None)
                if name:
                    try:
                        self._client.files.delete(name=name)  # type: ignore[attr-defined]
                    except Exception:
                        LOGGER.debug("Could not delete temporary Gemini file: %s", name)

    def _document_part(self, uploaded: object) -> object:
        """Reference an uploaded PDF with explicit resolution for tiny visual markers."""

        uri = getattr(uploaded, "uri", None)
        if not isinstance(uri, str) or not uri:
            raise LLMProviderError("Gemini uploaded file has no usable URI")
        mime_type = getattr(uploaded, "mime_type", None) or "application/pdf"
        try:
            from google.genai import types
        except ImportError as error:  # pragma: no cover - guarded during client creation
            raise MissingPDFDependencyError(
                "Install cardenveil-core[pdf-gemini] to use Gemini PDF extraction"
            ) from error
        return types.Part.from_uri(
            file_uri=uri,
            mime_type=mime_type,
            media_resolution=self.config.media_resolution,
        )

    def _retry(self, operation: Callable[[], object]) -> object:
        """Retry only transient provider failures with bounded exponential backoff."""

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                return operation()
            except Exception as error:
                translated, transient = _translate_provider_error(error)
                if not transient or attempt == self.config.max_attempts:
                    raise translated from error
                delay = self.config.initial_backoff_seconds * (2 ** (attempt - 1))
                LOGGER.warning(
                    "Transient Gemini failure; retrying: model=%s attempt=%d/%d delay=%.1f",
                    self.config.model,
                    attempt,
                    self.config.max_attempts,
                    delay,
                )
                self._sleeper(delay)
        raise AssertionError("Retry loop must return or raise")  # pragma: no cover

    @staticmethod
    def _create_client(api_key: str, timeout_seconds: int) -> object:
        """Lazily import the optional SDK so the core works without Gemini installed."""

        try:
            from google import genai
            from google.genai import types
        except ImportError as error:
            raise MissingPDFDependencyError(
                "Install cardenveil-core[pdf-gemini] to use Gemini PDF extraction"
            ) from error
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_seconds * 1000),
        )


def _translate_provider_error(error: Exception) -> tuple[LLMProviderError, bool]:
    """Translate SDK/network failures without exposing provider exceptions to callers."""

    status = getattr(error, "status_code", None) or getattr(error, "code", None)
    message = str(error).lower()
    if status in (401, 403) or "api key" in message or "unauth" in message:
        return LLMAuthenticationError("Gemini authentication failed"), False
    if status == 429 or "resource_exhausted" in message or "rate limit" in message:
        return LLMQuotaError("Gemini quota or rate limit exceeded"), True
    transient = status in (408, 500, 502, 503, 504) or any(
        token in message for token in ("timeout", "temporar", "connection", "unavailable")
    )
    return LLMProviderError("Gemini provider request failed"), transient

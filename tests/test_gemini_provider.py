"""Offline contract tests for Gemini Structured Output and retry behavior."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace

import pytest

from cardenveil.importers.pdf.config import GeminiConfig
from cardenveil.importers.pdf.errors import InvalidExtractionError, LLMAuthenticationError
from cardenveil.importers.pdf.gemini import GeminiCharacterDocumentExtractor


class StatusError(Exception):
    """Test exception exposing the status shape used by provider translation."""

    def __init__(self, status_code: int) -> None:
        """Store an HTTP-like status code."""

        super().__init__(f"status {status_code}")
        self.status_code = status_code


class FakeFilesAPI:
    """In-memory stand-in for Gemini's Files API."""

    def __init__(self) -> None:
        """Initialize upload/delete call tracking."""

        self.upload_calls = 0
        self.deleted: list[str] = []

    def upload(self, *, file: Path) -> object:
        """Return a fake uploaded file reference."""

        self.upload_calls += 1
        return SimpleNamespace(
            name="files/test",
            uri="https://generativelanguage.googleapis.com/files/test",
            mime_type="application/pdf",
            source=file,
        )

    def delete(self, *, name: str) -> None:
        """Record remote cleanup."""

        self.deleted.append(name)


class FakeModelsAPI:
    """Return structured JSON after an optional number of transient failures."""

    def __init__(self, failures: list[Exception] | None = None, text: str = "{}") -> None:
        """Configure sequential failures and final response text."""

        self.failures = list(failures or [])
        self.text = text
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs: object) -> object:
        """Capture Structured Output configuration and return a response."""

        self.calls.append(kwargs)
        if self.failures:
            raise self.failures.pop(0)
        return SimpleNamespace(text=self.text)


def _client(models: FakeModelsAPI) -> object:
    """Build an object matching the small SDK surface used by the provider."""

    return SimpleNamespace(files=FakeFilesAPI(), models=models)


def _pdf(tmp_path: Path) -> Path:
    """Create a minimal provider input PDF."""

    path = tmp_path / "character.pdf"
    path.write_bytes(b"%PDF-1.7\n%%EOF")
    return path


def test_gemini_uses_schema_retries_transient_errors_and_cleans_up(tmp_path: Path) -> None:
    """Verify bounded retry, Pydantic schema configuration, validation, and remote cleanup."""

    models = FakeModelsAPI([StatusError(503)], '{"identity":{"nom":"Mimyr"}}')
    client = _client(models)
    delays: list[float] = []
    extractor = GeminiCharacterDocumentExtractor(
        GeminiConfig("secret", max_attempts=3, initial_backoff_seconds=0.25),
        client=client,
        sleeper=delays.append,
    )
    result = extractor.extract(_pdf(tmp_path))

    assert result.identity.nom == "Mimyr"
    assert delays == [0.25]
    assert len(models.calls) == 2
    config = models.calls[-1]["config"]
    document_part = models.calls[-1]["contents"][0]  # type: ignore[index]
    assert config["response_mime_type"] == "application/json"  # type: ignore[index]
    assert "properties" in config["response_json_schema"]  # type: ignore[index]
    assert document_part.media_resolution.level == "MEDIA_RESOLUTION_HIGH"
    assert client.files.deleted == ["files/test"]  # type: ignore[attr-defined]


def test_authentication_error_is_not_retried(tmp_path: Path) -> None:
    """Authentication failures are translated immediately and never retried."""

    models = FakeModelsAPI([StatusError(401)])
    with pytest.raises(LLMAuthenticationError):
        GeminiCharacterDocumentExtractor(
            GeminiConfig("secret"), client=_client(models), sleeper=lambda _: None
        ).extract(_pdf(tmp_path))
    assert len(models.calls) == 1


def test_invalid_structured_response_is_rejected(tmp_path: Path) -> None:
    """Syntactically valid but schema-invalid output raises a stable import error."""

    models = FakeModelsAPI(text='{"stats":{"force":99}}')
    with pytest.raises(InvalidExtractionError):
        GeminiCharacterDocumentExtractor(GeminiConfig("secret"), client=_client(models)).extract(
            _pdf(tmp_path)
        )


def test_config_loads_key_and_model_from_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Central configuration reads a dotenv file without hard-coding provider settings."""

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GEMINI_API_KEY=test-key\nGEMINI_MODEL=gemini-test-model\n",
        encoding="utf-8",
    )

    config = GeminiConfig.from_env(env_file)

    assert config.api_key == "test-key"
    assert config.model == "gemini-test-model"
    assert config.media_resolution == "MEDIA_RESOLUTION_HIGH"


def test_config_rejects_a_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing secret fails before a client or network request can be created."""

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LLMAuthenticationError, match="missing or empty"):
        GeminiConfig.from_env(env_file=None)


def test_extraction_prompt_defines_optional_skills_and_narrative_rules() -> None:
    """Protect the best-effort skill policy and narrative layout conventions."""

    prompt = (
        files("cardenveil.importers.pdf.prompts")
        .joinpath("extract_character.md")
        .read_text(encoding="utf-8")
    )
    assert "La liste `skills` peut donc être vide" in prompt
    assert "`Nature` doit être transcrit sous l'ID canonique `survie`" in prompt
    assert "titres `Background`" in prompt
    assert "bord inférieur" in prompt
    assert "rectangles `Liens` et" in prompt

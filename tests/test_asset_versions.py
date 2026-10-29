"""Prevent stale browser images after a character archive is updated."""

import importlib
from pathlib import Path


def test_image_urls_follow_content(monkeypatch, tmp_path):
    """Unchanged bytes keep their URL; replacement bytes get a new existing file."""
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "web"))
    build = importlib.import_module("build")
    monkeypatch.setattr(build, "PUBLIC", tmp_path)
    first = build._write_versioned_asset("assets/example/portrait.png", b"first")
    assert build._write_versioned_asset("assets/example/portrait.png", b"first") == first
    second = build._write_versioned_asset("assets/example/portrait.png", b"replacement")
    assert first != second
    assert (tmp_path / first.lstrip("/")).read_bytes() == b"first"
    assert (tmp_path / second.lstrip("/")).read_bytes() == b"replacement"

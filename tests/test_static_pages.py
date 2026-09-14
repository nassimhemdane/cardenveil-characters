"""Verify that character pages expose real sheet content without executing JavaScript."""

import functools
import importlib
import json
import re
import shutil
import subprocess
import threading
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


class VisibleText(HTMLParser):
    """Collect visible text, excluding embedded scripts and their duplicate JSON data."""

    def __init__(self):
        """Prepare a minimal HTML text extractor for assertions."""
        super().__init__()
        self.hidden = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        """Hide scripts instead of counting their payload as page content."""
        if tag == "script":
            self.hidden = True

    def handle_endtag(self, tag):
        """Resume collecting visible text after a script."""
        if tag == "script":
            self.hidden = False

    def handle_data(self, data):
        """Collect text that a script-free HTML reader can access."""
        if not self.hidden:
            self.parts.append(data)


def visible(source):
    """Normalize text-node whitespace for comparison across nested markup."""
    parser = VisibleText()
    parser.feed(source)
    return " ".join(" ".join(parser.parts).split())


@pytest.fixture
def generator(monkeypatch):
    """Import the standalone build modules in the same environment as their CLI."""
    monkeypatch.syspath_prepend(str(ROOT / "web"))
    return importlib.import_module("static_pages")


def test_all_character_pages_contain_visible_content(generator, monkeypatch, tmp_path):
    """Build all archives in isolation and verify their HTML plus hydration payloads."""
    build = importlib.import_module("build")
    for name, directory in {
        "PUBLIC": tmp_path,
        "DATA": tmp_path / "data",
        "ASSETS": tmp_path / "assets",
        "DOWNLOADS": tmp_path / "downloads",
    }.items():
        monkeypatch.setattr(build, name, directory)
    build.build()
    characters = json.loads((tmp_path / "data/characters.json").read_text(encoding="utf-8"))
    index = (tmp_path / "personnages/index.html").read_text(encoding="utf-8")
    assert len(characters) == len(list((ROOT / "Final").glob("*.zip")))
    for c in characters:
        page = (tmp_path / c["pageUrl"].strip("/") / "index.html").read_text("utf-8")
        text = visible(page)
        assert visible(generator.rich(c["identity"]["nom"])) in text
        assert c["pageUrl"] in index
        payload = re.search(
            r'<script id="character-data" type="application/json">(.*?)</script>', page, re.S
        )
        assert payload and json.loads(payload[1]) == c
        for obj in [c["totem"], *c["capacities"]]:
            assert visible(generator.rich(obj["description"])) in text
            if obj.get("image"):
                assert f'src="{obj["image"]}"' in page
        assert c["printUrl"] in page


def test_static_text_safety_and_values(generator):
    """Keep emphasis, paragraphs, zeroes and false while rejecting active HTML."""
    result = generator.value_html(
        {
            "cost": 0,
            "trained": False,
            "description": '<p onclick="evil()"><strong>Texte</strong><br>Suite</p>'
            '<script>alert(1)</script><img src=x onerror="evil()">',
        }
    )
    assert "<strong>Texte</strong><br>Suite</p>" in result
    assert "<dd>0</dd>" in result and "<dd>Non</dd>" in result
    assert all(word not in result for word in ["onclick", "onerror", "<script", "alert"])


def test_reject_path_traversal(generator):
    """Never let a character identifier write outside its generated directory."""
    for identifier in ["../outside", "/outside", "a/b", "..", ""]:
        with pytest.raises(ValueError):
            generator.character_url(identifier)


def test_static_routes_in_browser(tmp_path):
    """Check direct hydration, legacy links and real catalogue anchors in Chromium."""
    browser = next(
        (
            str(p)
            for p in [
                Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
            ]
            if p.is_file()
        ),
        shutil.which("chromium"),
    )
    public = ROOT / "web/public"
    if not browser or not (public / "personnages/zotaru/index.html").is_file():
        pytest.skip("Build the catalogue and install Chromium for route checks")
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(SimpleHTTPRequestHandler, directory=str(public))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        for index, route in enumerate(
            [
                "/personnages/zotaru/",
                "/?character=zotaru&tab=narrative",
                "/",
            ]
        ):
            result = subprocess.run(
                [
                    browser,
                    "--headless",
                    "--disable-gpu",
                    "--no-first-run",
                    f"--user-data-dir={tmp_path / str(index)}",
                    "--virtual-time-budget=10000",
                    "--dump-dom",
                    f"http://127.0.0.1:{server.server_port}{route}",
                ],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
            assert result.returncode == 0, result.stderr[-1000:]
            if route == "/":
                assert 'class="character-link" href="/personnages/zotaru/"' in result.stdout
            else:
                assert 'class="hero"' in result.stdout
                assert 'data-tab="abilities"' in result.stdout
                assert "Zotaru" in result.stdout
                if "narrative" in route:
                    assert 'data-tab="narrative" class="active"' in result.stdout
    finally:
        server.shutdown()
        server.server_close()

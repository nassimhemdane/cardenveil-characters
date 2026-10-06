"""Regression coverage for the source-based, script-independent rules library."""

import importlib
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    """Collect local links and anchors without a browser or third-party parser."""

    def __init__(self):
        """Initialize per-document link and ID collections."""
        super().__init__()
        self.links = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        """Record targets for duplicate-anchor and broken-link checks."""
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])


def test_rules_build_and_links(tmp_path, monkeypatch):
    """Every published chapter and search result resolves to existing, unique anchors."""
    monkeypatch.syspath_prepend(str(ROOT / "web"))
    module = importlib.import_module("rules_pages")
    module.build_rules(ROOT, tmp_path)
    pages = list((tmp_path / "regles").rglob("index.html"))
    assert len(pages) == len(module.CHAPTERS) + 1 == 15
    for path in pages:
        source = path.read_text("utf-8")
        parser = Links()
        parser.feed(source)
        assert len(parser.ids) == len(set(parser.ids))
        assert 'aria-label="Chapitres"' in source
        for link in parser.links:
            if link.startswith("#"):
                assert link[1:] in parser.ids, (path, link)
            elif link.startswith("/regles/"):
                route, _, anchor = link.partition("#")
                target = tmp_path / route.strip("/") / "index.html"
                assert target.is_file(), link
                if anchor:
                    assert f'id="{anchor}"' in target.read_text("utf-8"), link
    index = json.loads((tmp_path / "regles/search.json").read_text("utf-8"))
    assert len(index) > 99
    for entry in index:
        url, _, anchor = entry["url"].partition("#")
        page = (tmp_path / url.strip("/") / "index.html").read_text("utf-8")
        if anchor:
            assert f'id="{anchor}"' in page
        assert entry["text"]
    weapons = (tmp_path / "regles/armes/index.html").read_text("utf-8")
    assert "<thead>" in weapons and "<tbody>" in weapons and "Bouclier" in weapons
    assert "unresolved" in (tmp_path / "regles/personnage/index.html").read_text("utf-8")
    base = (tmp_path / "regles/systeme-de-base/index.html").read_text("utf-8")
    assert 'class="rule-heading"' in base and 'class="source-cite"' in base
    assert 'id="source-page-1"' in base
    assert "character.stats.modifier</h" not in (
        tmp_path / "regles/personnage/index.html"
    ).read_text("utf-8")


def test_source_text_is_not_rewritten(tmp_path, monkeypatch):
    """All extracted PDF blocks survive HTML escaping and no engineering docs are published."""
    from html import escape

    monkeypatch.syspath_prepend(str(ROOT / "web"))
    module = importlib.import_module("rules_pages")
    module.build_rules(ROOT, tmp_path)
    for source in (ROOT / "docs/rules/sources").glob("*.json"):
        doc = json.loads(source.read_text("utf-8"))
        page = (tmp_path / "regles" / source.stem / "index.html").read_text("utf-8")
        for item in doc["pages"]:
            for block in item["blocks"]:
                assert escape(block) in page
    assert not (tmp_path / "regles/pdf-import").exists()
    html, _ = module.markdown("# Title\n\n## Heading\n\n<script>alert(1)</script>\n")
    assert "<script>" not in html and "&lt;script&gt;" in html

"""Regression coverage for the source-based, script-independent rules library."""

import importlib
import json
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_emphasis_preserves_rule_text_and_markdown_safety():
    """Reading emphasis must preserve wording and keep markup safely escaped."""
    module = importlib.import_module("web.rules_pages")
    text = "L’armure absorbe au maximum 50 % : <script>alert(1)</script>."
    rendered = module.emphasize(text)
    assert "<strong>50 %</strong>" in rendered
    assert "<script>" not in rendered
    assert unescape(rendered.replace("<strong>", "").replace("</strong>", "")) == text
    rendered = module.inline("**50 %** et `1d8`, [parade](/regles/combat/)")
    assert rendered == (
        '<strong>50 %</strong> et <code>1d8</code>, '
        '<a href="/regles/combat/">parade</a>'
    )


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
    """Every current chapter, race image, legacy redirect and search anchor resolves."""
    monkeypatch.syspath_prepend(str(ROOT / "web"))
    module = importlib.import_module("rules_pages")
    module.build_rules(ROOT, tmp_path)
    assert len(module.CHAPTERS) == 8
    assert module.CHAPTERS[0][1] == "reference-rapide"
    active = {chapter[1] for chapter in module.CHAPTERS}
    assert active == {"reference-rapide", "systeme-de-base", "creation", "races",
                      "progression", "combat", "capacites", "narration"}
    pages = list((tmp_path / "regles").rglob("index.html"))
    assert len(pages) == 17  # Eight chapters, home, eight compatibility redirects.
    for path in pages:
        source = path.read_text("utf-8")
        parser = Links()
        parser.feed(source)
        assert len(parser.ids) == len(set(parser.ids)), path
        if 'http-equiv="refresh"' not in source:
            assert 'aria-label="Chapitres"' in source
            assert "Arbitrages du MJ" not in source
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
    assert len(index) > 100
    assert {entry["url"].split("/")[2] for entry in index} == active
    for entry in index:
        url, _, anchor = entry["url"].partition("#")
        page = (tmp_path / url.strip("/") / "index.html").read_text("utf-8")
        if anchor:
            assert f'id="{anchor}"' in page
        assert entry["text"] and entry["format"] == "markdown"
        assert entry["source"].endswith(".md") and entry["source"] != "Partie MJ.md"
        assert "![[" not in entry["text"] and "page undefined" not in entry["text"]
    races = (tmp_path / "regles/races/index.html").read_text("utf-8")
    assert races.count('class="race-card"') == 26
    assert races.count('class="rule-illustration"') == 25
    assert "Illustration non disponible" in races
    import re
    for url in re.findall(r'src="(/assets/rules/[^"]+)"', races):
        assert (tmp_path / url.lstrip("/")).is_file()
    base = (tmp_path / "regles/systeme-de-base/index.html").read_text("utf-8")
    assert 'class="rule-heading"' in base
    assert 'class="source-cite"' not in base and 'id="source-document"' not in base
    for path in pages:
        page = path.read_text("utf-8")
        assert 'id="reading-size"' not in page and 'id="reading-theme"' not in page
        assert 'class="document-source"' not in page and 'Consulter le Markdown source' not in page
    combat = (tmp_path / "regles/combat/index.html").read_text("utf-8")
    assert 'class="chapter-navigation" data-chapter="combat" open' in combat
    assert 'class="chapter-sections"' in combat and 'class="chapter-subsections"' in combat
    assert 'href="/regles/combat/#actions-disponibles-en-combat">Actions en combat</a>' in combat
    assert 'href="/regles/combat/#actions-principales"' in combat
    assert 'href="/regles/combat/#actions-bonus"' in combat
    assert 'href="/regles/combat/#reactions"' in combat
    for path in pages:
        page = path.read_text("utf-8")
        assert 'class="docs-toc"' not in page and 'Sur cette page' not in page
        assert 'class="mobile-toc"' not in page
        if 'http-equiv="refresh"' not in page:
            assert '/rules.css?v=' in page
            assert page.count('class="chapter-heading"') == len(module.CHAPTERS)
            assert page.count('class="chapter-navigation"') == len(module.CHAPTERS)
            for chapter in module.CHAPTERS:
                assert f'data-chapter="{chapter[1]}"' in page
    home = (tmp_path / "regles/index.html").read_text("utf-8")
    assert home.index('class="quick-reference-feature"') < home.index('class="docs-search"')
    assert 'class="quick-reference-home"' in home
    legacy = (tmp_path / "regles/arbitrages/index.html").read_text("utf-8")
    assert 'http-equiv="refresh"' in legacy and "Arbitrages du MJ" not in legacy


def test_source_text_is_not_rewritten(tmp_path, monkeypatch):
    """Exact snapshots stay in the repo, not the public UI; the MJ file is never copied."""
    import hashlib

    monkeypatch.syspath_prepend(str(ROOT / "web"))
    module = importlib.import_module("rules_pages")
    module.build_rules(ROOT, tmp_path)
    snapshot = ROOT / "docs/rules/fragmented"
    manifest = json.loads((snapshot / "manifest.json").read_text("utf-8"))
    assert len(manifest["documents"]) == 7
    assert len(list(snapshot.glob("*.md"))) == 7
    assert not (snapshot / "Partie MJ.md").exists()
    for key, source in manifest["documents"].items():
        raw = (snapshot / source["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]
        page = (tmp_path / "regles" / key / "index.html").read_text("utf-8")
        assert 'class="original-page"' not in page
        assert 'class="document-source"' not in page
        assert 'class="source-cite"' not in page
    assert not (tmp_path / "regles/pdf-import").exists()
    html, _ = module.markdown("# Title\n\n## Heading\n\n<script>alert(1)</script>\n")
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_current_markdown_renderer_nested_lists_and_safety(monkeypatch):
    """Support actual Obsidian constructs without executing HTML or external image URLs."""
    monkeypatch.syspath_prepend(str(ROOT / "web"))
    renderer = importlib.import_module("fragmented_rules").Markdown({}, {})
    source = ("# Title\n\n## Heading\n\n- Parent\n    - Child **important**\n\n"
              "> Une citation.\n\n1. Premier\n2. Second\n\n"
              "| A | B |\n| --- | --- |\n| 0 | 5 |\n\n"
              "<script>alert(1)</script>\n\n[unsafe](javascript:alert(1))\n\n"
              "![[missing.png|400]]\n\n### Heading\n")
    html = renderer.render(source)
    assert "<strong>important</strong>" in html
    assert html.count("<ul>") == 2 and "<ol" in html
    assert "<blockquote" in html and "<thead>" in html and "<tbody>" in html
    assert "<script>" not in html and 'href="javascript:' not in html
    assert "Illustration non disponible" in html
    assert len({anchor for anchor, _ in renderer.toc}) == len(renderer.toc)

"""Check dashboard mathematics, complete catalogue coverage and responsive rendering."""

import importlib
import json
import math
from pathlib import Path

import pytest

from test_gemini_pages import run_harness

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def dashboard(monkeypatch):
    """Import the standalone dashboard generator with its build-time dependencies."""
    monkeypatch.syspath_prepend(str(ROOT / "web"))
    return importlib.import_module("statistics_pages")


def test_population_statistics_preserve_zeros_and_reject_invalid_values(dashboard):
    """Use a known distribution so sample/population and missing/zero mistakes fail."""
    result = dashboard.summary([0, 2, "4", "6,0", None, "", "2 + 3", True, float("inf")])
    assert result["n"] == 4
    assert result["missing"] == 5
    assert result["mean"] == result["median"] == 3
    assert result["stddev"] == pytest.approx(math.sqrt(5))
    assert (result["min"], result["max"], result["zeros"]) == (0, 6, 1)
    assert dashboard.summary([])["mean"] is None
    assert dashboard.summary([4])["stddev"] == 0


@pytest.mark.parametrize("usage,expected", [
    ("Bonus Action / Réaction / Concentration", ["Action bonus", "Réaction"]),
    ("Action Bonus action Concentration", ["Action", "Action bonus"]),
    ("Action/réaction /bonus action Concentration", ["Action", "Action bonus", "Réaction"]),
    ("Réaction + Action", ["Action", "Réaction"]),
    ("Action bonus", ["Action bonus"]),
    ("Actio | Concentration", []),
    ("", []),
])
def test_usage_modes_do_not_double_count_bonus_actions(dashboard, usage, expected):
    """Distinguish multimode abilities, accents, unknown labels and bonus-only usages."""
    assert dashboard.usage_modes(usage) == expected


def test_aggregation_and_safe_static_rendering(dashboard, tmp_path):
    """Exercise every color, partial data, malicious labels and multi-action abilities."""
    characters = [
        {"identity": {"race": "<p>Nain</p>"}, "stats": {"force": 6, "esprit": 18},
         "capacities": [{"cost": {"color": color, "base": 10 + i, "total": i},
                         "usage": "Bonus action / Réaction"} for i, color in enumerate(dashboard.COLORS)]},
        {"identity": {"race": "nain"}, "stats": {"force": 14},
         "capacities": [{"cost": {"color": "unknown", "total": -1}, "usage": '<img src=x onerror="alert(1)">'},
                        {"cost": {"color": "heart", "total": "?"}}]},
        {"identity": {}, "stats": {}},
    ]
    data = dashboard.write_statistics(tmp_path, characters)
    assert data["races"] == {"Nain": 2, "Non renseignée": 1}
    assert data["capacities"] == 6
    assert data["costs"]["all"]["total"]["mean"] == 1.5
    assert data["costs"]["all"]["total"]["missing"] == 2
    assert data["costs"]["heart"]["total"]["zeros"] == 1
    assert data["modes"] == {"Action": 0, "Action bonus": 4, "Réaction": 4}
    assert sum(data["combinations"].values()) == 6
    assert data["stats"]["force"]["stddev"] == 4
    assert data["stats"]["force"]["missing"] == 1
    html = (tmp_path / "statistiques/index.html").read_text(encoding="utf-8")
    assert "<img" not in html and "<script" not in html
    assert "Écart type" in html and 'href="/statistiques/"' in html
    assert json.loads((tmp_path / "statistiques/donnees.json").read_text(encoding="utf-8")) == json.loads(json.dumps(data))
    empty = dashboard.write_statistics(tmp_path / "empty", [])
    assert empty["characters"] == empty["capacities"] == 0


def test_dashboard_matches_every_canonical_archive(dashboard, monkeypatch, tmp_path):
    """Independently count canonical core objects and verify build integration and totals."""
    from cardenveil.serialization import character_from_archive

    build = importlib.import_module("build")
    for name, folder in {"PUBLIC": tmp_path, "DATA": tmp_path / "data", "ASSETS": tmp_path / "assets", "DOWNLOADS": tmp_path / "downloads"}.items():
        monkeypatch.setattr(build, name, folder)
    build.build()
    data = json.loads((tmp_path / "statistiques/donnees.json").read_text(encoding="utf-8"))
    sheets = [character_from_archive(p) for p in (ROOT / "Final").glob("*.zip")]
    count = sum(len(c.capacities) for c in sheets)
    assert data["characters"] == len(sheets)
    assert data["capacities"] == count
    assert sum(data["races"].values()) == len(sheets)
    assert sum(data["colors"].values()) == sum(data["combinations"].values()) == count
    assert data["costs"]["all"]["total"]["n"] + data["costs"]["all"]["total"]["missing"] == count
    assert sum(s["total"]["n"] for k, s in data["costs"].items() if k != "all") == data["costs"]["all"]["total"]["n"]
    assert all(s["n"] + s["missing"] == len(sheets) for s in data["stats"].values())


@pytest.mark.parametrize("width", [390, 1280])
def test_dashboard_browser_no_overflow_or_javascript_dependency(dashboard, tmp_path, width):
    """Load real generated charts and stylesheet in mobile/desktop iframe viewports."""
    characters = json.loads((ROOT / "web/public/data/characters.json").read_text(encoding="utf-8"))
    dashboard.write_statistics(tmp_path, characters)
    source = (tmp_path / "statistiques/index.html").read_text(encoding="utf-8")
    source = source.replace('href="/', 'href="/web/public/')
    harness = '''<pre id="result">RUNNING</pre><script>
    const frame=document.createElement('iframe');frame.width=WIDTH;frame.height=900;
    frame.onload=()=>{try{
      const doc=frame.contentDocument;
      if(doc.querySelectorAll('.stat-kpis article').length!==6)throw Error('KPI cards missing');
      if(doc.querySelectorAll('.stat-histograms article').length!==4)throw Error('Stat distributions missing');
      if(doc.documentElement.scrollWidth>doc.documentElement.clientWidth+1)throw Error('Horizontal page overflow '+doc.documentElement.scrollWidth);
      if(!doc.querySelector('table caption') || !doc.querySelector('.bar-caption strong'))throw Error('Accessible chart values missing');
      if(doc.querySelector('script'))throw Error('Dashboard unexpectedly depends on scripts');
      document.querySelector('#result').textContent='PASS';
    }catch(e){document.querySelector('#result').textContent='FAIL '+e.message;}};
    frame.srcdoc=SOURCE;document.body.append(frame);
    </script>'''.replace("WIDTH", str(width)).replace("SOURCE", json.dumps(source).replace("</", "<\\/"))
    run_harness(tmp_path, harness)

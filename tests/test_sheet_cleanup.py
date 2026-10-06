"""Check text preservation and removal of gear without changing the canonical JSON format."""

from cardenveil.domain.sheet import Character
from cardenveil.importers.sheet_cleanup import (
    normalize_and_empty_gear,
    plain_sheet_text,
)
from cardenveil.serialization import character_from_dict, character_to_dict


def test_html_becomes_readable_text():
    """Keep paragraph boundaries, accents and dice formulas; drop attributes and hidden content."""
    source = (
        '<p>Humain <strong data-start="1">Mod Esprit d6</strong></p>'
        '<p>3 × Force<br>PV ≥ 5 &amp; &lt; 10</p>'
    )
    result = plain_sheet_text(source)
    assert result == "Humain Mod Esprit d6\n\n3 × Force\nPV ≥ 5 & < 10"
    assert plain_sheet_text("&lt;p&gt;Death &lt;b&gt;Fusion&lt;/b&gt;&lt;/p&gt;") == "Death Fusion"
    assert plain_sheet_text("Coût < 10 et score > 5") == "Coût < 10 et score > 5"
    assert plain_sheet_text("<script>hidden()</script><p>Visible</p>") == "Visible"


def test_cleanup_is_idempotent_and_preserves_mechanics():
    """Empty items without clearing resources, defenses, progression or totem mechanics."""
    sheet = character_to_dict(Character())
    sheet["identity"]["race"] = "<p>Humain</p>"
    sheet["equipment"]["casque"]["nom"] = "Vrai casque"
    sheet["equipment"]["casque"]["volonte"] = 3
    sheet["inventory"]["inventaire"] = "<p>Objets</p>"
    sheet["inventory"]["totem"] = "<p>Effet du totem</p>"
    sheet["resources"]["or"] = 12
    sheet["defense"]["parade"] = 2
    keys = set(sheet)
    normalize_and_empty_gear(sheet)
    assert set(sheet) == keys
    assert sheet["identity"]["race"] == "Humain"
    assert all(v == "" for piece in sheet["equipment"].values() for v in piece.values())
    assert sheet["weapons"] == sheet["inventoryItems"] == []
    assert sheet["inventory"]["inventaire"] == ""
    assert sheet["inventory"]["totem"] == "Effet du totem"
    assert sheet["resources"]["or"] == 12 and sheet["defense"]["parade"] == 2
    assert character_to_dict(character_from_dict(sheet)) == sheet
    before = character_to_dict(character_from_dict(sheet))
    normalize_and_empty_gear(sheet)
    assert sheet == before

"""Ensure editorial fixes never rewrite numerical mechanics, names or image references."""

import importlib
from pathlib import Path


def test_spelling_is_targeted_and_idempotent(monkeypatch):
    """Repair known OCR ligatures while preserving proper names, URLs and all numbers."""
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts'))
    repair = importlib.import_module('correct_sheet_spelling').repair
    sheet = {'name': 'Bad trip', 'portrait': '/assets/example.png',
             'description': 'Tu e ectues une attaque in igeant 3d10 dégats.',
             'cost': {'color': 'spade', 'total': 13}, 'pvMax': 180,
             'notes': 'https://example.com/?a=inigeant'}
    changes = []
    result = repair(sheet, changes)
    assert result['description'] == 'Tu effectues une attaque infligeant 3d10 dégâts.'
    assert result['cost'] == sheet['cost'] and result['pvMax'] == 180
    assert result['name'] == sheet['name'] and result['portrait'] == sheet['portrait']
    assert result['notes'] == sheet['notes']
    assert len(changes) == 1
    again = []
    assert repair(result, again) == result
    assert not again

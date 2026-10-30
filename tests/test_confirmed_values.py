"""Check user-confirmed formulas and explicitly preserved passive exceptions."""

import importlib
from pathlib import Path

import pytest


@pytest.mark.parametrize('force,agility,spirit,trained,will,miss,channel', [
    (6, 14, 18, False, -2, 1, 4),
    (16, 8, 8, True, 6, 2, -1),
    (8, 6, 12, True, -2, 3, 1),
])
def test_confirmed_formulas(monkeypatch, force, agility, spirit, trained, will, miss, channel):
    """Double mastered Resilience and clamp miss to one without altering other fields."""
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts'))
    apply = importlib.import_module('recalculate_confirmed_values').apply_values
    sheet = {'id': 'test', 'stats': {'force': force, 'agilite': agility, 'esprit': spirit, 'social': 10},
             'skills': {'resilience': {'trained': trained, 'bonus': 999}, 'perception': {'trained': trained}},
             'resources': {'tokens': {'force': 0, 'agilite': 0, 'esprit': 0, 'social': 0}},
             'derived': {'pvActuels': 23, 'pvMax': 140, 'bonusAttaque': 4}}
    apply(sheet)
    assert sheet['derived'] == {'pvActuels': 23, 'pvMax': 140, 'bonusAttaque': '',
                                'volonte': will, 'seuilMiss': miss, 'canalisation': channel,
                                'initiative': agility - 10, 'mouvement': 5 + (agility + 1) // 2,
                                'perceptionPassive': 10 + channel * (2 if trained else 1)}
    assert sheet['resources']['tokens']['social'] == 1
    # No field access or mutation is allowed for the explicitly excluded character.
    exception = {'id': 'goldomus'}
    apply(exception)
    assert exception == {'id': 'goldomus'}

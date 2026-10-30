"""Exercise vector/raster skill-dot extraction without any model calls."""

import importlib
from pathlib import Path

import pytest

pymupdf = pytest.importorskip('pymupdf')


def extractor(monkeypatch):
    """Import the standalone review script without executing its migration."""
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts'))
    return importlib.import_module('extract_pdf_skill_dots')


def test_real_chillisy_masteries(monkeypatch):
    """Read all 16 circles and preserve Nature→Survie and actual social-row order."""
    module = extractor(monkeypatch)
    with pymupdf.open(module.ROOT / 'Toconvert/Fiche Chillisy.pdf') as document:
        result = module.extract(document[0])
    assert len(result) == 16
    assert {k for k, v in result.items() if v['trained']} == {
        'arcanes', 'perception', 'survie', 'perspicacite'}
    assert result['dressage']['trained'] is False


@pytest.mark.parametrize('filename', ['Rousse Naratif_merged.pdf', 'Tikoun Naratif_merged.pdf'])
def test_unmarked_pdf_is_not_guessed(monkeypatch, filename):
    """Every empty circle stays false instead of inferring skills from lore or statistics."""
    module = extractor(monkeypatch)
    with pymupdf.open(module.ROOT / 'Toconvert' / filename) as document:
        assert not any(v['trained'] for v in module.extract(document[0]).values())


def test_incomplete_layout_is_rejected(monkeypatch):
    """Do not write anything when the template cannot be fully recognised."""
    module = extractor(monkeypatch)
    with pymupdf.open() as document:
        page = document.new_page()
        with pytest.raises(ValueError, match='Expected 16'):
            module.extract(page)

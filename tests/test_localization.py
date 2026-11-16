"""Bilingual output must preserve mechanics, technical IDs and safe HTML."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('localization', ROOT / 'web/localization.py')
localization = importlib.util.module_from_spec(spec)
spec.loader.exec_module(localization)


def test_translated_values_leave_canonical_keys_numbers_and_assets_unchanged():
    source = {'id': 'force', 'stats': {'force': 16}, 'cost': {'color': 'heart', 'total': 8},
              'portrait': '/assets/force.webp', 'description': 'Force', 'trained': True}
    result = localization.translate_data(source, {'Force': 'Strength'})
    assert result == {**source, 'description': 'Strength'}
    assert source['description'] == 'Force'


def test_missing_prose_fails_instead_of_silently_publishing_french():
    with pytest.raises(ValueError, match='Missing character translation'):
        localization.translate_data({'description': 'Une capacité non traduite'}, {})


def test_html_translates_accessibility_without_touching_embedded_payload():
    parser = localization.LocalizedHTML({'Chercher': 'Search', 'Force': 'Strength'})
    parser.feed('<html lang="fr"><input id="force" aria-label="Chercher"><p>Force</p>'
                '<script type="application/json">{"force":16,"text":"Force"}</script>'
                '<a href="/regles/combat/#armes">Force</a></html>')
    result = ''.join(parser.parts)
    assert 'lang="en"' in result and 'aria-label="Search"' in result
    assert '<p>Strength</p>' in result and 'id="force"' in result
    assert '{"force":16,"text":"Force"}' in result
    assert 'href="/en/regles/combat/#armes"' in result


def test_script_routes_never_rewrite_api_or_shared_assets():
    source = "fetch('/api/gm/config'); fetch('/data/characters.json'); const r=/^\\/personnages\\/([^/]+)/; const a='/assets/p.png';"
    result = localization.localized_script(source)
    assert "'/api/gm/config'" in result
    assert "'/en/data/characters.json'" in result
    assert r'/^\/en\/personnages\/' in result
    assert "'/assets/p.png'" in result


def test_switch_is_idempotent_and_retains_both_editions():
    page = '<html><head></head><body><header></header></body></html>'
    first = localization.language_shell(page, Path('personnages/mimyr/index.html'), 'en')
    second = localization.language_shell(first, Path('personnages/mimyr/index.html'), 'en')
    assert second.count('data-language="en"') == 1
    assert second.count('src="/language.js"') == 1
    assert 'href="/personnages/mimyr/"' in second
    assert 'href="/en/personnages/mimyr/"' in second


def test_english_markdown_tracks_only_manifest_selected_french_markdown(monkeypatch):
    import hashlib
    monkeypatch.syspath_prepend(str(ROOT / 'web'))
    from fragmented_rules import indexed_rule_files

    hashes = json.loads((ROOT / 'docs/rules/en/sources.json').read_text(encoding='utf-8'))
    manifest, french = indexed_rule_files(ROOT)
    _, english = indexed_rule_files(ROOT, locale='en')
    assert set(french) == set(english) == set(manifest['documents'])
    assert 'Encounter-creation.md' not in {path.name for path in french.values()}
    for path in french.values():
        current = hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest()
        assert hashes[path.name] == current


def test_reviewed_raw_power_preserves_pool_multiplier_and_damage_type():
    spec = importlib.util.spec_from_file_location('review_translations', ROOT / 'scripts/review_translations.py')
    review = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(review)
    assert review.formula_translation('2.5 Mod Esprit D6 Force') == '2.5 Raw Spirit Power (Spirit Mod d6) Force'
    assert review.formula_translation('1/2 Mod Social D6 Psychiques') == '1/2 Raw Social Power (Social Mod d6) psychic'
    assert review.raw_power('2 × Raw Power (contextual Mod d6)') == '2 × Raw Power (contextual Mod d6)'
    assert review.raw_power('3 × Spirit Mod d6') == '3 × Raw Spirit Power (Spirit Mod d6)'


def test_complete_publication_preserves_all_numeric_data_and_archives():
    import zipfile
    public = ROOT / 'web/public'
    english = public / 'en'
    if not (english / 'downloads').exists():
        pytest.skip('Complete the bilingual build first')
    fr = json.loads((public / 'data/characters.json').read_text(encoding='utf-8'))
    en = json.loads((english / 'data/characters.json').read_text(encoding='utf-8'))
    assert [c['id'] for c in fr] == [c['id'] for c in en]

    def compare(source, translated, path=''):
        assert type(source) is type(translated), path
        if isinstance(source, dict):
            assert set(source) <= set(translated), path
            for key, value in source.items():
                compare(value, translated[key], path + '/' + key)
        elif isinstance(source, list):
            assert len(source) == len(translated), path
            for i, (a, b) in enumerate(zip(source, translated)):
                compare(a, b, path + '/' + str(i))
        elif not isinstance(source, str) or path.rsplit('/', 1)[-1] in localization.SKIP - {'download','pageUrl','printUrl'}:
            assert source == translated, path

    compare(fr, en)
    for archive in (ROOT / 'Final').glob('*.zip'):
        with zipfile.ZipFile(archive) as original, zipfile.ZipFile(english / 'downloads' / archive.name) as translated:
            assert original.namelist() == translated.namelist()
            for name in original.namelist():
                a, b = original.read(name), translated.read(name)
                if name.endswith('.rpsheet.json') or name == 'metadata.json':
                    compare(json.loads(a.decode('utf-8-sig')), json.loads(b.decode('utf-8-sig')), archive.name + '/' + name)
                else:
                    assert a == b, archive.name + '/' + name

"""Deterministic bilingual publication from reviewed, versioned translations.

No network calls at build time. Canonical French archives and machine keys stay intact.
"""
from __future__ import annotations
import hashlib
import json
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / 'web/i18n'
SCRIPTS = ('app.js', 'catalogue.js', 'print.js', 'rules.js', 'gm.js', 'rules-chat.js')
SKIP = {'id', 'image', 'portrait', 'download', 'printUrl', 'pageUrl', 'creator', 'joueur', 'color', 'forceAgi', 'schemaVersion', 'version'}


def load(name):
    return json.loads((I18N / name).read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def translate_data(value, translations, key=''):
    if key in SKIP:
        return value
    if isinstance(value, dict):
        return {k: translate_data(v, translations, k) for k, v in value.items()}
    if isinstance(value, list):
        return [translate_data(v, translations, key) for v in value]
    if isinstance(value, str):
        if value in translations:
            return translations[value]
        if re.search(r'[A-Za-zÀ-ÿ]{2}', value) and not value.startswith(('/', 'http:', 'https:', 'data:')):
            raise ValueError(f'Missing character translation: {key}: {value[:100]}')
    return value


def localized_url(url):
    origin = 'https://cardenveil-characters.pages.dev'
    if url.startswith(origin):
        return origin + localized_url(url[len(origin):])
    if url == '/' or url.startswith(('/?', '/#')):
        return '/en' + url
    if url.startswith(('/personnages/', '/regles/', '/statistiques/', '/gm/', '/data/', '/downloads/', '/print.html')):
        return '/en' + url
    if url.split('?')[0].lstrip('/') in SCRIPTS and url.startswith('/'):
        return '/en' + url
    return url


class LocalizedHTML(HTMLParser):
    """Translate text/accessible attributes, never scripts, IDs or embedded data."""
    def __init__(self, translations, *, english=True, collect=None, already_english=None):
        super().__init__(convert_charrefs=True)
        self.translations, self.english, self.collect = translations, english, collect
        self.parts = []
        self.blocked = 0
        self.already_english = already_english or set()

    def text(self, value):
        stripped = value.strip()
        if not stripped:
            return value
        if stripped in self.already_english:
            return value
        if self.collect is not None and re.search(r'[A-Za-zÀ-ÿ]{2}', stripped):
            self.collect.add(stripped)
        translated = self.translations.get(stripped, stripped) if self.english else stripped
        return value[:len(value)-len(value.lstrip())] + translated + value[len(value.rstrip()):]

    def handle_decl(self, decl):
        self.parts.append('<!' + decl + '>')

    def handle_comment(self, data):
        self.parts.append('<!--' + data + '-->')

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        converted = []
        for key, value in attrs:
            if value is None:
                converted.append(key)
                continue
            if key in {'alt', 'title', 'aria-label', 'placeholder', 'data-question'} or (
                key == 'value' and tag == 'input' and values.get('id') == 'session-name') or (
                tag == 'meta' and key == 'content' and
                (values.get('name') in {'description', 'twitter:title', 'twitter:description', 'twitter:image:alt'}
                 or values.get('property') in {'og:title', 'og:description', 'og:image:alt'})):
                value = self.text(value)
            if self.english:
                if key in {'href', 'src', 'action'} and 'hreflang' not in values:
                    value = localized_url(value)
                if tag == 'html' and key == 'lang':
                    value = 'en'
                if tag == 'meta' and key == 'content':
                    if values.get('property') == 'og:locale':
                        value = 'en_US'
                    elif values.get('property') == 'og:url':
                        value = localized_url(value)
                    elif values.get('http-equiv') == 'refresh':
                        value = re.sub(r'(?<=url=).*', lambda m: localized_url(m[0]), value)
            converted.append(f'{key}="{escape(value, quote=True)}"')
        self.parts.append('<' + tag + (' ' + ' '.join(converted) if converted else '') + '>')
        if tag in {'script', 'style'}:
            self.blocked += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.parts[-1] = self.parts[-1][:-1] + '/>'

    def handle_endtag(self, tag):
        self.parts.append('</' + tag + '>')
        if tag in {'script', 'style'}:
            self.blocked = max(0, self.blocked - 1)

    def handle_data(self, value):
        self.parts.append(value if self.blocked else escape(self.text(value), quote=False))


def language_shell(html, path, language):
    """Static language links work without JS; JS preserves query/fragment and preference."""
    html = re.sub(r'<!-- language-switch -->.*?<!-- /language-switch -->', '', html, flags=re.S)
    html = html.replace('<script src="/language.js"></script>', '').replace('<link rel="stylesheet" href="/language.css">', '')
    fr = '/' + path.as_posix().removesuffix('index.html')
    en = '/en' + fr
    alternates = f'<link rel="alternate" hreflang="fr" href="{fr}"><link rel="alternate" hreflang="en" href="{en}">'
    if 'hreflang="fr"' not in html:
        html = html.replace('</head>', alternates + '</head>')
    html = html.replace('<head>', '<head><script src="/language.js"></script><link rel="stylesheet" href="/language.css">', 1)
    french_flag = '<svg viewBox="0 0 30 20" aria-hidden="true"><path fill="#fff" d="M0 0h30v20H0z"/><path fill="#002395" d="M0 0h10v20H0z"/><path fill="#ed2939" d="M20 0h10v20H20z"/></svg>'
    english_flag = '<svg viewBox="0 0 30 20" aria-hidden="true"><path fill="#012169" d="M0 0h30v20H0z"/><path stroke="#fff" stroke-width="5" d="m0 0 30 20M30 0 0 20"/><path stroke="#c8102e" stroke-width="2" d="m0 0 30 20M30 0 0 20"/><path stroke="#fff" stroke-width="7" d="M15 0v20M0 10h30"/><path stroke="#c8102e" stroke-width="4" d="M15 0v20M0 10h30"/></svg>'
    selector = ('<!-- language-switch --><nav class="language-switch" aria-label="' + ('Language' if language == 'en' else 'Langue') + '">'
                + f'<a href="{fr}" lang="fr" hreflang="fr" data-language="fr" aria-label="Français"' + (' aria-current="true"' if language == 'fr' else '') + '>' + french_flag + ' FR</a>'
                + f'<a href="{en}" lang="en" hreflang="en" data-language="en" aria-label="English"' + (' aria-current="true"' if language == 'en' else '') + '>' + english_flag + ' EN</a></nav><!-- /language-switch -->')
    if '</header>' in html:
        html = html.replace('</header>', selector + '</header>', 1)
    else:
        html = html.replace('<body>', '<body>' + selector, 1)
    return html


def localized_script(source):
    # Only the known public content routes; APIs, assets, CSS and machine keys stay shared.
    for prefix in ['/personnages/', '/regles/', '/statistiques/', '/gm/', '/data/', '/downloads/', '/print.html']:
        source = re.sub(r'(?<![\w/])' + re.escape(prefix), '/en' + prefix, source)
        source = source.replace(prefix.replace('/', r'\/'), r'\/en' + prefix.replace('/', r'\/'))
    source = source.replace('href="/"', 'href="/en/"').replace("location.assign('/')", "location.assign('/en/')")
    return source


def build(public, characters, *, collect_only=False):
    from static_pages import write_character, write_index, label
    from fragmented_rules import build as build_rules, indexed_rule_files
    from rag_index import build_rag_index
    translations = load('characters.en.json')
    character_hashes = load('characters.sources.json')
    for character in characters:
        current = hashlib.sha256(json.dumps(character, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        if character_hashes.get(character['id']) != current:
            raise ValueError(f'English character translation is missing or outdated: {character["id"]}')
    source_hashes = json.loads((ROOT / 'docs/rules/en/sources.json').read_text(encoding='utf-8'))
    _, french_rule_files = indexed_rule_files(ROOT)
    for path in french_rule_files.values():
        current = hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest()
        if source_hashes.get(path.name) != current:
            raise ValueError(f'English rule translation is missing or outdated: {path.name}')
    ui_path = I18N / 'ui.en.json'
    ui = load('ui.en.json') if ui_path.exists() else {}
    english = public / 'en'
    english.mkdir(exist_ok=True)
    localized = []
    for character in characters:
        item = translate_data(character, translations)
        item['catalog']['classKeys'] = character.get('catalog', {}).get('class', [])
        for key in ['download', 'pageUrl', 'printUrl']:
            item[key] = localized_url(item[key])
        localized.append(item)
        write_character(english, item)
    write_index(english, localized)
    save(english / 'data/characters.json', localized)
    build_rules(ROOT, english, locale='en')
    # Compute statistics from canonical data; translate its presentation, not the grouping keys.
    stats = english / 'statistiques/index.html'
    stats.parent.mkdir(exist_ok=True)
    stats.write_text((public / 'statistiques/index.html').read_text(encoding='utf-8'), encoding='utf-8')
    statistics = json.loads((public / 'statistiques/donnees.json').read_text(encoding='utf-8'))
    def translated_statistics(value):
        if isinstance(value, dict):
            return {k: translated_statistics(v) for k, v in value.items()}
        if isinstance(value, list):
            return [translated_statistics(v) for v in value]
        return ui.get(value, translations.get(value, value)) if isinstance(value, str) else value
    save(english / 'statistiques/donnees.json', translated_statistics(statistics))
    for name in ['index.html', 'print.html', 'gm/index.html']:
        target = english / name
        target.parent.mkdir(exist_ok=True)
        target.write_text((public / name).read_text(encoding='utf-8'), encoding='utf-8')
    pending = set()
    # Translated prose is already English. Only template labels need a second dictionary.
    known_english = set()
    for value in translations.values():
        known_english.add(value.strip())
        fragment = LocalizedHTML({}, collect=known_english)
        fragment.feed(value)
    from fragmented_rules import Markdown
    manifest, english_rule_files = indexed_rule_files(ROOT, locale='en')
    for path in english_rule_files.values():
        fragment = LocalizedHTML({}, collect=known_english)
        fragment.feed(Markdown(manifest['images'], {}).render(path.read_text(encoding='utf-8'), skip_title=False))
    for path in english.rglob('*.html'):
        parser = LocalizedHTML(ui, collect=pending, already_english=known_english)
        parser.feed(path.read_text(encoding='utf-8'))
        rendered = ''.join(parser.parts)
        path.write_text(language_shell(rendered, path.relative_to(english), 'en'), encoding='utf-8')
    # Headings and index metadata use the same glossary as the HTML.
    index_path = english / 'regles/search.json'
    index = json.loads(index_path.read_text(encoding='utf-8'))
    for row in index:
        row['url'] = localized_url(row['url'])
        pending.add(row['title'])
        row['title'] = ui.get(row['title'], row['title'])
    save(index_path, index)
    save(I18N / 'ui-pending.json', sorted(pending - ui.keys()))
    if collect_only:
        return
    if pending - ui.keys():
        raise ValueError(f'{len(pending - ui.keys())} untranslated HTML strings; run the editorial translation workflow')
    metadata = load('js-sources.json')
    def all_keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from all_keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from all_keys(child)
    field_labels = {key: ui.get(label(key), label(key)) for key in set(all_keys(characters))}
    # Curated spellings take precedence over the legacy capitalization fallback.
    field_labels.update({'force':'Strength','agilite':'Agility','esprit':'Spirit','social':'Social',
        'athletisme':'Athletics','resilience':'Resilience','acrobaties':'Acrobatics','discretion':'Stealth',
        'escamotage':'Sleight of Hand','arcanes':'Arcana','culture':'Knowledge','survie':'Survival',
        'tromperie':'Deception','representation':'Performance','perspicacite':'Insight','dressage':'Animal Handling',
        'deflexion':'Deflection','parade':'Parry','armure':'Armor','de':'Die','forceAgi':'Attribute modifier'})
    for name in SCRIPTS:
        source = (public / name).read_text(encoding='utf-8')
        if metadata.get(name) != hashlib.sha256(source.encode()).hexdigest():
            raise ValueError(f'English JavaScript needs review after source changes: {name}')
        script = localized_script((I18N / 'en' / name).read_text(encoding='utf-8'))
        if name == 'app.js':
            script = script.replace('const pretty=', 'Object.assign(fieldNames,' + json.dumps(field_labels, ensure_ascii=False) + ');\nconst pretty=')
        if name == 'print.js':
            script = script.replace('const label=', 'Object.assign(names,' + json.dumps(field_labels, ensure_ascii=False) + ');\nconst label=')
        (english / name).write_text(script, encoding='utf-8')
    for path in [public / 'index.html', public / 'print.html', public / 'gm/index.html',
                 *list((public / 'personnages').rglob('*.html')), *list((public / 'regles').rglob('*.html')),
                 public / 'statistiques/index.html']:
        path.write_text(language_shell(path.read_text(encoding='utf-8'), path.relative_to(public), 'fr'), encoding='utf-8')
    # English retrieval has its own corpus, never stale French vectors attached to translated text.
    save(english / 'data/rag-index.json', build_rag_index(localized, None, labeler=lambda text: ui.get(text, text), language='en'))
    download_dir = english / 'downloads'
    download_dir.mkdir(exist_ok=True)
    for archive in (ROOT / 'Final').glob('*.zip'):
        with zipfile.ZipFile(archive) as source, zipfile.ZipFile(download_dir / archive.name, 'w', zipfile.ZIP_DEFLATED) as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename.endswith('.rpsheet.json') or info.filename == 'metadata.json':
                    payload = json.loads(data.decode('utf-8-sig'))
                    data = json.dumps(translate_data(payload, translations), ensure_ascii=False, indent=2).encode()
                target.writestr(info, data)
    print(f'English publication: {len(localized)} characters, {sum(len(c["capacities"]) for c in localized)} abilities')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--collect-ui', action='store_true')
    args = parser.parse_args()
    public = ROOT / 'web/public'
    build(public, json.loads((public / 'data/characters.json').read_text(encoding='utf-8')), collect_only=args.collect_ui)

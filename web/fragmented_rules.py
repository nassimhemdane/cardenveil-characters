"""Render the versioned player-only Markdown edition, including Obsidian race art."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

from rules_pages import CHAPTERS, shell, slug


class Text(HTMLParser):
    """Read rendered text for search without indexing markup or source-file attributes."""

    def __init__(self, source: str):
        """Collect normalized visible text from one already sanitized fragment."""
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.feed(source)

    def handle_data(self, value: str) -> None:
        """Retain every text node with boundaries between adjacent inline elements."""
        self.parts.append(value)

    @property
    def value(self) -> str:
        """Return whitespace-normalized text for labels and search excerpts."""
        return ' '.join(' '.join(self.parts).split())


class Markdown:
    """Render the actual source subset safely: headings, nested lists, tables, quotes and art."""

    tokens = re.compile(r'!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]|!\[([^\]]*)\]\(([^)]+)\)|\[\[([^\]]+)\]\]|\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`|\*\*([^*]+)\*\*|__([^_]+)__|\*([^*\n]+)\*')
    item = re.compile(r'^(\s*)([-+*]|\d+[.)])\s+(.+)$')

    def __init__(self, images: dict, links: dict):
        """Keep document-local anchors and approved image/link lookup tables."""
        self.images = images
        self.links = links
        self.toc: list[tuple[str, str]] = []
        self.outline: list[tuple[int, str, str]] = []
        self.used: dict[str, int] = {}
        self.offset = 0

    def inline(self, source: str) -> str:
        """Escape raw HTML and render only recognized, explicitly safe inline elements."""
        # Obsidian exports occasionally contain an empty bold marker before real prose.
        # Discard only that formatting artifact; words and mechanics remain untouched.
        source = source.replace('****', '')
        parts, start = [], 0
        for match in self.tokens.finditer(source):
            parts.append(escape(source[start:match.start()]))
            if match[1] or match[3]:
                reference = match[1] or match[3]
                image = self.images.get(reference)
                alt = (match[2] or 'Illustration des règles').split('|')[0]
                if image:
                    parts.append(f'<img class="rule-illustration" src="{escape(image["url"])}" alt="{escape(alt)}" width="{image["width"]}" height="{image["height"]}" loading="lazy" decoding="async">')
                else:
                    parts.append('<span class="missing-illustration">Illustration non disponible dans les sources locales.</span>')
            elif match[4] or match[6]:
                if match[4]:
                    destination, _, label = match[4].partition('|')
                    label = label or destination.split('#')[0]
                else:
                    label, destination = match[5], match[6]
                path, _, anchor = unquote(destination).partition('#')
                route = self.links.get(path.removesuffix('.md'))
                if route:
                    url = route + ('#' + slug(anchor) if anchor else '')
                elif destination.startswith(('/regles/', 'https://', 'http://')):
                    url = destination
                else:
                    url = ''
                parts.append(f'<a href="{escape(url)}">{escape(label)}</a>' if url else escape(label))
            elif match[7]:
                parts.append('<code>' + escape(match[7]) + '</code>')
            elif match[8] or match[9]:
                parts.append('<strong>' + self.inline(match[8] or match[9]) + '</strong>')
            else:
                parts.append('<em>' + self.inline(match[10]) + '</em>')
            start = match.end()
        parts.append(escape(source[start:]))
        return ''.join(parts).replace('\\|', '|')

    def heading(self, title: str, level: int) -> str:
        """Create unique anchors and retain heading levels for hierarchical navigation."""
        rendered = self.inline(title)
        label = Text(rendered).value
        base = slug(label)
        self.used[base] = self.used.get(base, 0) + 1
        anchor = base + (f'-{self.used[base]}' if self.used[base] > 1 else '')
        if level <= 3:
            self.toc.append((anchor, label))
        self.outline.append((level, anchor, label))
        return f'<h{level} class="rule-heading" id="{anchor}">{rendered}</h{level}>'

    def render(self, source: str, *, skip_title: bool = True) -> str:
        """Keep the first document title in the shell and preserve all remaining section levels."""
        lines = source.splitlines()
        if skip_title:
            first = next((i for i, line in enumerate(lines) if line.strip()), None)
            if first is not None and re.match(r'^#\s+', lines[first]):
                lines.pop(first)
        self.offset = int(any(re.match(r'^#\s+\S', line) for line in lines))
        return self.blocks(lines)

    def blocks(self, lines: list[str]) -> str:
        """Render recursive block structures, retaining source order and table contents."""
        result, index = [], 0
        while index < len(lines):
            raw = lines[index]
            line = raw.strip()
            if not line or re.fullmatch(r'#{1,6}\s*', line):
                index += 1
                continue
            heading = re.match(r'^(#{1,6})\s+(.+)', line)
            if heading:
                result.append(self.heading(heading[2], min(6, max(2, len(heading[1]) + self.offset))))
                index += 1
            elif re.fullmatch(r'(?:-{3,}|\*{3,}|_{3,})', line):
                result.append('<hr>')
                index += 1
            elif line.startswith('```'):
                code = []
                index += 1
                while index < len(lines) and not lines[index].strip().startswith('```'):
                    code.append(lines[index])
                    index += 1
                result.append('<pre><code>' + escape('\n'.join(code)) + '</code></pre>')
                index += 1
            elif line.startswith('>'):
                quote = []
                while index < len(lines) and lines[index].strip().startswith('>'):
                    quote.append(re.sub(r'^\s*> ?', '', lines[index]))
                    index += 1
                result.append('<blockquote class="rule-example">' + self.blocks(quote) + '</blockquote>')
            elif self.item.match(raw):
                first = self.item.match(raw)
                indent, ordered = len(first[1]), first[2][0].isdigit()
                tag = 'ol' if ordered else 'ul'
                items = []
                start_attr = f' start="{int(first[2].rstrip(".)"))}"' if ordered else ''
                while index < len(lines):
                    match = self.item.match(lines[index])
                    if not match or len(match[1]) != indent or match[2][0].isdigit() != ordered:
                        break
                    body = [match[3]]
                    index += 1
                    while index < len(lines):
                        next_line = lines[index]
                        if next_line.strip() and len(next_line) - len(next_line.lstrip()) <= indent:
                            break
                        body.append(next_line[min(len(next_line), indent + 2):])
                        index += 1
                    items.append('<li>' + self.blocks(body) + '</li>')
                result.append(f'<{tag}{start_attr}>' + ''.join(items) + f'</{tag}>')
            elif line.startswith('|'):
                rows = []
                while index < len(lines) and lines[index].strip().startswith('|'):
                    cells = re.split(r'(?<!\\)\|', lines[index].strip().strip('|'))
                    if not all(re.fullmatch(r'\s*:?-+:?\s*', cell) for cell in cells):
                        tag = 'th' if not rows else 'td'
                        rows.append('<tr>' + ''.join(f'<{tag}>{self.inline(c.strip())}</{tag}>' for c in cells) + '</tr>')
                    index += 1
                result.append('<div class="table-scroll" tabindex="0" role="region" aria-label="Tableau des règles"><table><thead>' + rows[0] + '</thead><tbody>' + ''.join(rows[1:]) + '</tbody></table></div>')
            else:
                paragraph = [line]
                index += 1
                while index < len(lines) and lines[index].strip() and not re.match(r'^\s*(?:#|>|\||```|[-+*]\s|\d+[.)]\s|---)', lines[index]):
                    paragraph.append(lines[index].strip())
                    index += 1
                result.append('<p class="rule-paragraph">' + self.inline(' '.join(paragraph)) + '</p>')
        return '\n'.join(result)


def race_section(source: str) -> tuple[str, str]:
    """Move the race chapter to its own page without dropping any mechanics or later maluses."""
    match = re.search(r'^#\s+\*\*Races Jouables\*\*\s*$', source, re.M)
    if not match:
        raise ValueError('The playable-races section was not found in Personnage.md')
    end = re.search(r'^#\s+', source[match.end():], re.M)
    stop = match.end() + end.start() if end else len(source)
    races = source[match.start():stop]
    creation = source[:match.start()] + '# Races jouables\n\n[Consulter les races, leurs traits et leurs illustrations](/regles/races/).\n\n' + source[stop:]
    return creation, races


def render_races(source: str, renderer: Markdown) -> str:
    """Turn each explicitly delimited race into an illustrated card with its original traits."""
    sections = re.split(r'^###\s+', source, flags=re.M)
    introduction = sections[0].split('\n', 1)[1]
    body = renderer.render(introduction, skip_title=False)
    body += '<label class="race-search-label" for="race-search">Retrouver une race<input id="race-search" type="search" placeholder="Humain, elfe, nain…" autocomplete="off"></label>'
    body += f'<p id="race-count" role="status">{len(sections) - 1} races jouables</p><div class="races-grid">'
    for section in sections[1:]:
        title, _, content = section.partition('\n')
        title = re.sub(r'^\d+\.\s*', '', title.replace('**', '').strip())
        rendered = renderer.render(content, skip_title=False)
        images = re.findall(r'<img\b[^>]+>', rendered)
        rendered = re.sub(r'<img\b[^>]+>', '', rendered)
        rendered = re.sub(r'<p class="rule-paragraph">\s*</p>', '', rendered)
        if images:
            image = re.sub(r'alt="[^"]*"', f'alt="Illustration de la race {escape(title)}"', images[0])
        else:
            image = '<div class="race-art-missing">Illustration non disponible</div>'
            rendered = re.sub(r'<span class="missing-illustration">.*?</span>', '', rendered)
        heading = renderer.heading(title, 2)
        body += f'<article class="race-card" data-race="{escape(title)}"><div class="race-art">{image}</div>{heading}<div class="race-traits">{rendered}</div></article>'
    return body + '</div>'


def search_sections(body: str, title: str, key: str, source: str) -> list[dict]:
    """Index heading-level topics, not raw PDF pages, filename embeds, or duplicated source blocks."""
    entries = []
    for section in re.split(r'(?=<h[2-6]\b)', body):
        heading = re.search(r'<h[2-6][^>]*id="([^"]+)"[^>]*>(.*?)</h[2-6]>', section, re.S)
        section = re.sub(r'<a class="source-cite".*?</a>', '', section)
        text = Text(section).value
        if text:
            label = Text(re.sub(r'<a class="source-cite".*?</a>', '', heading[2])).value if heading else title
            entries.append({"title": title, "section": label, "url": f'/regles/{key}/' + ('#' + heading[1] if heading else ''), "text": text, "source": source, "format": "markdown"})
    return entries


def combat_navigation(outline: list[tuple[int, str, str]]) -> list[dict]:
    """Name practical combat categories without changing source titles or their mechanics."""
    categories = {
        'ressources-et-types-dactions': ('Ressources du round', set()),
        'initiative-et-deroulement': ('Initiative & déroulement', {'phase-mj', 'phase-joueurs'}),
        'duree-des-effets': ('Durée des effets', set()),
        'faire-un-jet-dinitiative': ('Jet d’initiative', set()),
        'actions-disponibles-en-combat': ('Actions en combat', {'actions-principales', 'actions-bonus', 'reactions'}),
        'regles-des-attaques-et-degats': ('Attaques & dégâts', set()),
        'armes': ('Armes & propriétés', {'armes-uniques', 'tableau-des-armes', 'liste-des-proprietes'}),
        'armures': ('Armures', set()),
        'inconscience-et-fatigue': ('Inconscience & fatigue', set()),
        'types-de-degats': ('Types de dégâts', {'interactions-elementaires'}),
        'combinaisons-elementaires': ('Combinaisons élémentaires', set()),
        'conditions-negatives': ('Conditions & zones d’effet', {'zones-deffet', 'zones-d-effet'}),
        'types-dactions-des-pnj': ('Actions des PNJ', set()),
        'rupture-legendaire': ('Rupture légendaire', set()),
    }

    def key(label: str) -> str:
        """Ignore source numbering and decorative symbols while matching exact topic names."""
        return re.sub(r'^\d+(?:-\d+)*-', '', slug(label))

    groups, selected = [], None
    for level, anchor, label in outline:
        topic = key(label)
        if topic in categories:
            title, children = categories[topic]
            selected = {'label': title, 'anchor': anchor, 'children': [], 'wanted': children}
            groups.append(selected)
        elif selected and topic in selected['wanted']:
            selected['children'].append({'label': re.sub(r'^\d+(?:\.\d+)*[. ]*', '', label).strip(), 'anchor': anchor})
    return groups


def chapter_navigation(outline: list[tuple[int, str, str]]) -> list[dict]:
    """Convert all source heading levels into one properly nested, navigable chapter tree."""
    roots, parents = [], []
    for level, anchor, label in outline:
        node = {'label': label, 'anchor': anchor, 'children': []}
        while parents and parents[-1][0] >= level:
            parents.pop()
        (parents[-1][1]['children'] if parents else roots).append(node)
        parents.append((level, node))
    return roots


def build(root: Path, public: Path) -> None:
    """Publish only the player snapshot, preserve old URLs as redirects and foreground the quick reference."""
    directory = root / 'docs/rules/fragmented'
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    if len(manifest['documents']) != 7 or any('MJ' in d['source'] for d in manifest['documents'].values()):
        raise ValueError('Only the seven player documents may be published')
    output = public / 'regles'
    output.mkdir(parents=True, exist_ok=True)
    for image in manifest['images'].values():
        target = public / image['url'].lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(directory / image['file'], target)
    sources = {}
    links = {}
    for key, data in manifest['documents'].items():
        payload = (directory / data['file']).read_bytes()
        if hashlib.sha256(payload).hexdigest() != data['sha256']:
            raise ValueError(f'Snapshot hash mismatch for {key}; rerun the explicit sync')
        sources[key] = payload.decode('utf-8-sig')
        links[Path(data['source']).stem] = links[key] = f'/regles/{key}/'
    creation, races = race_section(sources['creation'])
    rendered, chapter_sections = {}, {}
    # Prepare every chapter first so every page gets the same complete left navigation.
    for _, key, _, _, _ in CHAPTERS:
        renderer = Markdown(manifest['images'], links)
        raw = sources['creation' if key == 'races' else key]
        body = render_races(races, renderer) if key == 'races' else renderer.render(creation if key == 'creation' else raw)
        rendered[key] = (body, renderer)
        chapter_sections[key] = combat_navigation(renderer.outline) if key == 'combat' else chapter_navigation(renderer.outline)
    searchable, quick = [], ''
    for position, (_, key, title, description, _) in enumerate(CHAPTERS):
        original_key = 'creation' if key == 'races' else key
        raw = sources[original_key]
        body, renderer = rendered[key]
        if key == 'reference-rapide':
            quick = body
        source_name = manifest['documents'][original_key]['source']
        searchable.extend(search_sections(body, title, key, source_name))
        adjacent = []
        for offset, caption in [(-1, 'Précédent'), (1, 'Suivant')]:
            if 0 <= position + offset < len(CHAPTERS):
                neighbor = CHAPTERS[position + offset]
                adjacent.append(f'<a href="/regles/{neighbor[1]}/"><small>{caption}</small>{escape(neighbor[2])}</a>')
        body += '<nav class="chapter-links" aria-label="Parcours de lecture">' + ''.join(adjacent) + '</nav>'
        target = output / key
        target.mkdir(exist_ok=True)
        (target / 'index.html').write_text(shell(title, description, body, key,
                                              chapter_sections=chapter_sections), encoding='utf-8')
    featured = '<section class="quick-reference-feature"><span class="eyebrow">À garder ouvert pendant la partie</span><h2>La référence rapide, à portée de main.</h2><p>Jets, cartes, tokens, actions et défense : retrouvez directement l’essentiel.</p><a class="button primary" href="/regles/reference-rapide/">Ouvrir la référence rapide →</a><a class="button" href="/regles/races/">Explorer les races illustrées</a></section>'
    quick = re.sub(r'<a class="source-cite".*?</a>', '', quick)
    cards = re.split(r'(?=<h2\b)', quick)
    body = '<section class="quick-reference-home" aria-label="Référence rapide">' + ''.join('<article>' + card + '</article>' for card in cards if '<h2' in card) + '</section>'
    for group in dict.fromkeys(c[0] for c in CHAPTERS):
        body += f'<section id="{slug(group)}"><h2 class="group-title">{escape(group)}</h2><div class="docs-cards">'
        for section, key, title, description, _ in CHAPTERS:
            if section == group:
                body += f'<a class="docs-card" href="/regles/{key}/"><span class="eyebrow">Règles joueurs</span><h3>{escape(title)} ↗</h3><p>{escape(description)}</p></a>'
        body += '</div></section>'
    (output / 'index.html').write_text(shell('Les règles de Cardenveil', 'La référence rapide et les règles joueurs, organisées pour préparer et jouer une partie.', body, featured=featured, chapter_sections=chapter_sections), encoding='utf-8')
    (output / 'search.json').write_text(json.dumps(searchable, ensure_ascii=False), encoding='utf-8')
    # Replace only known generated legacy pages: no stale PDFs or MJ arbitrages remain public.
    for old, new in {'introduction': 'systeme-de-base', 'personnage': 'creation', 'cartes': 'capacites', 'attaques': 'combat', 'conditions': 'combat', 'armes': 'combat', 'versions': 'reference-rapide', 'arbitrages': 'reference-rapide'}.items():
        target = output / old
        target.mkdir(exist_ok=True)
        url = f'/regles/{new}/'
        (target / 'index.html').write_text(f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url={url}"><title>Règles actualisées — Cardenveil</title></head><body><a href="{url}">Consulter les règles actualisées</a></body></html>', encoding='utf-8')

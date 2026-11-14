"""Integrate the local card sandbox into the existing generated navigation."""
import re
from pathlib import Path


def integrate_test_page(public: Path) -> None:
    for path in public.rglob('*.html'):
        if {'test', 'atelier', 'assets'} & set(path.relative_to(public).parts):
            continue
        html = path.read_text(encoding='utf-8')
        def update_header(match):
            header = match.group(0)
            if 'href="/atelier/"' not in header:
                header = re.sub(r'(<a\b[^>]*href="/(?:en/)?regles/"[^>]*>.*?</a>)',
                                r'\1<a href="/atelier/">Atelier</a>', header, count=1)
            return header
        updated = re.sub(r'<header\b.*?</header>', update_header, html, flags=re.S)
        if '/test-entry.js' not in updated:
            updated = updated.replace('</head>', '<script src="/test-entry.js" defer></script></head>')
        if updated != html:
            path.write_text(updated, encoding='utf-8')
    legacy = public / 'test'
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / 'index.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/atelier/"><link rel="canonical" href="/atelier/"><title>Atelier Cardenveil</title><a href="/atelier/">Ouvrir l’Atelier</a>', encoding='utf-8')

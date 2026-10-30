"""Recover skill mastery from black PDF dots, never from character descriptions."""

import argparse
import json
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import pymupdf

from apply_october_updates import rewrite

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'aiden-grim': 'Fiche Aiden.pdf', 'aldric': 'FicheAldric.pdf',
    'amethyste': 'Amethyste.pdf', 'anain-proviste': 'Fiche Anain Proviste.pdf',
    'azella': 'Fiche Azella.pdf', 'brah-him': 'Fiche Brah_him.pdf',
    'caspian': 'Fiche Caspian.pdf', 'chillisy': 'Fiche Chillisy.pdf',
    'craps': 'Fiche Craps.pdf', 'esterelle': 'Fiche Esterelle.pdf',
    'felix': 'Fiche Felix.pdf', 'foist': 'Fiche Foist.pdf',
    'frimellade': 'Fiche Frimellade.pdf', 'gadolia': 'Gadolia.pdf',
    'gaelfire': 'Gaelfire.pdf', 'jean-louis': 'Fiche Jean-Louis.pdf',
    'kazehira': 'Fiche Kazehira.pdf', 'linraj': 'Linraj.pdf',
    'ma-skira': 'Maskira.pdf', 'noegwang-ryong': 'Fiche de Neogwang.pdf',
    'rousse': 'Rousse Naratif_merged.pdf', 'sanjkul-the-black-tentacle': 'Fiche Sanjkul.pdf',
    'shin': 'Fiche Shin.pdf', 'thelonius': 'Fiche Thelonius.pdf',
    'tikoun': 'Tikoun Naratif_merged.pdf', 'zotarh': 'Fiche de Zotarh.pdf',
    'zotaru': 'Fiche de Zotaru.pdf',
}
SKILLS = {'athletisme', 'resilience', 'acrobaties', 'discretion', 'escamotage',
          'arcanes', 'investigation', 'perception', 'culture', 'survie', 'persuasion',
          'tromperie', 'intimidation', 'representation', 'perspicacite', 'dressage'}


def label_key(text):
    """Match printed labels independently of underscores and accents."""
    text = ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if not unicodedata.combining(c))
    text = re.sub('[^a-z]', '', text)
    return {'nature': 'survie', 'discression': 'discretion'}.get(text, text)


def extract(page):
    """Require 16 uniquely labelled circles and agreement between vector dots and pixels."""
    drawings = page.get_drawings()
    circles = []
    for drawing in drawings:
        rect = drawing['rect']
        if (drawing['type'] == 's' and len(drawing['items']) == 4
                and 5 < rect.width < 9 and abs(rect.width - rect.height) < .5
                and 80 < rect.x0 < 100 and 190 < rect.y0 < 470):
            if not any(abs(rect.y0 - other.y0) < 1 for other in circles):
                circles.append(rect)
    if len(circles) != 16:
        raise ValueError(f'Expected 16 skill circles, found {len(circles)}')
    words = page.get_text('words')
    result = {}
    for rect in sorted(circles, key=lambda r: r.y0):
        cx, cy = (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2
        labels = [w for w in words if label_key(w[4]) in SKILLS
                  and rect.x1 - 1 <= w[0] < rect.x1 + 12
                  and abs((w[1] + w[3]) / 2 - cy) < 4]
        if len(labels) != 1:
            raise ValueError(f'Ambiguous label beside circle at {cx}, {cy}: {labels}')
        key = label_key(labels[0][4])
        if key in result:
            raise ValueError(f'Duplicate skill: {key}')
        dots = [d for d in drawings if d['fill'] is not None and max(d['fill']) < .35
                and len(d['items']) == 4 and 3 < d['rect'].width < 7
                and abs(d['rect'].width - d['rect'].height) < .5
                and abs((d['rect'].x0 + d['rect'].x1) / 2 - cx) < 1.2
                and abs((d['rect'].y0 + d['rect'].y1) / 2 - cy) < 1.2]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(4, 4),
                             clip=pymupdf.Rect(cx-1, cy-1, cx+1, cy+1),
                             colorspace=pymupdf.csGRAY, alpha=False)
        dark = sum(v < 100 for v in pix.samples) / len(pix.samples)
        if not (dark < .1 or dark > .9) or bool(dots) != (dark > .9):
            raise ValueError(f'Ambiguous dot for {key}: vector={bool(dots)}, dark={dark}')
        result[key] = {'trained': bool(dots), 'label': labels[0][4], 'darkFraction': dark}
    if set(result) != SKILLS:
        raise ValueError('Incomplete skill label mapping')
    return result


def main():
    """Audit first; apply only complete, unambiguous readings with archive backups."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'gemini-output/pdf-skill-review'
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for character_id, filename in SOURCES.items():
        entry = {'id': character_id, 'pdf': filename}
        try:
            with pymupdf.open(ROOT / 'Toconvert' / filename) as document:
                page = document[0]
                entry['skills'] = extract(page)
                page.get_pixmap(matrix=pymupdf.Matrix(3, 3),
                    clip=pymupdf.Rect(85, 200, 155, 459)).save(output / f'{character_id}.png')
            entry['trained'] = [key for key, value in entry['skills'].items() if value['trained']]
            if not entry['trained']:
                raise ValueError('No black dots found: requires manual confirmation')
            entry['status'] = 'verified'
        except (ValueError, OSError) as exc:
            entry['status'] = 'review_required'
            entry['error'] = str(exc)
        results.append(entry)
        print(character_id, entry['status'], entry.get('trained', entry.get('error')), flush=True)
    if args.apply:
        backup = ROOT / 'Final/Backups' / ('skills-' + datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ'))
        for entry in results:
            if entry['status'] != 'verified':
                continue
            def update(sheet):
                """Restore mastery flags and the two derived scores dependent on those flags."""
                assert sheet['id'] == entry['id']
                existing = any(s['trained'] for s in sheet['skills'].values() if isinstance(s, dict))
                assert not existing or all(sheet['skills'][k]['trained'] == v['trained'] for k, v in entry['skills'].items()), 'Sheet has different masteries: do not overwrite.'
                for key, value in entry['skills'].items():
                    sheet['skills'][key]['trained'] = value['trained']
                sheet['derived']['volonte'] = ((sheet['stats']['force'] - 10) // 2) * (2 if sheet['skills']['resilience']['trained'] else 1)
                sheet['derived']['perceptionPassive'] = 10 + ((sheet['stats']['esprit'] - 10) // 2) * (2 if sheet['skills']['perception']['trained'] else 1)
            rewrite(ROOT / 'Final' / f"{entry['id']}.zip", backup, update)
        print('Backups:', backup)
    (output / 'report.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()

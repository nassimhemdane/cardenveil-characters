"""Audit canonical sheets without changing their text, suits, costs or statistics."""

import json
import re
from pathlib import Path

from cardenveil.serialization import character_from_archive, character_to_dict

ROOT = Path(__file__).resolve().parents[1]
ENCODING = re.compile(r"\w\?\w|\ufffd|Ã[\u0080-\u00bf]|Â[\u0080-\u00bf]|â€")
MARKUP = re.compile(r"</?[A-Za-z][^>]*>|&(?:lt|gt|nbsp);|data-(?:start|end)=")


def scan(value, path=""):
    """Locate suspect strings while avoiding binary image references."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from scan(child, f"{path}.{key}".lstrip('.'))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from scan(child, f"{path}[{index}]")
    elif isinstance(value, str) and not value.startswith('data:'):
        for kind, pattern in [('encoding', ENCODING), ('markup', MARKUP)]:
            inspected = re.sub(r'https?://\S+', '', value) if kind == 'encoding' else value
            if pattern.search(inspected):
                yield {'kind': kind, 'path': path, 'text': value}


def main():
    """Generate evidence and full capability descriptions for human colour decisions."""
    entries = []
    for archive in sorted((ROOT / 'Final').glob('*.zip')):
        sheet = character_to_dict(character_from_archive(archive))
        entries.append({'archive': archive.name, 'name': sheet['identity']['nom'],
            'issues': list(scan(sheet)), 'stats': sheet['stats'], 'derived': sheet['derived'],
            'allSpades': bool(sheet['capacities']) and all(a['cost']['color'] == 'spade' for a in sheet['capacities']),
            'capacities': [{'name': a['name'], 'color': a['cost']['color'], 'value': a['value'], 'description': a['description']}
                           for a in sheet['capacities']]})
    metadata = json.loads((ROOT / 'web/catalog-metadata.json').read_text(encoding='utf-8'))
    metadata_issues = list(scan(metadata))
    summary = {'sheets': len(entries), 'encoding': sum(any(i['kind']=='encoding' for i in e['issues']) for e in entries),
               'markup': sum(any(i['kind']=='markup' for i in e['issues']) for e in entries),
               'allSpades': sum(e['allSpades'] for e in entries),
               'missingColors': sum(any(not a['color'] for a in e['capacities']) for e in entries)}
    report = ROOT / 'gemini-output/quality-audit'
    report.mkdir(parents=True, exist_ok=True)
    (report / 'audit.json').write_text(json.dumps({'summary': summary, 'metadataIssues': metadata_issues, 'characters': entries}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary))
    for entry in entries:
        if entry['issues']:
            print(entry['name'], json.dumps(entry['issues'][:2], ensure_ascii=False))
        if 'anain' in entry['name'].casefold():
            print('ANAIN:',json.dumps(entry,ensure_ascii=False))


if __name__ == '__main__':
    main()

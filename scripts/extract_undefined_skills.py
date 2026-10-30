"""Copy sheets with no recorded skill mastery into a separate review folder."""

import json
import shutil
from pathlib import Path

from cardenveil.serialization import character_from_archive, character_to_dict

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Keep Final untouched and export complete ZIP copies plus an explicit review manifest."""
    output = ROOT / 'gemini-output/competences-a-verifier'
    output.mkdir(parents=True, exist_ok=True)
    matches = []
    for archive in sorted((ROOT / 'Final').glob('*.zip')):
        sheet = character_to_dict(character_from_archive(archive))
        skills = [value for value in sheet['skills'].values() if isinstance(value, dict)]
        if skills and not any(value.get('trained') for value in skills):
            destination = output / archive.name
            if destination.exists() and destination.read_bytes() != archive.read_bytes():
                raise FileExistsError(f'Review copy already exists with different content: {destination}')
            if not destination.exists():
                shutil.copy2(archive, destination)
            matches.append({'name': sheet['identity']['nom'], 'archive': archive.name,
                'allBonusesEmptyOrZero': all(s.get('bonus') in (None, '', 0) for s in skills)})
    report = {'criterion': 'No skill has trained=true. This is a review signal, not proof of an extraction failure.',
              'count': len(matches), 'characters': matches}
    (output / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# Compétences à vérifier', '',
             'Aucune compétence maîtrisée enregistrée. Cela peut venir d’une extraction manquante ou du document source : à vérifier avant correction.', '',
             f'{len(matches)} copies complètes ; les originaux de Final sont inchangés.', '']
    lines.extend(f"- [{item['name']}]({item['archive']})" for item in matches)
    (output / 'README.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(f'{len(matches)} sheets copied to {output}')


if __name__ == '__main__':
    main()

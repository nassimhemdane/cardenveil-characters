"""Apply explicitly reviewed English rule edits after local draft generation."""
import hashlib
import json
from pathlib import Path
import re

from review_translations import raw_power

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'docs/rules/en'
CORRECTIONS = {
    'combat.md': {
        'Double your movement speed, allowing you a third movement during the round.':
            'Increase your movement speed by half, allowing you a third movement during the round.',
        'If you wield two Foci in one hand': 'If you wield two one-handed Foci',
        'an **weapon**': 'a **weapon**',
        'a NPC turn': 'an NPC turn',
        'retract, gain height, repositioning, etc.': 'retreat, gain height, reposition, etc.',
        '**Hideout**': '**Hide**',
        'an adverse creature': 'an opposing creature',
        'If you **miss** an attack against you': 'If an attack against you **misses**',
        '**Agility** (or **Strength** for shields/straight swords)': '**Agility Mod** (or **Strength Mod** for shields/straight swords)',
        '**Associated Attribute**: Strength / Agility / Spirit.': '**Associated Attribute Modifier**: Strength Mod / Agility Mod / Spirit Mod.',
        'uses Strength or Agility for attack and damage rolls.': 'uses Strength Mod or Agility Mod for attack and damage rolls.',
        'magical catalyst': 'magical Focus',
        'weapon or catalyst': 'weapon or Focus',
        'a **color** among': 'a **suit** among',
        'color bonus': 'suit bonus',
        '**Color Bonus**': '**Suit Bonus**',
        'corresponding color': 'corresponding suit',
        'its color': 'its suit',
        "Focus's color": "Focus's suit",
        '**colors**': '**suits**',
        '**Save Threshold**': '**Save DC**',
    },
}


def main():
    for path in DIRECTORY.glob('*.md'):
        text = path.read_text(encoding='utf-8')
        for before, after in CORRECTIONS.get(path.name, {}).items():
            text = text.replace(before, after)
        text = raw_power(text)
        text = re.sub(r'(?<=\d),(?=\d)', '.', text)
        path.write_text(text, encoding='utf-8')
    # These three modifier clarifications were reviewed in both languages.
    # Do not refresh any other fingerprint: unrelated source edits still fail the build.
    combat = (DIRECTORY / 'combat.md').read_text(encoding='utf-8')
    assert '**Agility Mod** (or **Strength Mod** for shields/straight swords)' in combat
    assert '**Associated Attribute Modifier**: Strength Mod / Agility Mod / Spirit Mod.' in combat
    assert 'uses Strength Mod or Agility Mod for attack and damage rolls.' in combat
    meta_path = DIRECTORY / 'sources.json'
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    current = hashlib.sha256((ROOT / 'docs/rules/fragmented/combat.md').read_text(encoding='utf-8').encode()).hexdigest()
    assert current == 'd0d4af4825be7ace1cccf77ba23040194ec08a3a74914766bf1717b8101c3ae6', 'French combat rules changed after editorial review'
    meta['combat.md'] = current
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()

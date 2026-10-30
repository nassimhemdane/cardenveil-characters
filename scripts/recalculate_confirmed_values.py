"""Migrate only the derived values whose formulas were confirmed by the user."""

import json
from datetime import UTC, datetime
from pathlib import Path

from apply_october_updates import rewrite

ROOT = Path(__file__).resolve().parents[1]


def apply_values(sheet):
    """Use displayed skill modifiers, not stale extracted bonus caches; leave Goldomus intact."""
    if sheet['id'] == 'goldomus':
        return
    stats = sheet['stats']
    resilience = (stats['force'] - 10) // 2
    if sheet['skills']['resilience']['trained']:
        resilience *= 2
    sheet['derived']['volonte'] = resilience
    # All current sheets have even Agility: this needs no additional rounding rule.
    assert stats['agilite'] % 2 == 0, 'Confirm the miss-threshold rounding for odd Agility.'
    sheet['derived']['seuilMiss'] = max(1, 1 - (stats['agilite'] - 10) // 2)
    sheet['derived']['canalisation'] = (stats['esprit'] - 10) // 2
    sheet['derived']['bonusAttaque'] = ''
    sheet['derived']['initiative'] = stats['agilite'] - 10
    sheet['derived']['mouvement'] = 5 + (stats['agilite'] + 1) // 2
    perception = (stats['esprit'] - 10) // 2
    if sheet['skills']['perception']['trained']:
        perception *= 2
    sheet['derived']['perceptionPassive'] = 10 + perception
    for stat in ('force', 'agilite', 'esprit', 'social'):
        sheet['resources']['tokens'][stat] = max(0, 1 + (stats[stat] - 10) // 2)


def main():
    """Back up changed archives and record exact before/after derived values."""
    backup = ROOT / 'Final/Backups' / ('derived-' + datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ'))
    changes = []
    for archive in sorted((ROOT / 'Final').glob('*.zip')):
        def update(sheet):
            """Keep all unconfirmed fields, costs, passives and current HP unchanged."""
            before = {'derived': dict(sheet['derived']), 'tokens': dict(sheet['resources']['tokens'])}
            apply_values(sheet)
            after = {'derived': dict(sheet['derived']), 'tokens': dict(sheet['resources']['tokens'])}
            if before != after:
                changes.append({'name': sheet['identity']['nom'], 'before': before, 'after': after})
        rewrite(archive, backup, update)
    backup.mkdir(parents=True, exist_ok=True)
    (backup / 'changes.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'{len(changes)} sheets updated; Goldomus excluded. Backup: {backup}')


if __name__ == '__main__':
    main()

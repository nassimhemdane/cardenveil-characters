"""Restore masteries supplied directly by the user when PDF circles are empty."""

import json
from datetime import UTC, datetime
from pathlib import Path

from apply_october_updates import rewrite

ROOT = Path(__file__).resolve().parents[1]
CONFIRMED = {
    'rousse': ['acrobaties', 'representation', 'persuasion', 'perception'],
    'tikoun': ['athletisme', 'resilience', 'investigation', 'perception', 'culture', 'arcanes'],
}


def main():
    """Apply confirmed flags and dependent values, preserving images and costs."""
    backup = ROOT / 'Final/Backups' / ('manual-skills-' + datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ'))
    for character_id, skills in CONFIRMED.items():
        def update(sheet):
            """Add only approved masteries; never clear another existing mastery."""
            assert sheet['id'] == character_id
            for key in skills:
                sheet['skills'][key]['trained'] = True
            sheet['derived']['volonte'] = ((sheet['stats']['force'] - 10) // 2) * (2 if sheet['skills']['resilience']['trained'] else 1)
            sheet['derived']['perceptionPassive'] = 10 + ((sheet['stats']['esprit'] - 10) // 2) * (2 if sheet['skills']['perception']['trained'] else 1)
        rewrite(ROOT / 'Final' / (character_id + '.zip'), backup, update)
    backup.mkdir(parents=True, exist_ok=True)
    (backup / 'confirmed.json').write_text(json.dumps(CONFIRMED, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Manual masteries applied; backups:', backup)


if __name__ == '__main__':
    main()

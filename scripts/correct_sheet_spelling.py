"""Repair explicit French spelling/OCR errors without rewriting game mechanics."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from apply_october_updates import rewrite

ROOT = Path(__file__).resolve().parents[1]
# Deliberately restricted to unambiguous errors; names and asset URLs are excluded.
CORRECTIONS = {
    'in igeant': 'infligeant', 'in igeants': 'infligeants', 'in ige': 'inflige',
    'iniges': 'infliges', 'e ectues': 'effectues', 'e ectue': 'effectue',
    'e et': 'effet', 'e ets': 'effets', 'dé agration': 'déflagration',
    'terri ant': 'terrifiant', 'térri ées': 'terrifiées', 'champ d’é et': 'champ d’effet',
    'En n': 'Enfin', 'dégats': 'dégâts', 'degats': 'dégâts',
    'dégat': 'dégât', 'degat': 'dégât', 'aggriper': 'agripper',
    'aggripée': 'agrippée', 'aggripées': 'agrippées',
    'aggripement': 'agrippement', 'cummulatif': 'cumulatif',
    'cummulative': 'cumulative', 'cummuler': 'cumuler', 'cummulatives': 'cumulatives',
    'cummulatifs': 'cumulatifs', 'commulatif': 'cumulatif',
    'supplémentaire': 'supplémentaire', 'supplementaires': 'supplémentaires',
    'supplementaire': 'supplémentaire', 'mélée': 'mêlée', 'mélées': 'mêlées',
    'confere': 'confère', 'desavantage': 'désavantage', 'enenmis': 'ennemis',
    'stennant': 'étourdissant', 'moité': 'moitié', 'impregnez': 'imprégnez',
    'augmantant': 'augmentant', 'augmante': 'augmente', 'augmantez': 'augmentez',
    'deplace': 'déplace', 'deplacer': 'déplacer', 'deplacez': 'déplacez',
    'deplacement': 'déplacement', 'contirbuent': 'contribuent', 'déja': 'déjà',
    'devstatrice': 'dévastatrice', 'atterir': 'atterrir', 'deven z': 'devenez',
    'devnz': 'devenez', 'Devenz': 'Devenez', 'protée': 'portée',
    'réacztion': 'réaction', 'jusqu’a': 'jusqu’à',
    'jsuqu’a': 'jusqu’à', 'jusuq’a': 'jusqu’à',
    'deuxime': 'deuxième', 'maintneir': 'maintenir', 'annimaux': 'animaux',
    'animéé': 'animée', 'inconsicent': 'inconscient', 'frêre': 'frère',
    'pér ruque': 'perruque', 'pérruque': 'perruque', 'maitre': 'maître',
    'Vétrinaire': 'Vétérinaire', 'malédiciton': 'malédiction', 'devnir': 'devenir',
    'initiatle': 'initiale', 'empechant': 'empêchant', 'gaillir': 'jaillir',
    'créatrure': 'créature', 'Comprennez': 'Comprenez', 'Intéragir': 'Interagir',
    'Dégats': 'Dégâts', 'Esrpit': 'Esprit', 'esrpit': 'esprit',
    'esprit': 'esprit', 'Eprit': 'Esprit', 'parocurs': 'parcours',
    'interompu': 'interrompu', 'possiblité': 'possibilité', 'fragements': 'fragments',
    'projettez': 'projetez', 'projettées': 'projetées', 'désavatage': 'désavantage',
    'aprées': 'après', 'en retours': 'en retour', 'en mélée': 'en mêlée',
    'autours de': 'autour de',
    'soignet': 'soignent', 'sbirent': 'sbires', 'cadavre répliquent': 'cadavres répliquent',
    'assouridssant': 'assourdissant', 'ennmi': 'ennemi', 'cadvares': 'cadavres',
    'cadvare': 'cadavre', 'jetter': 'jeter',
    'gravitiationelles': 'gravitationnelles', 'lours': 'lourds',
}
PATTERNS = [(re.compile(r'(?<!\w)' + re.escape(a) + r'(?!\w)'), b)
            for a, b in CORRECTIONS.items() if a != b]
SKIP = {'id', 'nom', 'name', 'image', 'portrait', 'createdAt', 'updatedAt', 'templateId', 'url'}


def repair(value, changes, path=''):
    """Correct words only, leaving proper names, links, field types and structure intact."""
    if isinstance(value, dict):
        return {k: v if k in SKIP else repair(v, changes, f'{path}.{k}') for k, v in value.items()}
    if isinstance(value, list):
        return [repair(v, changes, f'{path}[{i}]') for i, v in enumerate(value)]
    if not isinstance(value, str) or '://' in value or value.startswith('data:'):
        return value
    original = value
    for pattern, replacement in PATTERNS:
        value = pattern.sub(replacement, value)
    if value != original:
        changes.append({'field': path, 'before': original, 'after': value})
    return value


def main():
    """Back up changed archives and retain an exact before/after editorial report."""
    backup = ROOT / 'Final/Backups' / ('spelling-' + datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ'))
    report = {}
    metadata_path = ROOT / 'web/catalog-metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    for archive in sorted((ROOT / 'Final').glob('*.zip')):
        changes = []
        def update(sheet):
            """Replace corrected strings on a validated copy, never numerical fields."""
            corrected = repair(sheet, changes)
            sheet.clear()
            sheet.update(corrected)
        if rewrite(archive, backup, update):
            report[archive.name] = changes
    metadata_changes = []
    corrected = repair(metadata, metadata_changes)
    if metadata_changes:
        backup.mkdir(parents=True, exist_ok=True)
        (backup / 'catalog-metadata.before.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        metadata_path.write_text(json.dumps(corrected, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        report['catalog-metadata.json'] = metadata_changes
    backup.mkdir(parents=True, exist_ok=True)
    (backup / 'corrections.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'{len(report)} files corrected; {sum(len(v) for v in report.values())} text fields; {backup}')


if __name__ == '__main__':
    main()

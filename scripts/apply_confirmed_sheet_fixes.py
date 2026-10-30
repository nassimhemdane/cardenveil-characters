"""Apply only user-confirmed HP, Anain suits and catalogue text corrections."""

import json
from datetime import UTC, datetime
from pathlib import Path

from apply_october_updates import rewrite

ROOT = Path(__file__).resolve().parents[1]
ANAIN = ['diamond', 'spade', 'club', 'heart', 'heart', 'club', 'diamond', 'spade']
CASPIAN = ['diamond', 'heart', 'club', 'spade', 'club', 'heart', 'club']
ESTERELLE = ['diamond', 'diamond', 'heart', 'heart', 'club', 'club', 'spade', 'spade']
GADOLIA = ['diamond', 'diamond', 'diamond', 'club', 'spade', 'spade', 'heart', 'heart', 'heart']
JEAN_LOUIS = ['diamond', 'diamond', 'spade', 'club', 'heart', 'heart']
LINRAJ = ['diamond', 'diamond', 'spade', 'spade', 'heart', 'heart', 'club']
NOEGWANG = ['diamond', 'diamond', 'diamond', 'heart', 'heart', 'spade', 'club', 'club']
THELONIUS = ['diamond', 'diamond', 'heart', 'heart', 'heart', 'club', 'club', 'spade', 'spade']
BAURGALMIR = ['diamond', 'diamond', 'spade', 'heart', 'heart', 'heart', 'club', 'club', 'club']


def main():
    """Preserve all costs, current HP and images; back up each modified archive."""
    backup = ROOT / 'Final/Backups' / ('confirmed-' + datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ'))
    path = ROOT / 'web/catalog-metadata.json'
    metadata = json.loads(path.read_text(encoding='utf-8'))
    entry = metadata['characters']['baurgalmir-volmerkekya']
    entry['loreSummary'] = 'Baurgalmir Volmerkekya est un vétérinaire humain qui cherche à lever sa malédiction démoniaque pour retrouver sa tribu et voir grandir ses petits-enfants.'
    entry['gameplaySummary'] = 'Accompagné de son hibou, il combine invocations animales, contrôle, réactions défensives et capacités aléatoires ou exigeant un sacrifice de points de vie.'
    changes = []
    for archive in sorted((ROOT / 'Final').glob('*.zip')):
        def update(sheet):
            """Update the explicit maximum-HP rule and approved colours only."""
            if sheet['id'] == 'goldomus':
                return
            before = sheet['derived']['pvMax']
            after = 60 + 5 * sheet['stats']['force']
            sheet['derived']['pvMax'] = after
            if sheet['id'] == 'anain-proviste':
                assert len(sheet['capacities']) == len(ANAIN)
                for ability, suit in zip(sheet['capacities'], ANAIN, strict=True):
                    ability['cost']['color'] = suit
            if sheet['id'] == 'caspian':
                assert [a['name'] for a in sheet['capacities']] == [
                    'Mirage waltz', 'Mirage focus', 'Mirage Madness', 'Mirage step',
                    'Sirens’s whisper', 'Mirage refraction', 'Sirens’s charm',
                ]
                for ability, suit in zip(sheet['capacities'], CASPIAN, strict=True):
                    ability['cost']['color'] = suit
            if sheet['id'] == 'esterelle':
                assert [a['name'] for a in sheet['capacities']] == [
                    'Insectocalypse', 'Ruéclair', 'Esquiflore', 'Polleniarol',
                    'Pétalidrift', 'Étreinte boisée', 'Mandragouffre', 'Dards à toi',
                ]
                for ability, suit in zip(sheet['capacities'], ESTERELLE, strict=True):
                    ability['cost']['color'] = suit
            if sheet['id'] == 'gadolia':
                assert [a['name'] for a in sheet['capacities']] == [
                    'Fudohast', 'Blahkurst', 'Rhomnoss', 'Stahsk', 'Liao',
                    'Ô’krim', 'Blïms', 'Éxswip', 'Nèdôrim',
                ]
                for ability, suit in zip(sheet['capacities'], GADOLIA, strict=True):
                    ability['cost']['color'] = suit
            if sheet['id'] == 'jean-louis':
                assert [a['name'] for a in sheet['capacities']] == [
                    'Racquette', 'Kinnaping', 'TP', 'On m’appelle l’ovni', 'Akha', 'La Darone',
                ]
                for ability, suit in zip(sheet['capacities'], JEAN_LOUIS, strict=True):
                    ability['cost']['color'] = suit
            if sheet['id'] == 'linraj':
                assert [a['name'] for a in sheet['capacities']] == [
                    'Croc et Lame', 'Danse du Croc Blanc', 'Ombre du Flanc',
                    'Chasseur Vertical', 'Tempête élémentaire', 'L’Œil du Chasseur', 'Lame Hurlante',
                ]
                for ability, suit in zip(sheet['capacities'], LINRAJ, strict=True):
                    ability['cost']['color'] = suit
            if sheet['id'] == 'noegwang-ryong':
                assert [a['name'] for a in sheet['capacities']] == [
                    'Frappe du Vortex', 'Triptyque foudroyant', 'Dragonstrike',
                    'Garde fulminante', 'Cuirasse du moine', 'Pas fulgurant',
                    'Impact céleste', 'Champ de rupture',
                ]
                for ability, suit in zip(sheet['capacities'], NOEGWANG, strict=True):
                    ability['cost']['color'] = suit
            if sheet['id'] == 'thelonius':
                assert [a['name'] for a in sheet['capacities']] == [
                    'Dissonance cognitive', 'Pogo', 'Musicothérapie', "Sonnerie d'alerte",
                    'Chant du Cygne', 'Cacophonie', 'Soufflante', 'Slam', 'Danse fusionnelle',
                ]
                for ability, suit in zip(sheet['capacities'], THELONIUS, strict=True):
                    ability['cost']['color'] = suit
            if sheet['id'] == 'baurgalmir-volmerkekya':
                assert [a['name'] for a in sheet['capacities']] == [
                    'Bristlehunter', 'Orbbelly', 'Shadowpunch', 'Bluntback', 'Bronzeforce',
                    'Doomchew', 'Moltenmight', 'Hellstrength', 'Shadehunter',
                ]
                for ability, suit in zip(sheet['capacities'], BAURGALMIR, strict=True):
                    ability['cost']['color'] = suit
            if before != after:
                changes.append({'name': sheet['identity']['nom'], 'oldMaxHP': before, 'newMaxHP': after})
        assets = {}
        if archive.name == 'baurgalmir-volmerkekya.zip':
            assets['metadata.json'] = json.dumps(entry, ensure_ascii=False, indent=2).encode('utf-8')
        rewrite(archive, backup, update, assets=assets)
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    backup.mkdir(parents=True, exist_ok=True)
    (backup / 'hp-changes.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'{len(changes)} HP maxima changed; backup: {backup}')


if __name__ == '__main__':
    main()

"""Apply the author's November 8 rulings, with an exact before/after ledger."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / 'docs/rules/fragmented'
CHANGES = {
    'systeme-de-base.md': [
        ('**1d20 + la Force**', '**1d20 + le Mod. Force**'),
        ('**1d8 + l’Esprit**', '**1d8 + le Mod. Esprit**'),
    ],
    'capacites.md': [
        ('valeur cumulée dépasse le **coût de la capacité**', 'valeur cumulée atteint au moins le **coût de la capacité**'),
        ('Le seuil à dépasser pour que les adversaires esquivent vos capacités:', 'Le seuil à atteindre ou dépasser (résultat ≥ seuil) pour que les adversaires esquivent vos capacités :'),
        ('**Nombre de tokens disponibles = Modificateur de la caractéristique associée.**', '**Nombre de tokens disponibles = max(0, 1 + modificateur de la caractéristique associée).**'),
        ('**Valeur = K × Mod × d6**', '**Valeur = K × somme de Mod dés à six faces (Mod d6).**'),
        ('égale à **Mod contextuel D6**', 'égale à **Mod contextuel d6 (somme de Mod dés à six faces)**'),
    ],
    'combat.md': [
        ('• 1 tour = jusqu’à la fin du prochain round global.', '• 1 round = jusqu’à la fin du prochain round global.'),
        ('• 2 tours = jusqu’à la fin du round +2, etc.', '• 2 rounds = jusqu’à la fin du round +2, etc.'),
        ('(durée 1 tour)', '(durée 1 round)'),
        ('Ligne droite de 30 m de longueur', 'Ligne droite de 18 m de longueur'),
        ('**repousser de 4m**', '**repousser de 5 m**'),
        ('être repoussée de 3 m', 'être repoussée de 5 m'),
        ('+ votre **agilité** (ou **force** pour les boucliers/épées droites)', '+ votre **Mod. Agilité** (ou **Mod. Force** pour les boucliers/épées droites)'),
        ('**Caractéristique associée** : Force / Agilité / Esprit.', '**Modificateur de la caractéristique associée** : Mod. Force / Mod. Agilité / Mod. Esprit.'),
        ('utilise Force ou Agilité pour les jets d’attaque et de dégâts.', 'utilise le Mod. Force ou le Mod. Agilité pour les jets d’attaque et de dégâts.'),
    ],
}


def main():
    ledger = []
    for name, replacements in CHANGES.items():
        path = RULES / name
        source = path.read_text(encoding='utf-8')
        for before, after in replacements:
            if before not in source:
                if after in source:
                    continue
                raise ValueError(f'Missing expected passage: {name}: {before}')
            ledger.append({'file': str(path.relative_to(ROOT)), 'before': before, 'after': after, 'occurrences': source.count(before)})
            source = source.replace(before, after)
        path.write_text(source, encoding='utf-8', newline='\n')
    manifest_path = RULES / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for doc in manifest['documents'].values():
        doc['sha256'] = hashlib.sha256((RULES / doc['file']).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if ledger:
        ledger_path = ROOT / 'docs/translation-rulings-2026-11-08.json'
        previous = json.loads(ledger_path.read_text(encoding='utf-8')) if ledger_path.exists() else []
        ledger_path.write_text(json.dumps(previous + ledger, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(ledger)} traced corrections')


if __name__ == '__main__':
    main()

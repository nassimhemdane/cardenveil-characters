# Guide développeur — Grumpy

Ce document montre comment intégrer `cardenveil-core` dans une application Python. Le core fournit
le modèle canonique des personnages, la sérialisation JSON/ZIP, une validation non destructive et
une persistance locale. Il ne fournit pas d'API HTTP, d'interface graphique ni de moteur de combat.

## Installation

Le projet demande Python 3.11 ou plus récent. Depuis la racine du dépôt :

```bash
python -m venv .venv
```

Sous Windows :

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Sous Linux ou macOS :

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

L'installation éditable rend le package `cardenveil` importable tout en utilisant directement le
code source local.

## Créer un personnage

`Character` est la fiche complète. Chaque sous-objet correspond à une section du fichier
`*.rpsheet.json`.

```python
from cardenveil import Character
from cardenveil.domain import (
    SheetIdentity,
    SheetProgression,
    SheetStats,
    SheetWeapon,
)

character = Character(
    id="grumpy-hero",  # identifiant stable : lettres, chiffres, - et _
    identity=SheetIdentity(
        nom="Grumpy",
        joueur="Développeur",
        niveau=1,
        race="Humain",
        alignement="Neutre Bon",
    ),
    stats=SheetStats(force=14, agilite=12, esprit=16, social=10),
    progression=SheetProgression(xpDepenses=0, xpDisponibles=5),
    weapons=[SheetWeapon(nom="Épée longue", de="1d8", notes="Polyvalente")],
)
```

Les quatre statistiques totalisent ici 52, la valeur de création standard. Le modèle préserve les
champs vides et les valeurs calculées déjà enregistrées : il ne modifie pas silencieusement une
fiche chargée.

## Valider la fiche

La validation retourne des diagnostics structurés. Une fiche importée ou évoluée peut être valide
tout en produisant un avertissement.

```python
from cardenveil.validation import validate_character

result = validate_character(character)
if not result.is_valid:
    for issue in result.issues:
        print(issue.severity, issue.path, issue.message)
```

## Convertir en JSON et recharger

```python
from cardenveil.serialization import character_from_json, character_to_json

json_text = character_to_json(character)
restored = character_from_json(json_text)
assert restored == character
```

Le décodeur est strict : une clé inconnue est rejetée au lieu d'être perdue. Cette propriété permet
de détecter rapidement une incompatibilité de schéma.

## Sauvegarder plusieurs personnages

```python
from cardenveil import CardenveilCore, FileCharacterRepository

core = CardenveilCore(FileCharacterRepository("characters"))
saved_path = core.save_character(character)
same_character = core.load_character("grumpy-hero")
all_characters = core.load_all_characters()
```

Le dépôt écrit un fichier `characters/<id>.rpsheet.json` de manière atomique. L'identifiant doit
rester simple et sûr pour être utilisé comme nom de fichier.

## Exporter et importer une archive ZIP

```python
from cardenveil.serialization import character_from_archive, character_to_archive

character_to_archive(character, "exports/grumpy-hero.zip")
restored = character_from_archive("exports/grumpy-hero.zip")
assert restored == character
```

Si la fiche référence des images sous `/assets/grumpy-hero/...`, passez à
`character_to_archive` le dossier parent via `asset_root`. Chaque image référencée doit exister ;
l'export échoue volontairement si un asset manque.

## Calculs de règles disponibles

Seules les règles non ambiguës sont exposées comme fonctions pures :

```python
from cardenveil.rules.derived import modifier

assert modifier(16) == 3
```

Les valeurs `derived` de la fiche sont persistées telles quelles et ne sont pas recalculées au
chargement.

## Lancer les tests Grumpy

```bash
python -m pytest tests/grumpy -v
```

Pour exécuter toute la suite hors intégrations Gemini :

```bash
python -m pytest -m "not integration"
python -m ruff check .
```

Les tests dans `tests/grumpy/` sont volontairement courts : ils peuvent être copiés comme exemples
d'intégration. Pour une fiche remplissant toutes les sections du schéma, consulter également
`examples/complete_character_cli.py` et `tests/test_complete_character.py`.


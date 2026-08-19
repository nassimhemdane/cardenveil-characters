# cardenveil-core

`cardenveil-core` est la source de vérité logicielle du domaine Cardenveil. Son format persistant
par défaut est le JSON `*.rpsheet.json` observé dans les archives de référence. `Character` possède
un mapping 1:1 avec ce document et préserve les chaînes HTML, valeurs vides et types existants.

Elle n'est ni une API web, ni un parseur PDF, ni un moteur de combat, ni un framework LLM. Ces
applications doivent dépendre du core; le core ne dépend d'aucune d'elles.

## Installation et qualité

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

Python 3.11 ou plus récent est requis. La bibliothèque n'a aucune dépendance runtime.

## Exemple minimal

```python
from cardenveil import Character
from cardenveil.domain import SheetIdentity, SheetStats

mimyr = Character(
    id="mimyr",
    identity=SheetIdentity(nom="Mimyr", race="Aasimar", alignement="Chaotique Bon"),
    stats=SheetStats(force=16, agilite=8, esprit=16, social=6),
)
print(mimyr.stats.force)
```

## Architecture et principes

- `domain/sheet.py`: dataclasses correspondant exactement aux objets JSON de la fiche.
- `content/`: définitions officielles validées et catalogues typés; le contenu custom utilise les
  mêmes modèles et n'a pas besoin d'être inscrit dans ces catalogues.
- `rules/`: règles naturelles atomiques et sourcées; seules les règles claires deviennent des
  fonctions pures dans `derived.py`.
- `serialization/`: mapping strict du JSON `rpsheet`; toute clé inconnue est rejetée.
- `persistence.py`: dépôt de fichiers JSON et façade `CardenveilCore`.
- `validation.py`: diagnostics structurés, distincts des invariants de construction.

Les valeurs dérivées présentes dans le format sont persistées sans recalcul afin de garantir un
roundtrip exact. Le runtime de combat reste hors scope.

```python
from cardenveil.serialization import character_from_json, character_to_json

payload = character_to_json(mimyr)
restored = character_from_json(payload)
assert restored == mimyr
```

## Rulebook et contenu custom

```python
from cardenveil.content import RACES, WEAPONS
from cardenveil.rules import rules

aasimar = RACES.get("aasimar")
modifier_rule = rules.get("character.stats.modifier")
longsword = WEAPONS.get("longsword")
```

## Persistance et scénario complet

```python
from cardenveil import CardenveilCore, FileCharacterRepository

core = CardenveilCore(FileCharacterRepository("characters"))
core.save_character(mimyr)
loaded = core.load_character("mimyr")
all_characters = core.load_all_characters()
```

Le scénario commenté remplissant toutes les sections est exécutable avec :

```bash
py -3.11 examples/complete_character_cli.py --output demo-complet.rpsheet.json
```

## Import PDF multimodal avec Gemini

Le domaine pur reste utilisable sans Gemini. Installez seulement l'extra nécessaire :

```bash
py -3.11 -m pip install -e ".[pdf-gemini]"
```

Copiez `.env.example` vers `.env`, puis renseignez uniquement la clé :

```dotenv
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_MEDIA_RESOLUTION=MEDIA_RESOLUTION_HIGH
```

`.env` est ignoré par Git. Le modèle reste configurable et n'est pas dispersé dans le code.

```python
from cardenveil.importers.pdf import (
    CharacterPDFImporter,
    GeminiCharacterDocumentExtractor,
)

extractor = GeminiCharacterDocumentExtractor.from_env()
importer = CharacterPDFImporter(extractor)
character = importer.load("References/Pdf/Aurore.pdf")
print(character)
```

Gemini reçoit le PDF complet comme document multimodal et doit respecter le JSON Schema Pydantic
d'`ExtractedCharacter`. Le mapper produit ensuite le véritable `CharacterSheet`; aucune méthode
`from_pdf()` n'est ajoutée au domaine.

Architecture, responsabilités et limites : [docs/pdf-import.md](docs/pdf-import.md).

## Première passe : archives existantes sans Gemini

Le script séparé normalise tous les ZIP de `Toconvert` vers `Final`, fait passer chaque JSON par le
modèle strict `Character`, renomme depuis le nom du personnage, externalise les anciennes images
base64 et recompresse tous les assets :

```powershell
py -3.11 scripts/convert_character_archives.py
```

Les personnages déjà présents sont ignorés. L'écrasement est explicite :

```powershell
py -3.11 scripts/convert_character_archives.py --overwrite
```

Documentation complète : [docs/archive-normalization.md](docs/archive-normalization.md).

## Deuxième passe : PDF, candidats et incohérences

La passe Gemini place les conversions dans `Final/Candidates` sans modifier les ZIP déjà présents
dans `Final`. Le matching utilise `identity.nom`, jamais le nom du fichier :

```powershell
py -3.11 -X utf8 scripts/analyze_pdf_inconsistencies.py
```

Après avoir coché les choix A/B dans `Final/INCOHERENCES.md`, les décisions sont appliquées avec
sauvegarde automatique :

```powershell
py -3.11 -X utf8 scripts/fix_inconsistencies.py
```

Documentation complète : [docs/pdf-reconciliation.md](docs/pdf-reconciliation.md).

Tests offline :

```bash
py -3.11 -m pytest -m "not integration"
```

Test réel Gemini, volontairement opt-in pour ne jamais consommer de quota par accident :

```bash
set CARDENVEIL_RUN_GEMINI_INTEGRATION=1
py -3.11 -m pytest tests/test_pdf_gemini_integration.py -m integration -s
```

Conversion des quatre PDF de référence pour évaluation manuelle :

```powershell
$env:CARDENVEIL_RUN_GEMINI_INTEGRATION = "1"
py -3.11 -m pytest tests/test_pdf_gemini_all_examples.py -m integration -s -rs
```

Les résultats sont conservés dans `gemini-output/`. Les images compressées sont écrites dans
`gemini-output/assets/{character-id}/` et leurs chemins `/assets/...` sont directement injectés dans
le JSON final. Une archive `{character-id}.zip`, contenant le `.rpsheet.json` et son dossier
d'assets, est créée directement pour chaque personnage. Les JSON de debug intermédiaires restent
disponibles dans leur sous-dossier. `gemini-output/` est ignoré par Git.

Les catalogues officiels sont des valeurs par défaut, pas une liste d'autorisation. Une race, une
capacité, un feat, un totem ou une arme custom reçoit simplement son propre `ContentId` stable.

## Roadmap

- compléter le corpus officiel après arbitrage des versions de règles;
- fournir des migrations lorsqu'un schéma V2 existe réellement;
- ajouter les opérations applicatives explicites autour de `Character`;
- stabiliser les calculs dérivés restants;
- ajouter plus tard runtime et résolution;
- exposer les mêmes IDs aux adaptateurs PDF, API, MCP, RAG et ontologie externes.

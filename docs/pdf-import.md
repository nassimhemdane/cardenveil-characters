# Import PDF de personnages

## Architecture

```text
PDF visuel
  → CharacterDocumentExtractor (Protocol)
  → ExtractedCharacter (Pydantic, données observables uniquement)
  → CharacterMapper
  → CharacterSheet (alias du Character canonique rpsheet)
  → PDFImageAssetExtractor (optionnel, traitement local sans LLM)
```

`CharacterPDFImporter` orchestre les étapes et ne connaît aucun SDK. Le provider Gemini est une
implémentation interchangeable de `CharacterDocumentExtractor`. Un futur provider local devra
retourner le même `ExtractedCharacter`; aucun changement du mapper ou du domaine ne sera nécessaire.

## Images et compression

`PDFImageAssetExtractor` lit directement les objets images embarqués dans le PDF, sans nouvel appel
Gemini. Il reconnaît le portrait et le totem de la première page, puis les illustrations de capacités
de la seconde page dans leur ordre visuel. Les références injectées suivent exactement les archives :

```text
/assets/{character-id}/portrait.png
/assets/{character-id}/totem.png
/assets/{character-id}/capacity-1.png
```

Les images restent en PNG pour respecter ce contrat. Elles sont redimensionnées à 512 px pour le
portrait, 384 px pour les autres assets, quantifiées sur une palette de 128 couleurs, puis enregistrées
avec le niveau de compression PNG maximal. Sur la fiche Edmound, les 11 images passent d'environ
9,2 Mo embarqués à moins de 1 Mo au total.

## Archive finale

`CharacterPDFImporter.load_to_archive()` produit directement l'archive d'échange nommée d'après
l'ID du personnage :

```text
edmound.zip
├── edmound.rpsheet.json
└── assets/
    └── edmound/
        ├── portrait.png
        ├── totem.png
        └── capacity-1.png
```

L'écriture est atomique et chaque chemin d'image non vide du JSON est vérifié avant la création du
ZIP. `character_to_archive()` expose aussi cette opération indépendamment de l'import PDF.

## Choix Gemini V1

Le modèle par défaut est `gemini-3.1-flash-lite`, configurable par `GEMINI_MODEL`. La documentation
officielle montre qu'il accepte les PDF multimodaux et les sorties structurées JSON Schema. Le
provider utilise le SDK officiel `google-genai`, la Files API et le schéma Pydantic de
`ExtractedCharacter`.

Sources techniques consultées :

- <https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite>
- <https://ai.google.dev/gemini-api/docs/generate-content/document-processing>
- <https://ai.google.dev/gemini-api/docs/structured-output>

## Responsabilités

- Gemini lit sémantiquement toutes les pages; il ne crée ni ID, timestamp, image ou valeur absente.
- Pydantic refuse les clés supplémentaires, enums invalides et scores hors bornes.
- Le mapper génère seulement les champs techniques requis et traduit `None` vers les valeurs vides
  imposées par le format `rpsheet`.
- Les valeurs dérivées ne sont jamais recalculées; elles sont copiées seulement si visibles.
- L'extraction future des images appartiendra à un composant d'assets distinct.

## Dataset

Quatre PDF se trouvent dans `References/Pdf` et six archives dans `References/Expected`. Leurs noms
ne définissent pas de couples directs. Aucun benchmark d'exactitude PDF↔expected n'est donc inventé
pour le moment; une table de correspondance devra être fournie.

## Debug

Passer `debug_directory="debug"` à `CharacterPDFImporter` produit :

```text
debug/extracted_character.json
debug/character_sheet.json
```

Ces fichiers permettent de distinguer une erreur d'extraction d'une erreur de mapping.

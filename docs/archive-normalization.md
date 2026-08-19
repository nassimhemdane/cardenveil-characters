# Normalisation des archives existantes

La première passe traite uniquement les ZIP déjà présents dans `Toconvert`. Elle n'utilise ni
Gemini ni un autre service réseau.

Pour chaque archive, le script :

1. lit l'unique `*.rpsheet.json` du ZIP ;
2. le désérialise strictement en `Character` avec `cardenveil-core` ;
3. génère l'ID et le nom du ZIP depuis `identity.nom` ;
4. extrait les images externes ou les anciennes images base64 ;
5. redimensionne et compresse chaque image en PNG ;
6. met à jour les chemins `/assets/{character-id}/...` ;
7. resérialise le `Character` avec le format canonique ;
8. écrit atomiquement `Final/{character-id}.zip`.

Exécution normale, idempotente :

```powershell
py -3.11 scripts/convert_character_archives.py
```

Une archive déjà présente dans `Final` est signalée comme `SKIPPED`. Pour la reconstruire :

```powershell
py -3.11 scripts/convert_character_archives.py --overwrite
```

Les dossiers peuvent être remplacés :

```powershell
py -3.11 scripts/convert_character_archives.py --source Toconvert --output Final
```

Le script continue après une archive invalide, affiche chaque erreur et retourne un code non nul si
au moins une conversion échoue.

# Réconciliation des PDF

Ce workflow traite les PDF de `Toconvert` sans écraser les archives existantes de `Final`.
L'identité d'un personnage vient exclusivement de `identity.nom`, puis est normalisée avec la même
fonction que le core. Le nom du PDF et celui du ZIP ne participent pas au rapprochement.

## 1. Analyse sans modification de Final

```powershell
py -3.11 -X utf8 scripts/analyze_pdf_inconsistencies.py
```

Pour chaque PDF, le script :

1. envoie le document complet à Gemini ;
2. valide la réponse structurée ;
3. passe le résultat par `CharacterMapper` puis par la sérialisation stricte du core ;
4. extrait et compresse les images ;
5. écrit une archive temporaire dans `Final/Candidates` ;
6. compare les données réellement extraites avec une éventuelle archive portant le même nom de
   personnage ;
7. régénère `Final/INCOHERENCES.md`.

Le script refuse d'écraser un rapport existant afin de protéger les cases déjà cochées. Les options
explicites sont :

```powershell
# Petit essai limitant le quota
py -3.11 -X utf8 scripts/analyze_pdf_inconsistencies.py --limit 1

# Régénération volontaire des candidats et du rapport
py -3.11 -X utf8 scripts/analyze_pdf_inconsistencies.py `
  --overwrite-candidates --overwrite-report
```

`--timeout` borne chaque requête réseau et `--max-attempts` contrôle les nouvelles tentatives. La
valeur par défaut d'une seule tentative évite qu'une série consomme plusieurs fois le quota.

## 2. Choix dans le rapport

Chaque incohérence possède exactement deux cases :

```markdown
- [ ] A — conserver la valeur actuelle
- [ ] B — appliquer la valeur extraite du PDF
```

Remplacer `[ ]` par `[x]` pour sélectionner un choix. Une seule case peut être cochée par bloc.
Les deux cases vides signifient « décision reportée ». Il ne faut pas modifier le commentaire
`CARDENVEIL_ISSUE`, qui contient les données machine nécessaires au correcteur.

Les avertissements placés à la fin du document signalent une lecture incertaine sans deux valeurs
fiables. Ils restent documentaires : le système ne fabrique pas une correction que le PDF ne
permet pas de justifier.

## 3. Application contrôlée

```powershell
py -3.11 -X utf8 scripts/fix_inconsistencies.py
```

Pour considérer automatiquement toute décision vide comme le choix A :

```powershell
py -3.11 -X utf8 scripts/fix_inconsistencies.py --default-a
```

Le correcteur :

- refuse tout bloc où A et B sont cochés ensemble ;
- ignore les décisions laissées vides ;
- ou les interprète comme A lorsque `--default-a` est fourni ;
- applique uniquement les choix cochés ;
- repasse chaque JSON modifié dans `character_from_dict` avant de remplacer son archive ;
- conserve tous les assets du ZIP ;
- sauvegarde toute archive finale modifiée dans `Final/Backups` ;
- refuse d'écraser un nouveau fichier apparu depuis l'analyse, sauf avec `--overwrite-new`.

Une correction invalide pour le schéma arrête l'opération. Le fichier temporaire est supprimé et
l'archive d'origine reste disponible.

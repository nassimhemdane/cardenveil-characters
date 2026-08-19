# Site Cardenveil

Le site est statique. Ses données sont générées depuis les archives canoniques de `Final/` avec
le parseur officiel de `cardenveil-core`.

```powershell
web\site.cmd build
web\site.cmd preview
```

Ouvrir ensuite `http://localhost:8000/`.

Les champs éditoriaux du catalogue vivent dans `web/catalog-metadata.json`. Initialiser les entrées,
les valider, puis les recopier dans un `metadata.json` interne à chaque archive :

```powershell
py web/metadata.py init
py web/metadata.py validate
py web/metadata.py sync
py web/build.py
```

Tous les champs sont facultatifs :

```json
{
  "mimyr": {
    "difficulty": 3.5,
    "class": ["Mage", "Invocateur"],
    "creator": "",
    "loreSummary": "Résumé éditorial validé.",
    "gameplaySummary": "Résumé de gameplay validé."
  }
}
```

`difficulty` accepte les valeurs de 0,5 à 5 par pas de 0,5. Chaque classe doit appartenir au lexique
global `classVocabulary`; plusieurs classes sont permises. Le générateur n'invente aucune valeur
manquante. Seule la commande
explicite `metadata.py sync` modifie les archives pour y inclure leur copie de `metadata.json`.

## Routine de mise à jour

1. Ajouter, remplacer ou retirer les archives dans `Final/`.
2. Exécuter `web\site.cmd build` pour créer les nouvelles entrées de métadonnées et reconstruire
   le site.
3. Modifier les champs éditoriaux dans `web/catalog-metadata.json`.
4. Relancer `web\site.cmd check`.
5. Commit et push : Cloudflare Pages redéploie automatiquement le site.

La commande `preview` lance également une prévisualisation sur `http://127.0.0.1:8000`.

## Cloudflare Pages

Relier le dépôt Git au projet Pages avec cette configuration :

```text
Commande de build : sh web/cloudflare-build.sh
Dossier de sortie : web/public
Répertoire racine : laisser vide
```

Le site est entièrement statique : les archives et images sont intégrées au déploiement. Aucun
serveur applicatif ni secret n'est nécessaire pour cette première version.

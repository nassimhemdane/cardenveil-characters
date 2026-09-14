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

## Pages HTML par personnage

Le build génère `/personnages/<identifiant>/` et un index `/personnages/`.
Ces pages contiennent les données complètes de la fiche dans leur HTML, sans nécessiter
JavaScript ni appel réseau. Avec JavaScript, le rendu interactif habituel utilise une copie
embarquée du même payload, générée dans la même passe que le catalogue.
Les cartes du catalogue pointent vers ces URL ; les anciens liens `?character=...` restent
compatibles, mais les nouveaux liens sont à privilégier pour partager une fiche.
Les sorties `web/public/personnages/` sont régénérables et ignorées par Git.
Cela facilite la lecture par les robots, sans garantir leur accès ni leur indexation.

## Déploiement Cloudflare Pages

Relier le dépôt Git au projet Pages avec cette configuration :

```text
Commande de build : sh web/cloudflare-build.sh
Dossier de sortie : web/public
Répertoire racine : laisser vide
```

Le site est entièrement statique : les archives et images sont intégrées au déploiement. Aucun
serveur applicatif ni secret n'est nécessaire pour cette première version.

## Fiches HTML A4 imprimables

Le bouton « Fiche A4 / Imprimer » ouvre `print.html?character=<identifiant>`. Cette vue en lecture
seule affiche des feuilles blanches de 210 × 297 mm, avec portrait, caractéristiques, combat,
narratif, totem pleine largeur et capacités illustrées sur deux colonnes. L'équipement et
l'inventaire, lorsqu'ils sont renseignés, occupent la troisième feuille ; les continuations
éventuelles suivent. Les métadonnées éditoriales ne sont pas imprimées.

La pagination attend les images et les polices, mesure les blocs et conserve le texte riche
lors des continuations. La police principale est de 9 pt ; 8,5 pt est utilisé uniquement si cela
économise une page. Les fiches très chargées peuvent utiliser une quatrième feuille. Aucun texte
n'est masqué pour imposer cette limite : de futures fiches exceptionnellement longues pourront
nécessiter davantage de pages.

Le navigateur assure l'impression et l'enregistrement PDF : sélectionner A4, échelle 100 % et
désactiver ses en-têtes/pieds de page. Les navigateurs Chromium sont utilisés pour la validation.
Le build du site ne produit plus de fichiers PDF et ne nécessite plus les dépendances PDF.
L'ancien exporteur Python reste disponible pour les consommateurs existants du core.

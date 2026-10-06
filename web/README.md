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

## Bibliothèque des règles

`/regles/` suit un parcours : comprendre le jeu, créer et faire évoluer un personnage,
jouer une partie, consulter les aides de jeu puis les références et versions.
Le menu, les chapitres et leurs sommaires fonctionnent sans JavaScript ; la recherche locale
utilise un index généré au build. Le contenu public est limité explicitement dans
`web/rules_pages.py` : les documents techniques internes de `docs/` ne sont pas publiés.

Les huit PDF de `RulesCardenveil/` sont transcrits dans `docs/rules/sources/*.json`, avec leurs
numéros de page, titres déduits de leur typographie, paragraphes et tableaux reconstruits.
La lecture principale suit les sections ; chaque citation renvoie au texte original dans un
volet dépliable. Les anciennes ancres `#page-N` restent utilisables. La recherche indexe les
sujets et indique le document et la page. Pour actualiser : `py scripts/extract_rule_sources.py`
(nécessite PyMuPDF, inclus dans l'extra `pdf-assets`). Le déploiement ne dépend pas des PDF
locaux : il utilise les transcriptions versionnées et les Markdown existants de `docs/rules/`.
Les images des PDF ne sont pas incluses ; les transcriptions ne résolvent aucune contradiction.
`reading-guide.md` signale les principales divergences repérées.

Le rendu des fiches Markdown couvre leurs titres, paragraphes, listes, code inline, gras et
tableaux. Les sorties `web/public/regles/` sont régénérées par `web/build.py` et ignorées par Git.

## Configuration Cloudflare Pages

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
narratif et totem pleine largeur. Le recto reprend les cadres des exemples `htmls/recto.html` ;
le verso reprend le tableau à sept colonnes de `htmls/verso.html` (visuel, description, valeur,
coût, incantation, sauvegarde, utilisation). Ces exemples sont des captures de Toupou : le rendu
les reconstruit en vrai HTML, sans réutiliser leur image de fond ni leurs champs modifiables.
Les cadres d'identité et narratifs vides restent disponibles pour l'annotation sur papier.
L'équipement et
l'inventaire, lorsqu'ils sont renseignés, occupent la troisième feuille ; les continuations
éventuelles suivent. Les métadonnées éditoriales ne sont pas imprimées.

La pagination attend les images et les polices, mesure les blocs et conserve le texte riche
lors des continuations. La police principale est de 9 pt, celle du tableau de 8,5 pt. Le nombre
de lignes et leur hauteur suivent les capacités du personnage, sans limite arbitraire de pages.
Chaque continuation répète les en-têtes du tableau. Une description trop longue se poursuit sur
une nouvelle feuille A4 sans être tronquée ; une zone de notes lignées est ajoutée s'il reste de
la place. Les copies identiques du texte du totem dans l'ancien champ d'inventaire ne sont pas
imprimées deux fois. Aucune donnée de l'archive n'est modifiée.

Le navigateur assure l'impression et l'enregistrement PDF : sélectionner A4, échelle 100 % et
désactiver ses en-têtes/pieds de page. Les navigateurs Chromium sont utilisés pour la validation.
Le build du site ne produit plus de fichiers PDF et ne nécessite plus les dépendances PDF.
L'ancien exporteur Python reste disponible pour les consommateurs existants du core.

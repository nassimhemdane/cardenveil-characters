# Dashboard du catalogue

La page `/statistiques/` est produite par `web/statistics_pages.py` lors de
`py -3.11 -X utf8 web/build.py`. Elle utilise les mêmes personnages, chargés par
Cardenveil Core depuis `Final/*.zip`, que le catalogue. Elle fonctionne sans
JavaScript, sans Gemini et sans bibliothèque graphique externe.

## Indicateurs

- Nombre de personnages et de capacités ; moyenne des capacités par personnage.
- Répartition des races, des quatre couleurs et des modes d’utilisation.
- Coûts de base et finaux : effectif, moyenne, médiane, écart type de population,
  minimum, maximum et nombre de valeurs absentes ou invalides, par couleur et au total.
- Distribution des scores bruts Force, Agilité, Esprit et Social.
- PV maximum, difficulté et nombre de compétences cochées par personnage.

Les statistiques exportables se trouvent dans `/statistiques/donnees.json`.
Les calculs exportés conservent leur précision ; l’affichage est arrondi à deux
décimales. Les pages et données générées ne sont pas versionnées : elles sont
reconstruites lors du déploiement.

## Conventions de calcul

Chaque capacité compte une fois, préparée ou non. Les totems sont exclus. Le coût
final est le champ `cost.total`, sans recalcul ni interprétation de sa formule.
Les coûts nuls sont inclus ; les coûts négatifs, manquants, non numériques ou
infinis sont exclus des statistiques numériques et signalés. Les groupes sans
observation affichent « — », et non zéro.

L’écart type décrit la population du catalogue :
`σ = sqrt(sum((x - moyenne)²) / N)`. Une seule observation donne zéro.
Chaque capacité a le même poids dans la moyenne des coûts.

Une capacité « Action / Réaction » est comptée dans les deux modes pour le
graphique des modes. Un second graphique des combinaisons la compte une seule
fois. Une action bonus seule n’est jamais comptée comme une action. La
concentration est un indicateur séparé. Les libellés non reconnus sont visibles
dans la section qualité, sans correction automatique.

Les races sont regroupées en ignorant casse, accents, balises et espaces
superflus. Les hybrides, variantes orthographiques et différentes désignations
ne sont pas fusionnés sémantiquement. Aucun personnage n’est modifié.

Les compétences décochées ne permettent pas de savoir si une extraction est
incomplète : le dashboard compte uniquement les maîtrises explicitement cochées.

## Validation

`py -3.11 -X utf8 -m pytest -q tests/test_statistics_pages.py tests/test_static_pages.py`

Les tests couvrent les mathématiques sur des distributions connues, les valeurs
nulles et invalides, les couleurs inconnues, les usages multiples, le catalogue
complet, l’absence de scripts, et les affichages Chrome de 390 et 1280 pixels.

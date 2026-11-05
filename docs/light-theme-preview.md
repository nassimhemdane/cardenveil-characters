# Aperçu du thème clair

Ce prototype s’inspire de la sobriété de [Workflow](https://www.workflow.design/) :
fond blanc, typographie simple, espaces généreux, bordures fines, boutons neutres.
Il conserve les données et les fonctions du catalogue, des fiches, des règles et
du dashboard. Les feuilles A4 et l’impression restent inchangées.

## Code couleur

| Caractéristique | Couleur | Valeur |
| --- | --- | --- |
| Force | Rouge | `#b42332` |
| Agilité | Vert | `#187647` |
| Esprit | Bleu | `#245bc1` |
| Social | Violet | `#7541a7` |

Les libellés sont conservés : aucune information ne repose sur la couleur seule.

## Essayer

```powershell
py -3.11 -X utf8 web/build.py
py -3.11 -m http.server 8768 --bind 127.0.0.1 --directory web/public
```

Ouvrir `http://127.0.0.1:8768/`, une fiche de personnage et `/statistiques/`.

## Revenir au thème sombre

Le thème est une couche CSS séparée : `web/public/theme-light.css`.
Il suffit de retirer la première ligne de `web/public/styles.css` :

```css
@import url("/theme-light.css");
```

Les anciens styles restent intacts sous cette ligne. Les attributs `data-stat`
ajoutés au HTML sont sans effet sur le thème sombre.

Une sauvegarde des fichiers originaux se trouve dans :
`Final/Backups/site-theme-before-light-20261105.zip`.
Elle contient `styles.css`, `app.js` et `statistics_pages.py`, pris avant les
modifications. Le commit `2d353d6` est également la référence du site publié
avant ce prototype. Ne pas remplacer d’autres changements locaux pour revenir
sur le thème.

Cette version a été validée en aperçu local avant publication.

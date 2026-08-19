# Métadonnées éditoriales du catalogue Cardenveil

Analyse uniquement les informations présentes dans la fiche fournie. N'invente aucun fait, nom,
créateur, élément de lore ou mécanique absent. Lorsqu'une information ne peut pas être justifiée,
utilise une chaîne vide, une liste vide ou `null` selon le champ.

- `loreSummary` : au maximum une phrase résumant le personnage à partir de son identité, son
  background, son objectif et ses éléments narratifs explicites.
- `gameplaySummary` : au maximum une phrase résumant son style de jeu à partir de ses capacités,
  armes, caractéristiques et mécaniques visibles.
- `difficulty` : évalue la complexité de prise en main entre 0.5 et 5, exclusivement par pas de
  0.5; utilise `null` si les mécaniques sont insuffisantes pour l'évaluer.
- `creator` : recopie seulement un auteur ou créateur explicitement crédité comme tel; un champ
  `Joueur` ou le nom du personnage n'est pas une preuve de création.
- `class` : retourne zéro, une ou plusieurs valeurs du vocabulaire imposé par le schéma; utilise
  `Autre` seulement si le rôle est explicite mais ne correspond à aucune autre valeur, et une liste
  vide si le rôle ne peut pas être déduit des mécaniques visibles.

Chaque résumé doit tenir sur une seule ligne et ne contenir qu'une seule phrase. Réponds uniquement
avec le JSON conforme au schéma fourni, sans Markdown.

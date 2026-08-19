# Réparation ciblée du totem et des capacités

Analyse le PDF Cardenveil complet, mais retourne exclusivement le bloc `totem`, la liste
`capacities` et les éventuels `warnings` prévus par le JSON Schema.

## Totem

Sur la première page, localise le bloc intitulé `Totem`. Transcris son nom dans `totem.nom` et
l'intégralité de son effet dans `totem.description`. Le titre du bloc peut être imprimé sur la
bordure inférieure. Inspecte le texte immédiatement au-dessus de ce titre et les zones voisines.

## Capacités

La page suivante contient un tableau dont les colonnes sont généralement `Description`, `Valeur`,
`Visuel`, `Coût`, `Incantation`, `Sauvegarde` et `Utilisation`. Parcours la page entière de haut en
bas. Chaque titre suivi d'une description ou de valeurs constitue une capacité distincte.

Pour chaque capacité visible :

1. crée exactement une entrée dans `capacities` ;
2. conserve le titre et la description complète ;
3. copie les valeurs, coûts et formules sans les recalculer ;
4. utilise `null` uniquement pour un sous-champ réellement absent ou illisible ;
5. n'omets pas une capacité au seul motif qu'un de ses sous-champs est vide.

Avant de répondre, recompte les titres de capacité visibles sur toutes les pages et vérifie que la
liste JSON contient le même nombre d'entrées. Si du texte de capacité est visible, la liste ne doit
jamais être vide. N'extrais aucune identité, statistique, compétence ou donnée narrative.

Réponds uniquement avec le JSON conforme au schéma fourni, sans Markdown.

# Règles du personnage

## character.stats.modifier

- Statut: `canonical`
- Source: `Cardenveil Systeme de base`, section Caractéristiques
- Concepts: `Character`, `SheetStats`
- Formule: `floor((score - 10) / 2)`

Le modificateur d'une caractéristique est la moitié de son écart à 10, arrondie à l'entier
inférieur. Par exemple, une valeur de 8 produit un modificateur de −1 et une valeur de 16 produit
un modificateur de +3.

## character.health.max

- Statut: `unresolved`
- Source A: `Compain rules (layer 5)`, page 4
- Source B: fiche de Mimyr
- Concepts: `DerivedValues.pvMax`, `SheetStats.force`

Une source définit les PV maximum comme `35 + 2 × Force`. La fiche de Mimyr indique cependant
70 PV maximum avec Force 16, alors que cette formule produit 67. Aucun calcul canonique ne doit
être effectué tant que cette divergence n'est pas arbitrée.

## character.stats.creation_pool

- Statut: `canonical`
- Source: `Compain rules (layer 5)`, page 5
- Concepts: `SheetStats`

À la création, un personnage répartit 52 points entre Force, Agilité, Esprit et Social. Chaque
caractéristique est comprise entre 0 et 20.


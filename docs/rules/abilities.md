# Règles des capacités et cartes

## ability.save.aoe_acrobatics

- Statut: `canonical`
- Source: `Compain rules (layer 5)`, page 21
- Concepts: `SheetCapacity.save`, `SheetSkills.acrobaties`

Lorsqu'une créature résiste à une capacité à effet de zone, elle effectue une sauvegarde
d'Acrobaties associée à l'Agilité contre le seuil de sauvegarde de l'utilisateur.

## ability.cost.stat_reduction

- Statut: `canonical`
- Source: `Compain rules (layer 5)`, pages 4–5
- Concepts: `AbilityCost.base`, `AbilityCost.incantationReduction`

Le coût d'une capacité est réduit par l'écart entre sa caractéristique d'incantation et 10. Le JSON
conserve séparément le coût de base, cette réduction et les autres réductions afin de reproduire la
fiche sans recalcul lors du chargement.

## ability.known.maximum

- Statut: `unresolved`
- Source: `Compain rules (layer 5)`, pages 5 et 20
- Concepts: `AbilityControls.knownAbilities`, `SheetStats.esprit`

Le corpus donne à la fois un arrondi supérieur et un arrondi inférieur pour `Esprit ÷ 2`. Le maximum
de capacités connues reste donc une valeur persistée, non recalculée par le core.


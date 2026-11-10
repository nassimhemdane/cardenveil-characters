# Arbitrages de traduction — 8 novembre 2026

Autorité : réponses de l'auteur dans `translation-audit-fr-en.md`, puis demande d'appliquer aussi les clarifications au français.

## Choix validés

Résilience → Resilience ; Culture → Knowledge ; compétence maîtrisée → Proficient skill ; maîtrise d'arme → Weapon Mastery ; valeur brute → Raw Power ; seuil de miss → Miss Threshold ; Incantation → Incantation ; Précipitation → Rush ; Ruée → Dash ; catalyseur → Focus.

Force → Strength ; Agilité → Agility ; Esprit → Spirit ; Social → Social ; Escamotage → Sleight of Hand. Les capacités ne sont pas toutes des sorts : Ability reste le terme générique.

## Clarifications françaises appliquées

Le fichier compagnon `translation-rulings-2026-11-08.json` contient pour chaque modification le fichier, le texte exact avant/après et le nombre d'occurrences.

- Exemples de jets de Force et d'Esprit : préciser le modificateur, sans modifier les valeurs de caractéristiques ni les formules qui utilisent réellement le score (PV, initiative, sauvegarde, coûts).
- Paiement des capacités : somme des cartes supérieure ou égale au coût.
- Sauvegarde : résultat supérieur ou égal au seuil.
- Tokens : `max(0, 1 + modificateur)`. Le plancher existant à zéro est conservé pour éviter un nombre négatif de tokens.
- Valeur brute : somme de `Mod d6`, puis application du multiplicateur `K` au total. Ce n'est pas `Mod` multiplié par le résultat d'un seul dé.
- Durée des zones : écrire round lorsque l'unité est explicitement le round global.
- Zone en ligne : 18 m, pas 30 m.
- Propriété Impact : repousse de 5 m, pas 3 ou 4 m.

Les durées attachées au tour personnel restent des tours. Les passages de rupture légendaire « 2 tours (peu importe lesquels) » et d'initiative ne sont pas réinterprétés : l'auteur a demandé de conserver l'initiative et n'a pas précisé une nouvelle unité pour ces durées.

## Publication et données

Les Markdown français corrigés conservent leur rôle de source ; leurs empreintes dans le manifeste sont actualisées. Les traductions anglaises sont stockées séparément. Les archives sources ne sont ni renommées ni recalculées pour traduire : seules les copies anglaises de téléchargement sont localisées, avec les mêmes clés, nombres et ressources graphiques.

Le sélecteur utilise 🇫🇷 FR et 🇬🇧 EN. La détection au premier accès à l'accueil utilise le pays fourni par Cloudflare, puis la langue du navigateur si ce renseignement n'est pas disponible. Les pays multilingues figurant dans la liste francophone choisissent le français par défaut ; le visiteur peut toujours changer ce choix. Les liens directs `/en/…` ou français sont respectés.

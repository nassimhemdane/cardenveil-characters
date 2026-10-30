# Formules de migration des fiches — arbitrages du 30 octobre 2026

Ces formules ont été confirmées par l'utilisateur pour corriger les archives
existantes, sans modifier leur format JSON ni les coûts des capacités.

- Modificateur : `floor((caractéristique − 10) / 2)`.
- PV max : `60 + 5 × Force`.
- Mouvement : `5 + ceil(Agilité / 2)`.
- Initiative : `Agilité − 10`.
- Perception passive : `10 + bonus de Perception`.
- Volonté : bonus de Résilience.
- Une compétence maîtrisée utilise deux fois le modificateur de sa caractéristique.
- Canalisation : modificateur d'Esprit.
- Seuil de miss : `max(1, 1 − (Agilité − 10) / 2)` ; les 67 fiches actuelles ont
  une Agilité paire. L'arrondi pour une future valeur impaire reste à confirmer.
- Jetons : `max(0, 1 + modificateur)` pour chaque caractéristique.
- Bonus d'attaque : champ vide.

Goldomus est explicitement exclu des nouvelles passes de recalcul, à la demande
de l'utilisateur en raison de son passif. Les PV actuels et temporaires ne sont
pas réinitialisés. Aucun nouveau bonus racial n'est déduit automatiquement du
texte des passifs. Le seuil de sauvegarde reste inchangé, sa formule n'ayant pas
été fournie.

Scripts : `scripts/recalculate_confirmed_values.py` et
`scripts/apply_confirmed_sheet_fixes.py`. Chaque passe sauvegarde les archives
modifiées dans `Final/Backups/`.

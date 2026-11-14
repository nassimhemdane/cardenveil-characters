# Cardenveil VTT — interactions et fluidité

Date de validation locale : 14 novembre 2026

## Implémenté

- Déplacement des tokens au pointeur réel, sans interpolation pendant le drag.
- Conservation du point de saisie initial du token.
- Seuil de 4 px entre clic et déplacement afin d’éviter les faux drags.
- Hover distinct et immédiat, curseurs `grab` / `grabbing` et contour discret.
- Agrandissement `1.04` et ombre du token pendant le drag, sans modifier les coordonnées du pointeur.
- Confirmation d’atterrissage sobre de 110 ms après un déplacement effectif.
- Capture du pointeur sur le canvas et libération propre à la fin de l’interaction.
- Regroupement des `pointermove` avec `requestAnimationFrame` : au maximum une mise à jour visuelle par frame.
- Déplacement collectif conservant les positions relatives de la sélection.
- `Escape` annule le déplacement et restaure l’état précédant la saisie.
- Une perte de focus ou un `pointercancel` annule également l’interaction sans laisser d’objet bloqué.
- Undo/redo existant conservé ; un drag terminé crée une seule entrée d’historique, pas une entrée par frame.
- Zoom centré sur le curseur et limites existantes conservés (`0.05` à `16`).
- Conversions centralisées et testables : écran → monde et monde → écran.
- Snapping configurable et persistant : `Désactivé`, `Doux`, `Fort`.
- Sensibilité configurable du snapping doux.
- Hystérésis du snapping doux (zone de sortie à 135 % du seuil) pour éviter l’oscillation entre deux cibles.
- Origine X/Y configurable pour une grille décalée.
- Ancrage configurable sur le centre des cellules ou sur leurs coins/intersections.
- Conversions `worldToGrid` / `gridToWorld` compatibles avec une origine décalée et une rotation de grille.
- Désactivation temporaire du snapping avec `Ctrl` ou `Cmd` pendant le déplacement.
- Position libre séparée de la position candidate ; le token suit librement la souris et un point d’aperçu indique la destination aimantée.
- Alignement appliqué seulement au dépôt, sans arrondi prématuré des coordonnées écran.
- Les groupes sont alignés à partir de leur ancre sans modifier leurs espacements relatifs.
- Anciennes sauvegardes compatibles : l’ancien booléen `grid.snap` est migré vers le nouveau mode.
- Micro-interactions uniformisées : feedback pressé immédiat, apparition courte des menus et focus existant conservé.
- Menus de sélection contraints horizontalement et verticalement au viewport.
- Auto-scroll des bibliothèques et de l’outliner lors d’un drag près de leurs bords.
- Raccourcis clavier directs : `V` sélection, `H` main, `R` mesure, `D` dessin, `T` texte et `G` grille.
- `Espace` recentre progressivement la caméra sur l’objet ou sur les limites de la sélection multiple.
- La main de cartes est masquée au premier chargement et reste accessible par son bouton flottant.
- Le panneau Grille s’ouvre latéralement à côté de la barre d’outils, comme le panneau Dessin.
- Un texte vide est abandonné sans créer d’objet dans la scène.
- Outil **Gabarit de portée** : cercle, cône ou ligne, tailles Cardenveil `1,5 / 5 / 8 / 14 / 20`, couleur et transparence configurables.
- Prévisualisation transparente sous le curseur avec taille inscrite en blanc, puis placement persistant comme objet Note.
- Un cône ou une ligne placé depuis un personnage, une monture ou un accessoire s’ancre sur cet objet et s’oriente avec la souris.
- Sans objet d’ancrage, `Ctrl/Cmd + molette` oriente les gabarits directionnels par pas de 5°.
- `prefers-reduced-motion` désactive pratiquement toutes les animations et transitions.
- La sauvegarde reste différée ; aucun accès IndexedDB ou dossier local n’est exécuté directement dans `pointermove`.

## Fonctionnalités existantes conservées

- Pan à la molette centrale et outil Main.
- Zoom sous le curseur.
- Sélection simple, Shift, rectangle et sélection multiple.
- Shift-clic ajoute ou retire directement un objet de la sélection ; Shift sur le vide conserve le rectangle cumulatif.
- Objets verrouillés, double-clic, hiérarchie, outliner et calques.
- Alt-clic de duplication, redimensionnement collectif, rotation et renommage.
- Mesure, portées, déplacement mesuré, dessins, texte, gomme et import d’images.
- Historique, persistance IndexedDB, dossier local et export/import de scène.
- Interface blanche/noire, overlays, main de cartes, fiche compacte et dés 3D.

## Paramètres disponibles

Dans le panneau **Grille** :

- affichage de la grille ;
- mode d’aimantation : Désactivée / Douce / Forte ;
- ancrage : centre des cellules ou coins/intersections ;
- sensibilité du mode Doux ;
- taille et échelle ;
- unité ;
- origine X et Y ;
- opacité.

Raccourci temporaire : maintenir `Ctrl` (Windows/Linux) ou `Cmd` (macOS) pour ignorer le snapping.

## Tests exécutés

- `npm test` : **18/18 tests réussis**.
- Couverture ajoutée : conversions pan/zoom réversibles, Off/Soft/Strong, centres/intersections, grille décalée et tournée, hystérésis, désactivation temporaire, migration des sauvegardes, groupes, objets verrouillés, contraintes des menus et charge de 100 tokens.
- `npm run build` : **réussi**, bundle Vite de production généré.
- `npm run test:browser` : **réussi dans Chrome headless**.
- Le scénario navigateur historique a été actualisé pour les accordions Atelier et passe à nouveau intégralement.
- Validation directe ajoutée : création d’un token depuis le personnage, drag réel au pointeur, déplacement détecté, puis `Ctrl+Z` et restauration exacte de la position.
- Ratios validés : `1920×1080`, `1440×900`, `1024×600`, `768×1024`, `650×1024`, `390×844`, `320×568`, `844×390`, `1280×420`, `320×320`.
- Le même passage valide aussi la persistance, les dés 3D, les panneaux compacts, la main, les contraintes de viewport et l’absence d’erreur console.
- Le scénario navigateur vérifie également la main initialement masquée, le menu Portées latéral, sa couleur rouge par défaut, la persistance d’un cône comme Note et le recentrage par `Espace`.
- `git diff --check` : aucune erreur d’espace ; seuls les avertissements Windows LF/CRLF sont signalés.

## Mesure de performance locale

- Benchmark Node sur 1 000 000 conversions écran → monde suivies d’un calcul de snapping doux : **90,8 ms au total**, soit environ **0,091 µs par opération** sur cette machine.
- Test automatisé de charge : déplacement collectif de **100 tokens pendant 600 frames** terminé en environ **6,5 ms** pour les calculs géométriques sur cette machine.
- Le calcul géométrique représente donc une fraction négligeable du budget de frame de 16,7 ms ; le rendu canvas et le décodage des images restent les éléments à profiler avec les assets de campagne réels.

## Validation technique

- Aucun changement des règles, données de personnages ou logique métier.
- Aucune nouvelle dépendance.
- Aucun push ni commit effectué.
- Les fichiers générés du build ne sont pas inclus comme sources du changement.

## Limites restant à vérifier manuellement

- Mesure FPS/GPU avec une véritable battlemap lourde et 100 images : elle dépend du GPU, du décodage des assets et de la machine cible ; les calculs géométriques de 100 tokens sont néanmoins couverts automatiquement.
- Le ressenti précis du snapping doux et de l’atterrissage reste une validation humaine à effectuer avec la souris ou le trackpad réellement utilisé.

## Validation manuelle minimale

1. **Déplacer un token** — Attraper le token près d’un bord, le déplacer rapidement puis lentement et le relâcher. Il doit rester exactement sous le point saisi, sans saut ni retard, légèrement se soulever pendant le drag et se poser discrètement.
2. **Tester le snapping** — Essayer successivement Désactivé, Doux et Fort, puis maintenir `Ctrl` pendant un déplacement. Le mode Doux doit rester libre sauf près d’une cible, le mode Fort doit toujours aligner le dépôt et `Ctrl` doit rendre le déplacement immédiatement libre.
3. **Zoomer et déplacer la vue** — Placer le curseur sur un détail, zoomer fortement puis utiliser la molette centrale pour déplacer la carte. Le détail doit rester sous le curseur et la caméra ne doit ni sauter ni donner une sensation de retard.
4. **Déplacer un groupe** — Sélectionner plusieurs tokens avec `Shift` ou le rectangle, puis déplacer et redimensionner le groupe. Tous les objets doivent conserver leurs écarts relatifs ; les objets verrouillés doivent rester immobiles.
5. **Interrompre et annuler** — Commencer un déplacement, appuyer sur `Escape`, puis effectuer un autre déplacement et utiliser `Ctrl+Z`. Dans les deux cas, le token doit revenir proprement à sa position précédente sans rester dans un état de drag.

Si ces cinq manipulations paraissent directes, précises et sans latence perceptible, le comportement attendu est validé.


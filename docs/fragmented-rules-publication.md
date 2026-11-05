# Règles joueurs : édition Cardenveil Fragmented

## Source publiée

Le site utilise désormais les sept Markdown joueurs du dossier
`Cardenveil/Cardenveil Fragmented`, conservés sans modification dans
`docs/rules/fragmented/` avec leurs empreintes SHA-256.

`Partie MJ.md` est exclu explicitement de l’import, de la navigation et de la
recherche. Les mentions du MJ présentes dans les règles joueurs restent intactes.
L’Agent MJ existant est un outil distinct ; cette mise à jour ne modifie pas son
moteur ni les données de règles utilisées par son serveur local.

Les anciennes transcriptions PDF et synthèses du Core ne sont plus mélangées aux
règles courantes du site. Elles restent dans le dépôt pour les usages techniques.
Leurs anciennes URL publiques renvoient vers les chapitres actuels, sans republier
leur texte ni les anciens arbitrages MJ.

## Organisation

1. Référence rapide : premier lien, accès principal et contenu disponible dès
   l’accueil `/regles/`.
2. Système de base.
3. Création de personnage.
4. Races jouables : chapitre extrait de Personnage, avec ses traits et images.
5. Progression.
6. Actions et combat.
7. Totems, capacités et cartes.
8. Aspects et narration.

Les titres, listes imbriquées, tableaux, citations et illustrations Obsidian sont
rendus sans HTML actif. Les sources originales restent dans le dépôt, mais leurs
boutons, noms de fichiers et volets ne sont pas affichés aux visiteurs. Les
options « À votre rythme », « Texte agrandi » et « Lecture claire » sont retirées.
Chaque chapitre propose ses sous-catégories dans une navigation unique à gauche,
qui devient repliable sur mobile. Les flèches et titres utilisent une ligne flex
commune pour éviter leur décalage. Le menu Actions & combat garde ses catégories
thématiques, notamment actions principales, bonus et réactions. Le sommaire de
droite et le deuxième sommaire mobile sont retirés. Les règles ne sont pas réécrites pour résoudre automatiquement leurs
éventuelles contradictions, et les fiches de personnages ne sont pas recalculées.

## Illustrations

26 races sont présentes. 25 illustrations ont été retrouvées et converties en
WebP, avec une dimension maximale de 900 pixels et une URL basée sur leur contenu.
Le total passe de 26,3 Mo à environ 0,89 Mo.

L’image de « Race Bestiale (Personnalisable) » est absente du dossier local :
`../../Races%20Jouables/021fe7ebd674dc0af101220e7246fbed.jpg`.
La page le signale sans réutiliser l’image d’une autre race.

## Actualiser les sources

```powershell
py -3.11 -X utf8 scripts/sync_fragmented_rules.py "C:/Users/Nassim/Desktop/RP_compaings/Cardenveil/Cardenveil Fragmented"
py -3.11 -X utf8 web/build.py
```

Le build de production utilise uniquement les fichiers versionnés ; il n’a pas
besoin du dossier Obsidian ni de Pillow. Pillow est utilisé par la synchronisation
locale pour compresser les illustrations. Le manifeste identifie les images
introuvables et les fichiers réellement retenus. Aucune clé Gemini n’est utilisée.

## Vérifier

```powershell
py -3.11 -X utf8 -m pytest -q tests/test_rules_pages.py tests/test_rules_browser.py
```

Les tests couvrent notamment les sources exactes, l’exclusion de la Partie MJ,
les liens et ancres, la sécurité du rendu, les 26 races et leurs 25 illustrations,
la recherche, le filtre des races et la navigation mobile.

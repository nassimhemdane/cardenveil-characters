# Ambiguïtés de règles

## Points de vie maximum

- Source A: `Compain rules (layer 5)` — `35 + 2 × Force`.
- Source B: fiche Mimyr — Force 16, PV max 70 (la formule A produit 67).
- Impact: calcul dérivé et validation.
- Decision: **UNRESOLVED**. Aucune fonction `max_hp` canonique.

## Initiative

- Source A: corpus consolidé — `2 × modificateur d'Agilité`.
- Source B: documents signalés comme donnant d'autres formulations.
- Impact: ordre des tours.
- Decision: **UNRESOLVED**. Non implémentée.

## Nombre maximum de capacités

- Source A: corpus consolidé — Esprit ÷ 2, arrondi au supérieur.
- Source B: variantes signalées avec des arrondis différents.
- Impact: validation de l'apprentissage.
- Decision: **UNRESOLVED**. Aucune limite exécutable.

## Nombre de tokens

- Source A/B: passages de versions différentes, sans priorité canonique.
- Impact: état runtime initial et repos.
- Decision: **UNRESOLVED**. Tokens hors du modèle persistant V1.

## Parade

- Source A/B: formulations différentes dans le corpus.
- Impact: défense dérivée et résolution d'attaque.
- Décision MJ du 23 octobre 2026 : la base de parade de toutes les armes est le dé maximal
  divisé par **2**. Les mentions de division par 3 sont obsolètes.
- Décision MJ du 24 octobre 2026 : arme = dé/2 + mod Agilité + déflexion ; épée droite =
  dé/2 + mod Force OU mod Agilité + déflexion ; bouclier = parade du bouclier + mod Force
  + déflexion. Le cumul Force + Agilité d'une ancienne page est remplacé par ce choix.
- Référence : [arbitrages MJ](rules/rulings.md). Le moteur de combat reste hors périmètre actuel.

## Mimyr comme golden sample

- Source A: fiche structurée de Mimyr, schéma applicatif V1.
- Source B: domaine canonique nouveau.
- Impact: présence d'images, champs UI, valeurs dérivées/runtime et texte mal encodé.
- Decision: fixture partiel sémantique; le schéma applicatif ne définit pas le domaine.


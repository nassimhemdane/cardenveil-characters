# ADR 0001 — Modèle indépendant des formats

## Contexte

PDF, application web et futurs adaptateurs possèdent leurs propres schémas.

## Décision

Le domaine n'importe aucun module de sérialisation ou d'application. Les adaptateurs convertissent
explicitement vers les objets du domaine.

## Conséquences

Un mapping est nécessaire par format, mais tous les consommateurs partagent la même sémantique.


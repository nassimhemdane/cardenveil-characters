# ADR 0004 — Persistent, derived et runtime

## Contexte

Une fiche mélange actuellement données durables, caches calculés et état de partie.

## Décision

Character ne contient que l'état durable. Les calculs sont des fonctions pures reliées à des règles;
le runtime aura plus tard son propre modèle.

## Conséquences

Les exports canoniques évitent les valeurs contradictoires et restent utilisables hors combat.


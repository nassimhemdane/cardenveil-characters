# ADR 0006 — Frontière fournisseur pour l'import PDF

## Contexte

La première implémentation utilise Gemini, mais le domaine doit rester utilisable sans SDK externe
et un VLM local devra pouvoir remplacer Gemini.

## Décision

Le domaine expose `CharacterSheet`. L'infrastructure PDF expose un protocole
`CharacterDocumentExtractor` qui retourne un `ExtractedCharacter` Pydantic. Un mapper explicite
est seul responsable de la conversion vers le domaine. Gemini est une dépendance optionnelle et
chargée paresseusement.

## Conséquences

Les tests usuels restent offline. Un provider local pourra implémenter le protocole sans modifier
le mapper. Le modèle métier ne connaît ni PDF, ni prompt, ni clé API, ni SDK Gemini.


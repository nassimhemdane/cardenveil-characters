# Traduction FR / EN — validation locale du 10 novembre 2026

## Résultat

Le build bilingue génère 68 personnages, 552 capacités, les huit chapitres publics issus de sept Markdown, les statistiques, le guide, les fiches imprimables et les 68 archives anglaises. Le sélecteur FR / EN conserve les paramètres et ancres ; le choix est mémorisé. La langue initiale dépend du pays fourni par Cloudflare, avec repli sur la langue du navigateur.

Les 2 322 textes de personnages sont enregistrés dans `web/i18n/characters.en.json`. Les traductions et corrections ont été produites ici et par le moteur Ollama local déjà installé, sans service externe de traduction. Le build est déterministe et sans appel de traduction.

## Corrections et relecture

Les clarifications françaises autorisées sont tracées dans `translation-rulings-2026-11-08.json`. Les traductions préservent les nombres, identifiants, clés et images ; les archives françaises ne sont pas modifiées par le générateur bilingue.

La relecture a corrigé deux lots dont les valeurs étaient décalées, des formules ayant perdu leur modificateur, les mentions de suit/color, la distinction Strength/force damage, la Ruée (+ moitié de vitesse), les propriétés d’armes et un titre dupliqué. Les corrections de personnages sont conservées dans `web/i18n/reviewed-overrides.en.json` et les scripts de relecture. Le rapport numérique ne contient plus d’écart à examiner.

Les divergences non arbitrées de la source restent conservées : initiative, certains arrondis et résumés, parade divisée par 2 ou 3 selon le passage. La phrase inachevée sur le token Social dans la création est signalée comme incomplète dans l’édition anglaise, sans inventer de règle.

## Vérification

- Build complet réussi : `py -X utf8 web/build.py`.
- 11 tests de localisation et Chromium réussis : données et archives, routes, choix de langue, catalogue, recherche, navigation, mobile et impression.
- 20 tests des API et assistants réussis : erreurs bilingues, recherche des règles, citations et recommandations.
- Titres et images des chapitres création et narration comparés aux sources ; le build vérifie la correspondance des titres de tous les chapitres et leurs empreintes.

Le site est prêt à être consulté localement. Aucun déploiement n’a été effectué. Les réponses génératives réelles des assistants n’ont pas été testées auprès d’un service externe ; les tests emploient des fournisseurs simulés.

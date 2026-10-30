# Recommandations publiques Gemini

Le site appelle une Pages Function, qui vérifie Turnstile puis appelle Gemini.
La clé Google et la clé secrète Turnstile ne passent jamais par le navigateur.
Le modèle est fixé côté serveur à `gemini-3.1-flash-lite`, sans outil, recherche
Google, bascule vers un autre modèle ou nouvelle tentative automatique.

## Activation dans Cloudflare

1. Dans Google AI Studio, créer/utiliser une clé d'un **projet au palier gratuit**.
   Vérifier le palier et les quotas réels dans AI Studio. Le code ne peut pas
   déterminer si le projet associé à une clé est facturé. Un modèle disposant
   d'un palier gratuit n'est pas automatiquement gratuit sur un projet payant.
2. Cloudflare → **Turnstile → Add widget** : mode Managed, hostname
   `cardenveil-characters.pages.dev`. Ajouter le domaine personnalisé si nécessaire.
   Conserver la Site key et la Secret key.
3. Cloudflare → **Workers & Pages → cardenveil-characters → Settings →
   Variables and Secrets**, environnement **Production** :

   | Nom | Type | Valeur |
   |---|---|---|
   | `GEMINI_API_KEY` | Secret | Clé du projet Google gratuit |
   | `TURNSTILE_SECRET_KEY` | Secret | Secret du widget Turnstile |
   | `TURNSTILE_SITE_KEY` | Texte | Clé publique du widget |
   | `GEMINI_FREE_TIER_CONFIRMED` | Texte | `1`, uniquement après vérification du palier gratuit |

4. Redéployer le dernier commit : **Deployments → dernier déploiement → Retry deployment**.
   Les variables de Preview doivent être configurées séparément si nécessaire.
5. Ouvrir `/api/recommendation-config` : `enabled` doit être `true` ; aucune clé
   secrète ne doit apparaître. Saisir ensuite une phrase dans « Parlez au guide ».

Ne jamais coller les secrets dans un fichier public, dans Git ou dans la conversation.
Pour désactiver immédiatement : retirer `GEMINI_FREE_TIER_CONFIRMED` ou passer sa
valeur à `0`, puis redéployer. La recherche sans IA reste disponible.

## Limites et confidentialité

- Zéro à six suggestions : identifiants existants, absence de doublons, commentaire
  borné et citation exacte contrôlés côté serveur. La pertinence des commentaires
  reste une appréciation du modèle, pas une preuve automatique.
- Résumés et extraits bornés des fiches, pas les images ni les fichiers PDF.
- Avec le RAG actif : au maximum un embedding de question et un appel d'explication
  par demande non mise en cache ; cache d'une heure lié au catalogue et
  à la phrase. Le cache Cloudflare n'est pas une garantie d'économie globale.
- Turnstile est obligatoire, jeton à usage unique vérifié côté serveur, hostname
  et action contrôlés. Ce n'est pas une authentification ni un plafond global de quota.
- Le palier gratuit Google impose ses propres limites : un dépassement renvoie
  un message de quota, sans bascule vers un modèle payant. Les Workers/Pages ont
  également leurs limites propres ; aucune promesse de disponibilité illimitée.
- Le palier gratuit Google peut utiliser les contenus envoyés pour améliorer
  ses produits : éviter les données personnelles et utiliser seulement des fiches
  dont la transmission est autorisée. Le site affiche un avertissement.
- Ollama reste utilisable sur le serveur local ; aucune ouverture de port n'est requise.

Le classement public utilise désormais les statistiques et l'index des capacités :
voir [le fonctionnement du RAG](character-recommendation-rag.md). Le modèle sélectionne
des identifiants de sources ; les citations affichées sont recopiées par le serveur.

Références : [tarifs Google](https://ai.google.dev/gemini-api/docs/pricing),
[secrets Pages](https://developers.cloudflare.com/pages/functions/bindings/#secrets),
[validation Turnstile](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/).

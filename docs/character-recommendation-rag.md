# Recherche de personnages : RAG hybride à priorité statistique

## Données utilisées

Les ZIP de `Final` restent la source de vérité ; leur schéma n'est pas modifié.
Le build produit `data/rag-index.json` à partir des caractéristiques Force,
Agilité, Esprit et Social et de passages mécaniques complets : un par capacité,
un par totem non vide. Les descriptions narratives et les résumés de lore ne
participent pas au classement.

Le corpus actuel comporte 67 personnages, 543 capacités et 67 totems. Contrairement
au précédent résumé de 1 100 caractères par personnage, les capacités en fin de
fiche sont elles aussi indexées et peuvent être retrouvées.

## Classement et justification

La race déclarée est conservée comme donnée structurée, distincte des textes
embeddés. Une demande de race agit comme un filtre strict avant le classement ;
les variantes singulier/pluriel et certaines variantes d'orthographe sont reconnues.
« Nain » ne correspond pas à un personnage simplement parce que son nom ou une
capacité contient ce mot. Une demande d'identité seule (« nain », « nains »,
« je cherche un nain ») retourne directement les fiches correspondantes, au maximum
six, sans embedding de question ni génération Gemini. La citation provient du champ
de race réel, pas d'une déduction du modèle. La source Foist indique « Cochon Nain » :
il apparaît donc avec Anain, Darion et Goldomus pour cette recherche.

1. Reconnaissance déterministe de préférences statistiques françaises : physique,
   agile, mental/magique, social, ainsi que des préférences faibles/négatives.
2. Filtres numériques reconnus appliqués strictement : seuil explicite de
   caractéristique, difficulté maximale ; une difficulté inconnue ne satisfait
   pas une limite numérique. Le parseur ne prétend pas comprendre toutes les
   formulations naturelles : les tests couvrent les expressions prises en charge.
   Les demandes explicites de foudre, feu, glace, poison ou soin exigent également
   une mention mécanique correspondante dans au moins un passage de la fiche,
   avec un petit lexique de variantes. Une forte Agilité ne suffit donc pas à
   recommander la foudre ; un Esprit élevé ne suffit pas à inventer un soin.
3. Recherche des passages par BM25 avec normalisation française légère et,
   lorsqu'il est disponible, cosinus entre embeddings de la question et des capacités.
4. Agrégation des trois meilleurs passages par personnage (75/15/10), limitant
   l'avantage des personnages possédant davantage de capacités.
5. Avec une préférence statistique reconnue : 65 % adéquation des statistiques,
   35 % pertinence mécanique. Sans préférence statistique reconnue : pertinence
   mécanique seule, sans imposer artificiellement une caractéristique.
6. Les six premiers candidats au maximum sont transmis à Gemini pour expliquer
   la correspondance et éventuellement en écarter. Le modèle ne peut pas introduire
   un autre personnage ni inverser l'ordre calculé par le serveur.

Le profil « physique / agile / mental / social / polyvalent » est une indication
calculée à partir des stats, pas une nouvelle classe officielle. Les classes
éditoriales existantes sont conservées, mais ne déterminent pas le score.

Chaque résultat affiche les quatre statistiques, son profil indicatif et une
citation exacte d'un passage fourni au modèle. Le modèle choisit un `source_id` ;
le serveur vérifie son appartenance au personnage et recopie lui-même l'extrait,
plutôt que de demander au modèle de retranscrire la citation. Les IDs, doublons,
longueurs des sorties et références sont vérifiés côté serveur. La pertinence de l'explication
reste une appréciation du modèle, pas une preuve formelle.

## Embeddings et quota

- Modèle de recherche : `gemini-embedding-001`, 768 dimensions, espaces compatibles
  `RETRIEVAL_DOCUMENT` à l'indexation et `RETRIEVAL_QUERY` pour la question.
- Appels à l'API standard `batchEmbedContents` ; ce n'est pas un job asynchrone
  de la Batch API tarifée séparément. Vérifier le palier réel de la clé dans AI Studio.
- Vecteurs compressés en int8 avec normalisation du cosinus ; environ 1 Ko par
  passage plutôt que des tableaux JSON de 768 nombres décimaux.
- Cache incrémental par empreinte du texte : modifier une statistique ne demande
  pas de réindexer les capacités ; modifier leur texte invalide les anciens vecteurs.
- L'index est lié à une empreinte de version. Les résultats en cache sont invalidés
  quand les stats, passages, embeddings ou règles de classement changent.
- À froid : au maximum un appel d'embedding de question puis un appel de génération
  d'explication. Aucun embedding documentaire n'est généré durant une requête utilisateur.
- Si l'index vectoriel est incomplet ou l'embedding de question échoue, repli
  explicite sur stats + BM25, indiqué dans l'interface. Aucune fausse affirmation
  de recherche vectorielle. Pas de tentative cachée ni de bascule payante.
- Turnstile et les contrôles de même origine restent obligatoires.

## Construction et mise à jour

```powershell
py -3.11 -X utf8 web/build.py
# Seulement après confirmation que la clé du .env appartient au projet gratuit :
py -3.11 -X utf8 scripts/index_character_embeddings.py --confirm-free-tier
py -3.11 -X utf8 web/build.py
```

Le script conserve chaque lot réussi dans `web/rag/embeddings.json`. En cas de quota
ou d'erreur HTTP, il s'arrête sans boucle de relance ; la commande peut être reprise
ultérieurement sans repayer/réenvoyer les passages déjà mis en cache. Ce fichier
ne contient que des empreintes et des vecteurs, jamais la clé API. Il doit être
versionné pour rendre l'index disponible au build Cloudflare sans secret de build.
Les lots sont espacés de 35 secondes par défaut pour éviter de saturer la limite
par minute. `--limit` permet de borner le nombre de nouveaux passages et
`--pause-seconds` de régler explicitement cet espacement.

## Vérifications

`tests/test_rag_index.py` vérifie le découpage, les embeddings périmés et la
quantification. `tests/test_rag_retrieval.py` vérifie la priorité des stats face
à un texte trompeur, les quatre profils, les préférences négatives, les filtres
et l'impossibilité pour le modèle d'inverser le classement.
`tests/test_gemini_pages.py` vérifie le budget d'appels, les citations, la protection
anti-abus et le repli explicite lorsque l'embedding de question est indisponible.

Ces tests ne remplacent pas une évaluation de pertinence sur des demandes réelles
validées par le créateur du jeu ; les poids 65/35 sont un choix initial explicite,
pas un optimum mesuré. Les dates d'indexation et les vrais vecteurs doivent être
contrôlés avant de déclarer l'index vectoriel opérationnel.

### Vérification initiale du 30 octobre 2026

- Index complet : 610 passages couverts par 601 vecteurs distincts (textes communs réutilisés).
- Quatre véritables embeddings de questions testés sur le corpus complet.
- Pour « mobile utilisant la foudre, difficulté maximum 4/5 », Hemdane Polytechnique
  arrive en tête avec Agilité 18. Le filtre mécanique retire notamment les personnages
  agiles sans effet de foudre documenté.
- Le test « mage soigneur » retrouve notamment Sanj’kul, Einhar et Aiden, avec un
  passage de soin identifié ; un Esprit élevé seul ne suffit plus.
- Un véritable appel de génération avec sources identifiées produit une recommandation
  d'Hemdane et une explication citant son Agilité 18 et sa capacité de foudre.
- Ces quatre cas sont un smoke test, pas une évaluation exhaustive ni une preuve
  que les pondérations choisies sont optimales.

`scripts/evaluate_character_embeddings.py --confirm-free-tier` génère ou réutilise
quatre embeddings de questions, puis produit les classements et leurs sources
dans `gemini-output/rag-evaluation/report.json`. Les timings Chromium sous horloge
virtuelle ne constituent pas une mesure fiable de latence Cloudflare.
`scripts/smoke_character_rag.py --confirm-free-tier` vérifie ensuite un véritable
appel de génération borné, avec contrôle des identifiants et des sources retournées.

Références : [embeddings Google](https://ai.google.dev/gemini-api/docs/embeddings),
[API embeddings](https://ai.google.dev/api/embeddings),
[tarifs](https://ai.google.dev/gemini-api/docs/pricing).

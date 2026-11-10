# Préparation de la traduction français / anglais

Audit du dépôt local, 8 novembre 2026. Analyse préparatoire uniquement : aucune traduction ni bascule de langue implémentée. Le site déployé n'a pas été contrôlé dans un navigateur.

## Périmètre constaté

- 68 archives dans `Final/` ; le catalogue généré local contient 68 personnages et 552 capacités.
- 7 documents Markdown de règles dans `docs/rules/fragmented/`, environ 19 134 mots comptés par séparation sur les espaces (inclut la syntaxe Markdown).
- 8 chapitres publics : référence rapide, système de base, création, races, progression, combat, capacités, narration. Les races sont extraites du document de création.
- `web/rules_pages.py:build_rules` délègue à `web/fragmented_rules.py`. Les anciennes transcriptions `docs/rules/sources/` ne sont donc pas la source principale de la publication actuelle. Le README web conserve des explications sur l'ancien parcours.
- Pas de couche de traduction partagée identifiée dans les générateurs et scripts examinés ; textes français dans Python, HTML, JavaScript et données.

| Surface | Sources à traiter | Contenu |
| --- | --- | --- |
| Accueil et catalogue | `web/public/index.html`, `app.js`, `catalogue.js`, `web/static_pages.py` | Navigation, recherche, filtres, classes, tri, compteurs, résultats vides, recommandation |
| Fiches | `web/static_pages.py`, `web/public/app.js`, `web/build.py`, archives `Final/`, `web/catalog-metadata.json` | Identité, descriptions, totems, capacités, effets, coûts, sauvegardes, inventaire, aspects, progression, résumés éditoriaux |
| Impression A4 | `web/public/print.html`, `print.js` | Titres, tableaux, légendes et intégralité des données textuelles ; repagination en anglais |
| Règles | `web/rules_pages.py`, `web/fragmented_rules.py`, `docs/rules/fragmented/*.md` | Corps, tableaux, navigation, sommaires, liens, illustrations et référence rapide |
| Recherche de règles | `web/public/rules.js`, index généré `/regles/search.json` | Index anglais, extraits, titres et ancres correspondantes |
| Statistiques | `web/statistics_pages.py` | Titres, graphiques, tableaux, catégories et explications ; conserver les agrégations sur les données canoniques |
| Guide et agent MJ | `web/public/gm/index.html`, `gm.js`, `rules-chat.js`, `src/cardenveil/gm/`, serveur | Interface, erreurs, réponses générées, citations et liens dans la langue choisie |
| Recommandations | `functions/api/recommendations.js`, `web/recommendations-core.js`, `web/rag_index.py`, `web/rag-retrieval.js` | Langue des réponses, recherche de personnages en anglais, contexte et noms affichés |
| Métadonnées et accessibilité | Gabarits HTML/Python | `lang`, titres, descriptions, Open Graph, textes alternatifs, labels ARIA, chargements et erreurs |
| Téléchargements | Archives copiées par `web/build.py` | Choisir si une copie anglaise complète doit aussi être proposée ; le bouton seul ne traduit pas le fichier |

Les images sont référencées par les fiches et le manifeste des règles. Leur éventuel texte incorporé reste à vérifier visuellement : il ne sera pas traduit par les dictionnaires du site.

## Glossaire

### Choix fournis

| Français | Anglais |
| --- | --- |
| Force | Strength |
| Agilité | Agility |
| Esprit | Spirit |
| Social | Social |
| Avantage | Advantage |
| Initiative | Initiative |
| Escamotage | Sleight of Hand |

« Sleight » est l'orthographe du terme attendu, plutôt que « slight ». Liberté de traduction accordée pour les personnages et leurs textes ; conserver les identifiants techniques, même si un nom affiché est adapté.

### Traductions proposées sans ambiguïté majeure

Athlétisme → Athletics ; Acrobaties → Acrobatics ; Discrétion → Stealth ; Arcanes → Arcana ; Investigation → Investigation ; Perception → Perception ; Survie → Survival ; Persuasion → Persuasion ; Tromperie → Deception ; Intimidation → Intimidation ; Représentation → Performance ; Perspicacité → Insight ; Dressage → Animal Handling.

Caractéristique → Attribute ; modificateur → Modifier ; compétence → Skill ; capacité → Ability (pas systématiquement Spell, car les capacités peuvent être martiales ou sociales) ; désavantage → Disadvantage ; jet de sauvegarde → Saving Throw ; seuil de sauvegarde → Save DC ; points de vie → Hit Points / HP ; MJ → GM ; PNJ → NPC ; totem → Totem ; jeton → Token ; carte cristallisée → Crystallized Card ; éveil de capacité → Ability Awakening ; maîtrise élémentaire → Elemental Mastery.

Couleur au sens ♠ ♥ ♦ ♣ → Suit ; rouge/noir → Color ; Cœurs → Hearts ; Carreaux → Diamonds ; Trèfles → Clubs ; Piques → Spades. Employer Suit Mastery pour maîtrise des couleurs et Suit Bonus pour bonus de couleur.

Action → Action ; action bonus → Bonus Action ; réaction → Reaction ; tour personnel → Turn ; round global → Round ; zone de contrôle → Zone of Control ; attaque d'opportunité → Opportunity Attack ; armure → Armor ; déflexion → Deflection ; parade → Parry ; dégâts de base → Base Damage.

Conserver les mètres et les cases, les formules, les nombres et les règles propres à Cardenveil. L'emploi de termes habituels de JDR n'importe pas les mécaniques d'un autre jeu.

### Choix terminologiques à valider

| Terme | Proposition | Alternative / enjeu |
| --- | --- | --- |
| Résilience | Resilience | Endurance sonne plus physique ; la compétence couvre notamment douleur, poison et conditions extrêmes |on garde resilience
| Culture | Lore | Knowledge est plus large ; Culture évoque plutôt les pratiques culturelles en anglais => on garde knowledge
| Compétence maîtrisée | Trained skill | Proficient est courant en JDR ; le bonus reste le double du modificateur, sans introduire de proficiency bonus Proficient c'est bien |
| Maîtrise d'arme | Weapon Mastery | Distinguer ce système des compétences entraînées oui weapon mastery|
| Valeur brute | Raw Power | Raw Value est plus littéral ; garder un terme distinct de Base Damage et ne pas laisser entendre que cela ignore l'armure Raw power est bien|
| Seuil de miss / seuil d'échec d'attaque | Miss Threshold | Fumble Threshold suggère une maladresse supplémentaire qui n'est pas nécessairement prévue miss threshold c'est bieb |
| Incantation, champ de fiche | Casting | Peut désigner la caractéristique utilisée, à distinguer d'un temps d'incantation ; vérifier les valeurs de chaque fiche avant traduction Incantation ça reste
 |
| Précipitation | Rush | Hasten Turn rend plus explicite l'anticipation du tour Rush c'est bien ; ne pas confondre avec Ruée → Dash |
| Catalyseur | Catalyst | Spellcasting Focus est plus idiomatique, mais Focus est déjà un type d'équipement dans les règles : préférer Catalyst on va garder focus |

## Ambiguïtés mécaniques à préserver et signaler

Ces points ne sont pas des autorisations de modifier les règles. Une traduction doit conserver les distinctions et les divergences tant qu'elles ne sont pas arbitrées.

1. **Tour / round / durée** : dans `combat.md`, un effet sur une créature dure jusqu'au plus tardif de deux événements (fin du prochain tour de la cible et début du prochain tour du lanceur). Les zones comptent en rounds globaux, même si le texte dit « 1 tour ». Traduire selon le contexte, jamais par remplacement global.
Tour indique un tour d'un joueur dans un round
quand a l'epoque j'utilisais beaucouo tour aulieu de round, je te permets de modifier tour par round quand c'est clair que je veux dire round mais de marquer ça quelque part
2. **Score / modificateur** : `systeme-de-base.md` donne des exemples « d20 + Force » et « d8 + Esprit », alors que des procédures détaillées utilisent le modificateur. Ne pas ajouter silencieusement « modifier » à tous les usages des caractéristiques. oui tu peux clairement ajouter Mod Force Mod esprit
et en angalis Strength Mod etc... 
et a modifier partout ces ambiguités et me les tracer dans un document de trace 
3. **Coût atteint / dépassé** : le début de `capacites.md` dit « dépasse », puis l'exemple dit « atteint au moins ». Même tension entre le seuil de sauvegarde « à dépasser » et la procédure `résultat ≥ DC`. Ok les capacités c'est >= et seuil c'est aussi >= donc atteint au moins
4. **Valeur brute** : le texte parle d'une quantité fixe de dés égale au modificateur, puis écrit `K × Mod × d6`. La rédaction anglaise ne doit pas transformer un pool de dés en multiplication d'un seul résultat. Pour l'avantage, la procédure indique de répéter le jet complet : à distinguer des dés individuels des attaques. OK a chaque fois ecrit Raw Spirit Power pour esprit ou Raw Power quand c'est pas marqué, et a chaque foisd ecris Raw power et entre parenthese la bonne formule
5. **Initiative** : `combat.md` contient à la fois une intervention une seule fois par tour de PNJ et une phrase sur une autre intervention avec un nouveau jet. Préserver le texte ou obtenir un arbitrage avant clarification éditoriale. J'ai pas compris pour l'instant préserves le texte 
6. **Sources et fiches** : les formules confirmées dans `docs/confirmed-sheet-formulas.md` incluent les tokens `max(0, 1 + modificateur)` ; `capacites.md` indique simplement le modificateur. Traduire chaque source sans recalculer ni harmoniser arbitrairement les fiches. c'est 1 + modificateur adaptes le FR et l'anglais 
7. **Mesures** : la ligne de zone indique 18 m dans son intitulé et 30 m dans sa description ; Impact mentionne 4 m dans un passage puis 3 m dans le résumé. Ce sont des divergences de source, pas des choix mlinguistiques. Ligne c'est 18m. Impact si on parle de repousser ça repousse a 5m. 


## Architecture proposée

1. Garder le français sur les URL existantes et générer une version anglaise sous `/en/`. Un bouton `FR / EN` mène à la page équivalente, mémorise le choix et conserve personnage, onglet et paramètres pertinents. L'URL explicite prévaut sur la préférence mémorisée. De base c'est français si on est dans un pays francophone, anglais sinon. avec un bouton simple pour chosiir la langue avec un drapeau Français et Anglais 
2. Créer des dictionnaires partagés pour l'interface et un glossaire versionné. Traduire les valeurs affichées sans renommer les clés de sérialisation (`force`, `agilite`, `esprit`, `nom`, etc.), IDs, symboles ou valeurs numériques. Oui crées
3. Stocker les traductions des personnages séparément, associées aux IDs et aux chemins de champs. Traduire les textes riches en préservant leur structure, les formules, les coûts et les liens. Générer les données anglaises et les fiches HTML depuis les mêmes traductions.
4. Stocker une édition anglaise séparée des sept documents Fragmented ; ne pas modifier le snapshot français ni ses empreintes pour traduire. Suivre l'empreinte du texte source afin de détecter les traductions périmées. oui les stocker en MD
5. Adapter tous les générateurs à la langue, y compris l'impression, les statistiques et les redirections. Les pages anglaises doivent être lisibles sans JavaScript comme leurs équivalents français. Oui 
6. Garder des identifiants de section stables ou une table de correspondance des ancres. Les ancres actuelles sont dérivées des titres : une traduction change donc les liens sans ce travail. oui
7. Générer un index de recherche par langue ; garder les identifiants de filtres indépendants de leurs libellés. Adapter tris, nombres décimaux et pluriels. oui
8. Transmettre explicitement la langue aux assistants. Vérifier la recherche anglaise sur le corpus et les embeddings existants, puis adapter l'index si nécessaire. Les citations doivent mener aux pages correspondantes. oui 
9. Décider séparément du téléchargement anglais : créer une copie localisée compatible si demandé, tout en conservant les archives canoniques françaises.oui 

## Vérification à prévoir lors de l'implémentation

- Couverture complète des clés et des champs textuels, avec signalement des traductions manquantes ou périmées.
- Parité des nombres, dés, formules, coûts, unités, nombres de personnages/capacités et identifiants entre les deux langues.
- Navigation FR → EN → FR sur chaque type de page ; conservation de la fiche et de l'onglet ; navigation précédente/suivante, liens directs et ancres.
- Recherche et filtres en anglais, cas sans résultats et erreurs réseau.
- Impression anglaise sans texte coupé ni tableau tronqué, y compris les longues capacités.
- Inspection mobile, lecteur d'écran et HTML sans JavaScript.
- Réponses des assistants dans la langue choisie et citations valides.
- Inventaire visuel du texte incorporé aux illustrations, non couvert par cet audit de code.

Les tests existants de pages statiques, règles, catalogue, impression, statistiques et assistants constituent les points de départ. Aucun test exécuté pour ce document d'analyse ; aucun code applicatif modifié.

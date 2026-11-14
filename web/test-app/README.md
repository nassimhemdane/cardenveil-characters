# Atelier local

Application Svelte autonome construite dans `web/public/test/`. Aucun backend,
compte ou accès Supabase. IndexedDB conserve fiche, images importées, cartes et
journal. La suppression des données du navigateur efface aussi cette sauvegarde.

Depuis ce dossier : `npm ci`, `npm test`, `npm run build`. Servir ensuite
`web/public` avec le serveur habituel du site. Le développement Vite est possible,
mais le catalogue `/data/characters.json` nécessite le serveur du site.

Les composants et le moteur dans `src/vendor` proviennent du dépôt MIT
`smuglilgoat/cardenveil-owlbear`, commit `48dc5a21b339c2fa081710ab6128ed0bfd316fa3`.
Ils sont conservés ici pour que le déploiement ne dépende pas du clone imbriqué.
La fiche conserve les six onglets, édition, import, inventaire et jets du plugin.
Les adaptateurs remplacent identité Owlbear, appels Supabase et broadcasts.

La main est montée à la racine de l'application, fixée en bas à droite et repliable.
Les commandes fixes permettent de la masquer/réafficher et d'activer une fiche
compacte déplaçable. Deux boutons circulaires à pictogramme restent au bord droit :
fiche en haut, cartes en bas. La position du compact est conservée dans le navigateur.
Le compact réutilise directement `SheetPopover.svelte` du plugin, avec ses PV,
caractéristiques, valeurs de combat, dés rapides, actions, attaque, valeur brute,
notes, favoris existants et totem. B. ATT. s'édite par clic ; une valeur vide
supprime la surcharge. Elle est enregistrée dans `derived.overrides.bonusAttaque`
de la copie locale et appliquée aux attaques dans les deux vues.
Le compact s'ouvre juste sous la navigation et grandit avec ses accordéons jusqu'au bord supérieur de la main,
avec une marge de 12 px. Au-delà, son contenu entier défile dans une zone
unique et sa barre de déplacement reste visible. La limite se recalcule
quand la main est repliée, masquée ou redimensionnée et lors du déplacement
du compact ou d'un changement de taille de fenêtre.
Aucune épingle n'est affichée ; les aspects narratifs s'affichent intégralement,
sans bouton +. Les capacités restent intégrales, sur deux colonnes sur grand
écran et une sur mobile. Leur bouton + ouvre toujours la vue détaillée.

Les dés 3D réutilisent `dice3d.js`, les modèles GLB et la simulation Three.js /
Rapier du plugin (même commit), avec dés noirs et chiffres blancs. Un iframe
local isole chaque lancer et transmet son résultat physique par postMessage,
vérifié sur origine, fenêtre et identifiant du lancer. La fiche et les attaques
consomment ce résultat ; les explosions d'attaque demandent un lancer par étape.
Sans WebGL, le repli du plugin affiche explicitement que la 3D est indisponible.
La fenêtre des dés reste en bas à gauche et suit la hauteur du viewport visible.
Le canvas respecte la résolution de l'écran et les chiffres utilisent des textures
512 px pour éviter le flou sur écran haute densité.

La main reste à 8 px du bord droit. Sa barre de commandes occupe toute la largeur
disponible ; Piocher est agrandi, vert si disponible et rouge si bloqué. Le bouton
rond reste juste au-dessus du bloc pour ne pas recouvrir les jetons. Sur les petites
largeurs, la barre se répartit sur deux lignes ; les fenêtres basses ont un défilement
du bloc avec commandes accessibles. Les tests navigateur couvrent dix formats de
320×320 à 1920×1080, portrait et paysage, ainsi que les cibles cliquables de pioche.

Les règles actuelles `docs/rules/fragmented` priment : fatigue linéaire, division
Nimbri soumise à la limite de main, repos avec cristallisation, récupération des
PV/jetons et remplissage de main. Le rythme des actions reste géré par le MJ.
Les échanges utilisent un allié fictif explicitement identifié.

`src/storage.js` isole la persistance ; `src/session.js` isole les actions locales
et l'identité. Une future connexion pourra remplacer ces adaptateurs.
La sélection `?character=<id>` copie une fiche du catalogue ; les originaux
ne sont jamais modifiés. L'import d'une autre fiche conserve la main courante.

Le build du site appelle le build Node après la génération Python. Aucun
hébergement supplémentaire ni déploiement automatique n'est créé par l'application.

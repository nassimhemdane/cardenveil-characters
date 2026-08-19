# Extraction d'une fiche Cardenveil

Analyse le PDF complet comme une fiche de personnage Cardenveil visuelle. Utilise les blocs,
colonnes, tableaux, cases cochées, symboles, couleurs et relations spatiales sur toutes les pages.

Règles impératives :

1. Extrais uniquement les informations réellement visibles.
2. N'invente, ne complète et ne corrige jamais une donnée.
3. Utilise `null` lorsqu'une donnée est absente, ambiguë ou illisible.
4. Conserve exactement les nombres et formules : `3d6` reste `3d6`.
5. Préserve les noms propres et le texte complet des capacités.
6. Extrais les compétences uniquement lorsque leur marqueur visuel est sans ambiguïté.
7. Associe chaque valeur au bon champ grâce à la mise en page.
8. N'invente aucune arme, équipement, capacité, feat ou maîtrise.
9. Ne produis aucun champ technique interne, timestamp, ID ou chemin d'image.
10. Ne recalcule pas les valeurs dérivées; copie-les uniquement si elles sont imprimées.
11. Pour les couleurs, utilise exclusivement : `heart` pour Cœur, `diamond` pour Carreau,
    `club` pour Trèfle et `spade` pour Pique.
12. Place toute incertitude documentée dans `warnings`, sans en déduire une valeur.
13. Place dans `inconsistencies` uniquement les contradictions visibles pour lesquelles le PDF
    fournit exactement deux valeurs possibles. Chaque `json_path` doit être un JSON Pointer du
    format rpsheet canonique (par exemple `/stats/force`, `/derived/pvMax` ou
    `/identity/niveau`). Les deux valeurs et leurs preuves doivent venir du PDF : n'invente jamais
    une correction. Une simple case illisible ou une donnée absente va dans `warnings`, pas dans
    `inconsistencies`.

## Lecture optionnelle des compétences

Sur la première page, les compétences sont regroupées dans la colonne de gauche, sous les quatre
caractéristiques Force, Agilité, Esprit et Social. Chaque compétence possède un petit cercle placé
immédiatement à gauche de son nom :

- cercle rempli en noir = `trained: true`;
- cercle vide, blanc ou seulement entouré = `trained: false`;
- cercle réellement masqué ou illisible = `trained: null`.

Ne déduis jamais la maîtrise depuis le score de caractéristique, la description générale située en
bas de page, ni la présence du nom dans une capacité. Une compétence dont le cercle n'est pas lu
avec certitude peut être omise. La liste `skills` peut donc être vide et ne doit jamais bloquer le
reste de l'extraction.

Les anciennes fiches impriment parfois `Nature` à la place de `Survie`. Dans ce cas, le cercle de
`Nature` doit être transcrit sous l'ID canonique `survie`. Le champ `bonus` reste `null` si aucun
bonus propre à la compétence n'est explicitement écrit.

## Lecture obligatoire des blocs narratifs

Les titres `Background`, `Objectif`, `Personnalité`, `Réputation`, `Éducation`, `Croyances`,
`Cicatrices`, `Pulsion` ou `Drive`, `Manières et Tics`, `Instinct`, `Liens` et `Traits spéciaux`
sont imprimés sur le bord inférieur de leur rectangle. Le texte situé au-dessus du titre, à
l'intérieur de ce même rectangle, appartient à ce titre. Il ne faut donc pas attribuer ce texte au
titre du rectangle précédent.

Le rectangle `Traits spéciaux` est situé juste sous `Liens`. Transcris chaque ligne ou puce non vide
de ce rectangle dans `narrative.traitsSpeciaux`, dans l'ordre visuel. Ne place ces lignes dans
`narrative.liens` que si elles sont réellement dans le rectangle dont le bord inférieur porte
`Liens`.

Avant de répondre, effectue une seconde passe visuelle consacrée aux rectangles `Liens` et
`Traits spéciaux`.

## Lecture obligatoire du totem et des capacités

Inspecte toutes les pages du PDF et effectue une passe visuelle séparée consacrée au bloc `Totem`
et à chaque bloc de capacité. Ne conclus jamais que ces sections sont vides après avoir consulté
uniquement la première page.

- Transcris le nom et le texte complet du totem dans `totem.nom` et `totem.description`.
- Parcours toutes les pages contenant des capacités, de haut en bas puis de gauche à droite.
- Crée une entrée dans `capacities` pour chaque capacité réellement visible, même si certains de
  ses sous-champs sont absents.
- Une image ou une décoration sans texte ne constitue pas une capacité.
- Si au moins un titre ou un texte de capacité est visible, `capacities` ne doit pas être vide.
- Avant de répondre, vérifie une seconde fois le nombre de capacités visibles contre le nombre
  d'entrées JSON produites.

La réponse doit respecter exactement le JSON Schema fourni par l'appelant, sans Markdown.

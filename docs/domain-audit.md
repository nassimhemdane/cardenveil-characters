# Audit du domaine Cardenveil — V1

## Corpus consulté

Le dépôt était vide. L'audit a retrouvé les huit documents de `Cardenveil rules/` (système de
base, personnage, narration, progression, totems/capacités/cartes, action/combat, résumé et
fragment), le corpus consolidé `Compain rules (layer 5)` et la fiche structurée de Mimyr. Les
fiches d'autres campagnes, cartes et documents purement applicatifs ne sont pas considérés comme
sources canoniques de règles.

Le corpus mélange des générations de règles. V1 encode seulement les concepts stables et conserve
les divergences dans `rule-ambiguities.md`.

## Concepts identifiés

- Agrégat durable: Character, Identity, Stats, Narrative, Progression.
- Références: race, capacités apprises, feats, totem, compétences maîtrisées et équipement.
- Définitions: Skill, Race, Ability, Feat, Totem, Weapon, WeaponFamily, WeaponProperty,
  Condition et DamageType.
- Valeurs fermées: Stat, SkillId, AspectType, CardSuit, ActionType et DamageTypeId.
- Règles: Rule, RuleSource, RuleStatus et catalogue Rulebook.
- Futur runtime: PV courants, cartes, tokens, conditions actives, concentration, actions et
  position. Ces concepts sont reconnus mais non modélisés en V1.

## Arborescence retenue

```text
src/cardenveil/
├── domain/{common.py,models.py}
├── content/{catalog.py,official.py}
├── rules/{rulebook.py,derived.py,resolution/README.md}
├── serialization/{rpsheet.py,migrations/README.md}
├── persistence.py
├── validation.py
└── errors.py
tests/{fixtures,test_domain.py,test_content.py,test_rules.py,test_serialization.py}
docs/{adr,domain-audit.md,rule-ambiguities.md}
```

Des modules cohésifs sont préférés à une forêt de sous-packages ne contenant qu'une classe.

## Décisions structurantes

- `Character`, pas `CharacterSheet`: l'objet représente le personnage, pas une présentation.
- Dataclasses standard library: validation locale explicite, aucune dépendance runtime.
- Le `Character.id` textuel est conservé exactement comme dans le contrat `rpsheet`.
- Définitions officielles immuables, agrégat Character mutable par opérations métier simples.
- Contenu officiel en Python typé pour cette petite V1. Un loader YAML ne se justifie pas encore.
- Le format persistant par défaut est désormais le JSON `rpsheet` avec mapping 1:1 strict.
- `player_name`, images et coordonnées de fiche restent des métadonnées applicatives.
- Les effets complexes restent naturels et reliés à des IDs; pas de moteur de règles.

## Sources encore à arbitrer

Les formules de PV, initiative, capacité maximale, tokens et parade ne deviennent pas des fonctions
canoniques avant décision. Les IDs anglais sont stables et les noms français restent de l'affichage.

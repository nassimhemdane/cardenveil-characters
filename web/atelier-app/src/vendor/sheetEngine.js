/**
 * Character Sheet API Module
 * Handles CRUD operations for character sheets stored in Supabase
 */
import { supabase } from './supabaseClient.js';
import { logError, logEvent } from './appLog.js';
import { RACES } from './deck.js';
import { mergeSheet } from './sheetMerge.js';

// ─── Shared UI constants (used by CharacterSheet + SheetPopover) ───
// French display labels for stat keys
export const STAT_LABELS = { force: 'Force', agilite: 'Agilité', esprit: 'Esprit', social: 'Social' };

export const STAT_COLORS = {
  force: '#b34c43',
  agilite: '#397a42',
  esprit: '#2d6499',
  social: '#765496'
};

/** Skill → governing stat mapping (single source for groups + labels).
 *  WIS-domain skills (perception, survie, perspicacité, dressage) map to
 *  esprit, the mental stat, since the four-stat system has no separate
 *  wisdom score. */
export const SKILL_TO_STAT = {
  athletisme: 'force',
  resilience: 'force',
  acrobaties: 'agilite',
  discretion: 'agilite',
  escamotage: 'agilite',
  arcanes: 'esprit',
  investigation: 'esprit',
  perception: 'esprit',
  culture: 'esprit',
  survie: 'esprit',
  persuasion: 'social',
  tromperie: 'social',
  intimidation: 'social',
  representation: 'social',
  perspicacite: 'social',
  dressage: 'social',
};

export const SKILL_LABELS = {
  athletisme: 'Athlétisme',
  resilience: 'Résilience',
  acrobaties: 'Acrobaties',
  discretion: 'Discrétion',
  escamotage: 'Escamotage',
  arcanes: 'Arcanes',
  investigation: 'Investigation',
  perception: 'Perception',
  culture: 'Culture',
  survie: 'Survie',
  persuasion: 'Persuasion',
  tromperie: 'Tromperie',
  intimidation: 'Intimidation',
  representation: 'Représentation',
  perspicacite: 'Perspicacité',
  dressage: 'Dressage'
};

const STAT_GROUP_LABELS = { force: 'FORCE', agilite: 'AGILITÉ', esprit: 'ESPRIT', social: 'SOCIAL' };

/** Skill groups (for display) derived from SKILL_TO_STAT, in stat order. */
export const SKILL_GROUPS = ['force', 'agilite', 'esprit', 'social'].map((stat) => ({
  stat,
  label: STAT_GROUP_LABELS[stat],
  skills: Object.keys(SKILL_TO_STAT).filter((skill) => SKILL_TO_STAT[skill] === stat),
}));

export const SUIT_LABELS = { heart: 'Cœur', spade: 'Pique', diamond: 'Carreau', club: 'Trèfle' };
export const SUIT_SYMBOLS = { heart: '♥', spade: '♠', diamond: '♦', club: '♣' };
export const SUIT_COLORS = { heart: '#b42323', spade: '#263129', diamond: '#946000', club: '#2d6d36' };

// Per-turn action tracker (3 diamond checkboxes, display only — no reset logic)
export const ACTION_CHECKS = [
  { key: 'action', label: 'ACTION' },
  { key: 'bonus', label: 'BONUS ACTION' },
  { key: 'reaction', label: 'RÉACTION' }
];

export function colorLabel(color) {
  return SUIT_LABELS[(color || '').toLowerCase()] || color || '—';
}

export function suitSymbol(color) {
  return SUIT_SYMBOLS[(color || '').toLowerCase()] || '·';
}

export function suitColor(color) {
  return SUIT_COLORS[(color || '').toLowerCase()] || '#9ca3af';
}

// Same schema keyed by suit SYMBOL (card objects carry symbols, not names).
export const SUIT_SYMBOL_COLORS = { '♥': '#f87171', '♠': '#e5e7eb', '♦': '#fbbf24', '♣': '#4ade80' };
// Same 4 hues darkened for white card faces (spade gray-200 / diamond amber-400
// are illegible at card-corner size on a light background).
export const SUIT_SYMBOL_COLORS_ON_LIGHT = { '♥': '#ef4444', '♠': '#6b7280', '♦': '#d97706', '♣': '#16a34a' };

export function suitColorBySymbol(suit, onLight = false) {
  const map = onLight ? SUIT_SYMBOL_COLORS_ON_LIGHT : SUIT_SYMBOL_COLORS;
  return map[suit] ?? (onLight ? '#6b7280' : '#9ca3af');
}

// ─── Card color scheme (local preference: 'color' schema vs classic red/black) ───
export const CARD_SCHEME_KEY = 'cardenveil-card-scheme';
const cardSchemeListeners = new Set();

export function getCardScheme() {
  try {
    return localStorage.getItem(CARD_SCHEME_KEY) === 'classic' ? 'classic' : 'color';
  } catch {
    return 'color';
  }
}

export function setCardScheme(scheme) {
  try {
    localStorage.setItem(CARD_SCHEME_KEY, scheme === 'classic' ? 'classic' : 'color');
  } catch {
    /* storage unavailable — applies locally only */
  }
  // Notifies same-runtime subscribers (cross-iframe views get the `storage` event)
  cardSchemeListeners.forEach((h) => h(scheme));
}

export function onCardSchemeChange(handler) {
  cardSchemeListeners.add(handler);
  return () => cardSchemeListeners.delete(handler);
}

/** Classic two-color card palette (red suits vs black suits). */
export function classicSuitColor(isRed) {
  return isRed ? '#dc2626' : '#111827';
}

// ─── Inventory item type color coding ───
export const ITEM_TYPE_COLORS = {
  arme: '#f87171',
  armure: '#60a5fa',
  consommable: '#4ade80',
  'équipement': '#60a5fa',
  divers: '#9ca3af'
};

export const ITEM_TYPE_OPTIONS = ['Arme', 'Équipement', 'Consommable', 'Divers'];

// Legacy type key from imports ('Armure') maps onto the merged Équipement type
export function normalizeItemType(type) {
  return String(type ?? '').trim() === 'Armure' ? 'Équipement' : type;
}

export function itemTypeColor(type) {
  return ITEM_TYPE_COLORS[String(type ?? '').trim().toLowerCase()] || '#9ca3af';
}

// ─── Race name normalization (sheet imports carry free-text race names) ───

function canonicalRace(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[\s_-]+/g, '-');
}

/**
 * Accepted spellings that are neither the id nor the label — imports and
 * hand-typed sheets carry "Khajit", "Halfelin", "Tiefling", "Drow"…
 * (canonical form = accentless, lowercase, hyphen-separated).
 */
const RACE_ALIASES = {
  // Humain
  human: 'humain', humans: 'humain', humaine: 'humain',
  // Haut-Elfe
  'high-elf': 'haut-elfe', 'high-elfe': 'haut-elfe',
  // Elfe des Bois
  'wood-elf': 'elfe-des-bois', 'elfe-sylvain': 'elfe-des-bois', 'elfe-sylvestre': 'elfe-des-bois',
  // Elfe Noir
  'dark-elf': 'elfe-noir', darkelf: 'elfe-noir', drow: 'elfe-noir', 'elfe-noire': 'elfe-noir',
  // Demi-Elfe
  'half-elf': 'demi-elfe', 'half-elfe': 'demi-elfe', halfelf: 'demi-elfe',
  // Tieffelin
  tiefling: 'tieffelin', tieflingue: 'tieffelin',
  // Aasimar
  aasimars: 'aasimar',
  // Demi-Orque
  'half-orc': 'demi-orque', 'half-orque': 'demi-orque', 'demi-orc': 'demi-orque',
  // Nain
  dwarf: 'nain', naine: 'nain', nains: 'nain', dwarve: 'nain',
  // Gobelin
  goblin: 'gobelin', gobelins: 'gobelin', goblins: 'gobelin',
  // Gnome
  gnomes: 'gnome',
  // Halfling
  halfelin: 'halfling', halfelins: 'halfling', hobbit: 'halfling', halflings: 'halfling',
  // Goliath
  goliaths: 'goliath',
  // Drakéide
  dragonborn: 'drakeide', drakeid: 'drakeide', drakeids: 'drakeide',
  // Sporelin
  sporeling: 'sporelin', sporlin: 'sporelin', sporelins: 'sporelin',
  // Mort-vivant
  undead: 'mort-vivant', revenant: 'mort-vivant', 'morts-vivants': 'mort-vivant', 'mort-vivante': 'mort-vivant',
  // Khajiit
  khajiit: 'khajeet', khajit: 'khajeet', khajet: 'khajeet', khajiits: 'khajeet',
  // Troll
  trolls: 'troll',
  // Homme-Poisson
  fishman: 'homme-poisson', 'fish-man': 'homme-poisson', 'poisson-homme': 'homme-poisson', fishfolk: 'homme-poisson',
  // Hobgoblin
  'hob-gobelin': 'hobgoblin', hobgobelins: 'hobgoblin',
  // Centaure
  centaur: 'centaure', centaures: 'centaure', centaurs: 'centaure',
  // Mécha
  mech: 'mecha', mechas: 'mecha', warforged: 'mecha', automatise: 'mecha',
  // Illithid
  illithide: 'illithid', illithids: 'illithid', mindflayer: 'illithid', 'mind-flayer': 'illithid', 'flagelleur-mental': 'illithid', flagelleur: 'illithid',
  // Firbolg
  'fir-bolg': 'firbolg', firbolgs: 'firbolg',
  // Nimbri
  nimbris: 'nimbri', nimbry: 'nimbri',
};

/**
 * Map a free-text race name to a canonical race id when recognizable
 * ("Haut Elfe" → "haut-elfe", "Khajit" → "khajeet"). Unrecognized values
 * pass through untouched so manually typed races ("Humain", …) keep their
 * text.
 * @param {unknown} race - Raw race value
 * @returns {unknown} Race id when matched, otherwise the input unchanged
 */
export function normalizeRaceName(race) {
  if (race == null) return race;
  const raw = String(race).trim();
  if (!raw) return race;
  const canon = canonicalRace(raw);
  const hit = RACES.find((r) => canonicalRace(r.id) === canon || canonicalRace(r.label) === canon);
  if (hit) return hit.id;
  return RACE_ALIASES[canon] ?? race;
}

/**
 * Display label for a race value (race id → label, anything else as-is).
 * @param {unknown} race - Race id or free text
 * @returns {string}
 */
export function raceLabel(race) {
  const value = String(race ?? '').trim();
  return RACES.find((r) => r.id === value)?.label ?? value;
}

/**
 * Racial traits, verbatim from the rulebook, in document order. Display-only
 * reference text: the reducer never reads it (see `raceTraits`). Races whose
 * passive the app cannot track (distances, vision, rests, damage types,
 * creature tracking) still list their text here — the sheet renders it.
 * @type {{ [raceId: string]: { nom: string, texte: string }[] }}
 */
export const RACE_TRAITS = {
  humain: [
    { nom: 'Polyvalence', texte: '+2 compétences supplémentaires.' },
    { nom: 'Aisance sociale', texte: '+2 jetons de Social.' }
  ],
  'haut-elfe': [
    { nom: 'Main étendue', texte: 'Vous pouvez conserver 1 carte supplémentaire en main.' },
    { nom: 'Maîtrise supplémentaire', texte: 'Vous maîtrisez 1 capacité supplémentaire.' }
  ],
  'elfe-des-bois': [
    { nom: 'Mobilité réactive', texte: 'Après avoir utilisé votre réaction, vous pouvez vous déplacer de 5 m. Si vous réagissez à une capacité non ciblée, ce déplacement est considéré comme effectué avant la capacité.' },
    { nom: 'Initiative', texte: 'Avantage au deuxième jet d\'initiative du round.' }
  ],
  'elfe-noir': [
    { nom: 'Réaction supplémentaire', texte: 'Si vous êtes hors du champ de vision d\'un ennemi, vous pouvez utiliser 1 réaction supplémentaire par tour.' },
    { nom: 'Discrétion', texte: 'Avantage aux jets de Discrétion.' }
  ],
  'demi-elfe': [
    { nom: 'Canalisation libre', texte: 'Lorsque vous utilisez une arme (attaque, parade, etc.), vous canalisez automatiquement pendant 1 round, avec une valeur égale à votre Esprit.' },
    { nom: 'Canalisation flexible', texte: 'Vous choisissez la couleur de canalisation indépendamment de l\'arme utilisée.' },
    { nom: 'Catalyseur défensif', texte: 'Vous pouvez parer avec un catalyseur, en utilisant sa valeur de canalisation à la place de la parade d\'une arme.' },
    { nom: 'Érudition mixte', texte: '+1 compétence.' }
  ],
  tieffelin: [
    { nom: 'Pioche ciblée', texte: 'Vous pouvez piocher spécifiquement du Pique 1 fois sur 2.' },
    { nom: 'Résistance', texte: 'Résistance au feu.' }
  ],
  aasimar: [
    { nom: 'Cœur supplémentaire', texte: 'Chaque fois que vous utilisez un token, quel qu\'en soit le type, invoquez également 1 carte de Cœur.' },
    { nom: 'Résistance', texte: 'Résistance aux dégâts radiants.' }
  ],
  'demi-orque': [
    { nom: 'Riposte cumulative', texte: 'Pour chaque créature vous ayant attaqué pendant le round, ajoutez votre modificateur à votre prochain jet d\'attaque ou à votre prochaine capacité infligeant des dégâts.' },
    { nom: 'Armure de survie', texte: 'Votre armure double lorsque vous avez moins de 50 % de vos PV.' }
  ],
  nain: [
    { nom: 'Points de vie supplémentaires', texte: 'Vous gagnez un nombre de PV égal à votre Force (source « Force pvs »).' },
    { nom: 'Réduction de coût', texte: 'Réduisez le coût de vos capacités de Trèfle de 1 pour chaque créature vous ayant attaqué pendant le round.' }
  ],
  gobelin: [
    { nom: 'Critique facilité', texte: 'Réduisez le seuil de critique de 1 (par exemple, 5–6 au lieu de 6 sur 1d6).' },
    { nom: 'Limite de critiques', texte: 'Maximum 3 critiques cumulés par attaque.' }
  ],
  gnome: [
    { nom: 'Faiblesse physique atténuée', texte: 'Les malus liés à une Force faible ne s\'appliquent qu\'à partir de 4 ou moins.' },
    { nom: 'Compensation du surcoût', texte: 'Si vous payez un surcoût pour une capacité, réduisez le coût de la prochaine capacité lancée du même montant.' }
  ],
  halfling: [
    { nom: 'Pioche sélective', texte: 'Lorsque vous piochez, piochez 2 cartes et défaussez-en 1.' },
    { nom: 'Relance', texte: 'Une fois par repos court, vous pouvez relancer un dé.' }
  ],
  goliath: [
    { nom: 'Force colossale', texte: 'Vous pouvez manier une arme à deux mains avec une seule main. Vous pouvez également manier deux armes polyvalentes ou deux bâtons simultanément (dual wield). Les épées longues sont considérées comme des armes de Finesse.' },
    { nom: 'Endurance des cimes', texte: 'Avantage aux jets d\'Athlétisme et résistance aux dégâts de glace.' }
  ],
  drakeide: [
    { nom: 'Héritage draconique', texte: 'Choisissez Feu, Foudre, Glace, Acide ou Poison. Vous résistez aux dégâts de cet élément et pouvez le générer pour interagir avec l\'environnement.' },
    { nom: 'Écailles draconiques', texte: 'Armure naturelle de 1, cumulable avec d\'autres sources.' },
    { nom: 'Souffle draconique', texte: 'En action bonus, infligez 1d10 dégâts de votre élément dans un cône de 4,5 m. À la place, vous pouvez retenir votre souffle pour canaliser automatiquement les capacités liées à cet élément (valeur = modificateur d\'Esprit).' },
    { nom: 'Résonance élémentaire', texte: 'Au contact d\'une source de votre élément que vous n\'avez pas générée, vous la canalisez automatiquement.' }
  ],
  sporelin: [
    { nom: 'Résistance et immunité', texte: 'Résistance au poison et immunité aux effets de saignement.' },
    { nom: 'Vulnérabilité', texte: 'Vulnérabilité aux dégâts de glace.' },
    { nom: 'Sporaissance', texte: 'Si vous ne vous déplacez pas pendant votre tour, vous activez cet état. Tant qu\'il est actif : vous récupérez un nombre de PV égal à votre déplacement ; si un ou plusieurs alliés restent pendant un round complet à moins de 3 m de vous, vous pouvez échanger gratuitement une carte avec chacun d\'eux à la fin de leur tour.' }
  ],
  'mort-vivant': [
    { nom: 'Nécrose', texte: 'Insensibilité aux dégâts nécrotiques.' },
    { nom: 'Résistance aux entraves', texte: 'Avantage aux jets de sauvegarde contre les effets restreignants.' },
    { nom: 'Insensibilité aux critiques', texte: 'Les coups critiques reçus infligent des dégâts normaux.' },
    { nom: 'Fatigue', texte: 'Ignorez les malus de fatigue jusqu\'au niveau 5.' }
  ],
  khajeet: [
    { nom: 'Griffes félines', texte: 'Vous possédez une attaque naturelle avec vos griffes (1d6, finesse). Si l\'une de vos mains est libre ou équipée d\'un catalyseur une main, vous pouvez effectuer une attaque avec vos griffes en bonus action.' },
    { nom: 'Souplesse féline', texte: 'Vous subissez moitié moins de dégâts liés aux chutes.' },
    { nom: 'Esquive instinctive', texte: 'Vous pouvez utiliser l\'action Esquiver en bonus action.' }
  ],
  troll: [
    { nom: 'Régénération totémique', texte: 'Chaque fois que vous utilisez un token, vous regagnez 2 × votre modificateur le plus élevé en points de vie (une fois par token par round / 30 min).' },
    { nom: 'Membre des Hautes Terres', texte: 'Vous ignorez les terrains difficiles.' }
  ],
  'homme-poisson': [
    { nom: 'Sens vibratoire', texte: 'En action bonus, vous pouvez maintenir votre Concentration. Tant qu\'elle est maintenue, toute créature qui se déplace d\'au moins 3 m bénéficie automatiquement de l\'effet de votre Ciblage.' },
    { nom: 'Physiologie aquatique', texte: 'Votre vitesse de nage est égale à votre déplacement et vous avez avantage à tous vos jets dans l\'eau.' },
    { nom: 'Peau glissante', texte: 'Si un liquide couvre entièrement votre zone de contrôle (rayon de 3 m), les attaques et capacités dirigées contre vous ont désavantage. Si ce liquide n\'est pas de l\'eau, un jet de Survie contextuel est nécessaire pour bénéficier de cet effet.' },
    { nom: 'Résistance au froid', texte: 'Résistance aux dégâts de froid.' },
    { nom: 'Dépendance hydrique', texte: 'Pour effectuer un repos court ou long, vous devez disposer d\'assez d\'eau pour garder votre peau immergée ou humide pendant toute la durée du repos. Un jet de Survie contextuel permet de trouver ou d\'exploiter une source d\'eau adaptée.' },
    { nom: 'Vulnérabilité au feu', texte: 'Vulnérabilité aux dégâts de feu.' }
  ],
  hobgoblin: [
    { nom: 'Discipline martiale', texte: 'Vous bénéficiez des bonus d\'armes de corps à corps avec les armes à distance (attaques d\'opportunité, parade, deuxième attaque, etc.). Vous avez avantage aux attaques d\'opportunité et pouvez vous déplacer après en avoir effectué une.' },
    { nom: 'Commandement tactique', texte: 'Vous pouvez donner vos tokens à vos alliés.' }
  ],
  centaure: [
    { nom: 'Vitesse équine', texte: 'Votre vitesse de déplacement est multipliée par 1,5.' },
    { nom: 'Morphologie quadrupède', texte: 'Avantage aux jets d\'Athlétisme pour pousser ; désavantage aux jets d\'Acrobaties.' },
    { nom: 'Angle mort', texte: 'Les attaques effectuées contre vous par derrière ont avantage.' },
    { nom: 'Charge', texte: 'Si vous parcourez au moins 10 m en ligne droite pendant votre tour, votre prochaine attaque ou capacité bénéficie d\'un avantage.' }
  ],
  mecha: [
    { nom: 'Corps résistant', texte: 'Résistance aux dégâts physiques.' },
    { nom: 'Résistance au poison', texte: 'Résistance aux dégâts de poison.' },
    { nom: 'Corps artificiel', texte: 'Vous n\'avez pas besoin de respirer et pouvez rester sous l\'eau indéfiniment.' },
    { nom: 'Immortel', texte: 'La Fatigue ne peut pas vous tuer.' },
    { nom: 'Corps modulaire', texte: 'Vous pouvez intégrer à l\'un de vos bras une arme à une main, un bouclier ou un catalyseur. L\'intégration est perdue si vous tombez inconscient.' },
    { nom: 'Auto-soin', texte: 'Les capacités vous permettant de vous soigner vous-même fonctionnent à 50 % de leur valeur.' },
    { nom: 'Fatigue mécanique', texte: 'Vous gagnez des niveaux de Fatigue par paliers de 1 et ne récupérez qu\'un niveau par repos court.' },
    { nom: 'Réparation', texte: 'Les soins classiques et les consommables de soin ne fonctionnent pas sur vous. Vous possédez un kit de réparation utilisable une fois par jour lors d\'un repos long. Effectuez un jet d\'Investigation ou d\'Escamotage : vous récupérez résultat du jet × 5 % de vos PV maximum.' },
    { nom: 'Relevage', texte: 'Lorsque vous êtes inconscient, un allié doit réussir un jet d\'Investigation ou d\'Escamotage de DC 8 + 2 × votre niveau de Fatigue pour vous relever.' },
    { nom: 'Repos mécanique', texte: 'Aucune ration n\'est nécessaire lors d\'un repos court, mais vous devez vous éteindre pendant 1 heure.' },
    { nom: 'Vulnérabilité électrique', texte: 'Vulnérabilité aux dégâts de foudre.' }
  ],
  illithid: [
    { nom: 'Harmonisation cérébrale', texte: 'Votre Harmonisation est passive autour de vous et améliore les attaques ou capacités alliées comme une Harmonisation classique. En l\'activant par une réaction, vous déclenchez une Harmonisation totale : la cible obtient avantage à ses jets d\'attaque et de capacités, en plus du bonus de base.' },
    { nom: 'Dévoration mentale', texte: 'Action bonus : dévorez le cerveau d\'une créature intelligente (Esprit > 8), morte depuis moins de 1 minute, pour récupérer 1 token d\'Esprit (maximum = modificateur d\'Esprit, minimum 1). Utilisable une fois par combat ou toutes les 30 minutes.' },
    { nom: 'Résonance de mort', texte: 'À 0 PV, vous émettez une onde psychique de 18 m infligeant modificateur d\'Esprit × 1d6 dégâts psychiques à toutes les créatures alliées autour de vous.' },
    { nom: 'Fragilité physique', texte: 'Désavantage à tous les jets de sauvegarde d\'Athlétisme.' }
  ],
  firbolg: [
    { nom: 'Force de géant', texte: 'Avantage aux jets de sauvegarde d\'Athlétisme.' },
    { nom: 'Imprégnation naturelle', texte: 'Lorsque vous utilisez Imprégner, vous pouvez imprégner votre équipement ou celui d\'un allié. L\'imprégnation dure 2 rounds.' },
    { nom: 'Combinaison élémentaire', texte: 'Vous pouvez altérer un Choc élémentaire créé par une autre créature pour produire une Combinaison élémentaire et prolonger cette combinaison jusqu\'à 2 rounds.' },
    { nom: 'Langage de la nature', texte: 'Vous pouvez communiquer avec les plantes et avez avantage aux jets de Dressage.' },
    { nom: 'Disparition naturelle', texte: 'Si vous passez l\'intégralité de votre tour sans vous déplacer et le terminez hors du champ de vision de tous les ennemis, vous devenez automatiquement Invisible. Vous pouvez également utiliser votre action pour devenir Invisible une fois par repos court.' },
    { nom: 'Lente mise en action', texte: 'Désavantage aux jets d\'Initiative.' }
  ],
  nimbri: [
    { nom: 'Nez Encombrant', texte: 'Vous avez désavantage aux jets de Perception à cause de votre gros nez.' },
    { nom: 'Compréhension Abstraite de la Magie', texte: 'Vous pouvez diviser une carte en deux parts égales, une fois par round ou une fois toutes les 30 minutes.' },
    { nom: 'Mobilité Particulière', texte: 'Une fois par round, si vous réussissez un jet d\'Acrobaties, vous obtenez un Dash gratuit.' }
  ]
};

/**
 * Traits for a race id (or an imported free-text name). Unknown races → []
 * (a manually typed race has no rulebook traits).
 * @param {unknown} race - Race id or free text
 * @returns {{ nom: string, texte: string }[]}
 */
export function raceTraits(race) {
  return RACE_TRAITS[normalizeRaceName(race)] ?? [];
}

/**
 * Whether an image-slot value is a URL (vs an emoji/glyph to render as text).
 * @param {unknown} value - Portrait/capacity/totem image value
 * @returns {boolean}
 */
export function isImageUrl(value) {
  const v = String(value ?? '');
  return /^https?:\/\//i.test(v) || v.startsWith('data:') || v.startsWith('/');
}

// ─── Equipment catalog (display data only — no dice/damage logic) ───
// Static skeleton from the equipment rules; enchantements/effets are added
// by hand on top of these entries.
export const EQUIPMENT_CATALOG = [
  {
    group: '⚔️ Épées droites — Garde',
    family: 'Épées droites',
    kind: 'arme',
    items: [
      { nom: 'Dague', de: '1d4', degats: 'tranchant/perçant', proprietes: 'Finesse, Légère, Lancer (10m), Garde' },
      { nom: 'Épée courte', de: '1d6', degats: 'tranchant/perçant', proprietes: 'Finesse, Légère, Garde' },
      { nom: 'Épée longue', de: '1d8', degats: 'tranchant/perçant', proprietes: 'Polyvalente (1d10), Garde' },
      { nom: 'Espadon (grande épée)', de: '1d12', degats: 'tranchant/perçant', proprietes: 'Deux mains, Garde' }
    ]
  },
  {
    group: '🗡 Épées courbes — Fluide',
    family: 'Épées courbes',
    kind: 'arme',
    items: [
      { nom: 'Serpe', de: '1d4', degats: 'tranchant', proprietes: 'Finesse, Légère, Fluide' },
      { nom: 'Épée courbe (cimeterre)', de: '1d6', degats: 'tranchant', proprietes: 'Finesse, Légère, Fluide' },
      { nom: 'Katana (sabre long)', de: '1d10', degats: 'tranchant', proprietes: 'Finesse, Deux mains, Fluide' },
      { nom: 'Grand sabre', de: '1d12', degats: 'tranchant', proprietes: 'Deux mains, Fluide' }
    ]
  },
  {
    group: '🪓 Haches — Brutalité',
    family: 'Haches',
    kind: 'arme',
    items: [
      { nom: 'Hachette', de: '1d6', degats: 'tranchant', proprietes: 'Légère, Lancer (10m), Brutalité' },
      { nom: 'Hache d’armes', de: '1d8', degats: 'tranchant', proprietes: 'Polyvalente (1d10), Brutalité' },
      { nom: 'Grande hache', de: '1d12', degats: 'tranchant', proprietes: 'Deux mains, Brutalité' }
    ]
  },
  {
    group: '🔨 Massues — Impact',
    family: 'Massues',
    kind: 'arme',
    items: [
      { nom: 'Gourdin', de: '1d4', degats: 'contondant', proprietes: 'Improvisée, Brute, Impact' },
      { nom: 'Gantelet de combat', de: '1d6', degats: 'contondant', proprietes: 'Léger, Impact' },
      { nom: 'Marteau de guerre', de: '1d8', degats: 'contondant', proprietes: 'Polyvalente (1d10), Impact' },
      { nom: 'Grand marteau', de: '1d12', degats: 'contondant', proprietes: 'Deux mains, Impact' }
    ]
  },
  {
    group: '🪶 Armes à allonge — Allonge',
    family: 'Armes à allonge',
    kind: 'arme',
    items: [
      { nom: 'Bâton long', de: '1d6', degats: 'contondant', proprietes: 'Allonge, Amplitude' },
      { nom: 'Lance', de: '1d8', degats: 'perçant', proprietes: 'Polyvalente (1d10), Allonge, Amplitude' },
      { nom: 'Hallebarde', de: '1d12', degats: 'tranchant', proprietes: 'Deux mains, Allonge' }
    ]
  },
  {
    group: '🏹 Arcs — Surplomb',
    family: 'Arcs',
    kind: 'arme',
    items: [
      { nom: 'Arc court', de: '1d6', degats: 'perçant', proprietes: 'Distance, Finesse, Deux mains, Surplomb' },
      { nom: 'Arc long', de: '1d8', degats: 'perçant', proprietes: 'Distance, Finesse, Deux mains, Surplomb' }
    ]
  },
  {
    group: '🔫 Arbalètes — Perforant',
    family: 'Arbalètes',
    kind: 'arme',
    items: [
      { nom: 'Arbalète de poing', de: '1d4', degats: 'perçant', proprietes: 'Distance, Finesse, Brute, Tir léger, Secondaire, Perforant' },
      { nom: 'Arbalète', de: '1d8', degats: 'perçant', proprietes: 'Distance, Finesse, Deux mains, Perforant' },
      { nom: 'Arbalète lourde', de: '1d12', degats: 'perçant', proprietes: 'Distance, Finesse, Deux mains, Recharge, Perforant' }
    ]
  },
  {
    group: '🔮 Catalyseurs',
    family: 'Catalyseurs',
    kind: 'arme',
    items: [
      { nom: 'Focus', de: '1d4', degats: 'magique/élémentaire', proprietes: 'Distance, Brute, Tir léger, Secondaire, Catalyseur' },
      { nom: 'Bâton', de: '1d8', degats: 'magique/élémentaire', proprietes: 'Distance, Deux mains, Catalyseur' }
    ]
  },
  {
    group: '🛡️ Boucliers — Rempart',
    family: 'Boucliers',
    kind: 'arme',
    items: [{ nom: 'Bouclier', de: '1d4', degats: 'contondant', proprietes: 'Brute, Secondaire, Rempart' }]
  },
  {
    group: 'Armes uniques',
    family: 'Armes uniques',
    kind: 'arme',
    items: [
      // Racial weapon of the Khajeet (griffes) — épée courte d6 profile
      { nom: 'Griffe', de: '1d6', degats: 'tranchant', proprietes: 'Finesse, Légère, Naturelle' },
      { nom: 'Faux', de: '1d10', degats: 'tranchant', proprietes: 'Deux mains, Fluide, Allonge, Amplitude' },
      { nom: 'Rapière', de: '1d8', degats: 'perçant', proprietes: 'Finesse, Contre d’Estoc' },
      { nom: 'Fouet', de: '1d6', degats: 'tranchant', proprietes: 'Finesse, Entrave' },
      { nom: 'Fist weapons', de: '1d4', degats: 'contondant', proprietes: 'Impact, Hybride' },
      { nom: 'Fléau', de: '1d8', degats: 'perçant', proprietes: 'Déstabilisation' }
    ]
  },
  {
    group: '🛡️ Équipement',
    family: 'Équipement',
    kind: 'armure',
    items: [
      { nom: 'Plastron', de: '', degats: '', slot: 'plastron', proprietes: 'Déflexion + Armure (plastron)' },
      { nom: 'Casque', de: '', degats: '', slot: 'casque', proprietes: 'Déflexion + Volonté (casque)' },
      { nom: 'Bottes', de: '', degats: '', slot: 'bottes', proprietes: 'Déflexion + Vitesse (bottes)' },
      { nom: 'Gantelets', de: '', degats: '', slot: 'gantelets', proprietes: 'Déflexion + Initiative (gantelets)' },
      { nom: 'Cape', de: '', degats: '', slot: 'cape', proprietes: 'Déflexion (cape)' },
      { nom: 'Amulette', de: '', degats: '', slot: 'amulette', proprietes: 'Enchantement (amulette)' },
      { nom: 'Anneau', de: '', degats: '', slot: 'anneau', proprietes: 'Enchantement (anneau)' }
    ]
  },
  {
    group: '🧪 Consommables',
    family: 'Consommables',
    kind: 'consommable',
    items: [
      { nom: 'Potion de soin', effet: 'Soigne 4d10 PV', quantite: 1 },
      { nom: 'Potion de buff', effet: 'Buff', quantite: 1 },
      { nom: 'Huile d’imprégnation', effet: 'Effet d’imprégnation d’arme', quantite: 1 },
      { nom: 'Parchemin', effet: 'Sort contenu dans le parchemin', quantite: 1 },
      { nom: 'Nourriture', effet: 'Effet', quantite: 1 },
      { nom: 'Poudre', effet: 'Effet', quantite: 1 },
      { nom: 'Bombe à dégâts', effet: '8d10 dégâts', quantite: 1 },
      { nom: 'Bombe à effet', effet: 'Effet', quantite: 1 },
      { nom: 'Munition spéciale', effet: 'Effet appliqué à la munition', quantite: 1 },
      { nom: 'Piège', effet: 'Effet du piège', quantite: 1 },
      { nom: 'Cristal', effet: 'Piocher une carte', quantite: 1 },
      { nom: 'Carte cristallisée', effet: 'Effet de la carte cristallisée', quantite: 1 },
      { nom: 'Ingrédient alchimique', effet: 'Effet', quantite: 1 }
    ]
  }
];

/**
 * Condensed family property summaries (source: CARDENVEIL.md "Famille" sections).
 * Keyed by family name; used by the item editor to auto-fill `familySummary`
 * when a family is chosen, and as the family dropdown list.
 */
export const FAMILY_SUMMARIES = {
  'Épées droites': 'Tranchant ou perçant au choix ; parade au dé/2 (Force possible) ; parer une mêlée donne l\'avantage à la prochaine attaque.',
  'Épées courbes': 'Tranchant ; Danse offensive (attaquer avec désavantage → avantage à la prochaine attaque ce round) ; la cible a désavantage à ses attaques d\'opportunité contre vous.',
  'Haches': 'Tranchant ; Brutalité : critique = 2 dés de dégâts, une paire sur les dés donne un nouveau critique.',
  'Massues': 'Contondant ; Impact ignore l\'armure passive et réduit la Parade de moitié ; critique = jet d\'Athlétisme pour repousser de 4 m.',
  'Armes à allonge': 'Portée 3 m ; attaque d\'opportunité quand une créature entre (1,5 m) ou sort (3 m) de la zone étendue.',
  'Arcs': 'Surplomb : avantage en tirant depuis une surélévation ≥ 5 m.',
  'Arbalètes': 'Perforante : ignore l\'armure passive, divise la Parade ; commence le combat rechargée.',
  'Catalyseurs': "Utilisent l'Esprit et la mécanique de canalisation.",
  'Boucliers': 'Rempart : armure passive indépendante de la Force, parade personnalisée ; Bastion fait parer automatiquement ; parade parfaite = renversement ; 10 en Force requis.',
  'Équipement': '',
  'Armes uniques': '',
};

/**
 * Weapon properties as a fixed vocabulary: id (accent-free, stored), label
 * (displayed) and the rulebook text (hover tooltip). Source: the GM's
 * temporary property list — a full redesign is announced, so this stays a
 * plain list with no rule engine behind it.
 */
export const PROPERTY_TAGS = [
  { id: 'finesse', label: 'Finesse', desc: 'Utilise Force ou Agilité pour les jets d’attaque et de dégâts.' },
  { id: 'legere', label: 'Légère', desc: 'Peut être utilisée pour une attaque à deux armes.' },
  { id: 'polyvalente', label: 'Polyvalente', desc: 'Peut être utilisée à une main ou à deux mains (dégâts augmentés).' },
  { id: 'deux-mains', label: 'Deux mains', desc: 'Doit être maniée avec deux mains.' },
  { id: 'lancer', label: 'Lancer', desc: 'Peut être lancée à distance, portée indiquée.' },
  { id: 'distance', label: 'Distance', desc: 'Arme de tir, attaque à distance, doit utiliser l’Agilité.' },
  { id: 'improvisee', label: 'Improvisée', desc: 'Arme de fortune.' },
  { id: 'brute', label: 'Brute', desc: 'L’arme ne peut pas infliger de coups critiques.' },
  { id: 'tir-leger', label: 'Tir léger', desc: 'Peut tirer en bonus action ou en action mais pas les deux.' },
  { id: 'recharge', label: 'Recharge', desc: 'Nécessite une bonus action pour recharger avant de tirer (commence rechargée).' },
  { id: 'secondaire', label: 'Secondaire', desc: 'Peut s’équiper sur la main secondaire en plus d’une arme non légère.' },
  { id: 'amplitude', label: 'Amplitude', desc: 'À votre portée maximale (3 m), l’arme bénéficie de la propriété Finesse.' },
  { id: 'garde', label: 'Garde', desc: 'Épées droites : tranchant ou perçant ; Parade = dé/2, versatile (Force possible) ; parer une mêlée donne avantage à la prochaine attaque contre l’assaillant.' },
  { id: 'brutalite', label: 'Brutalité', desc: 'Haches : sur un critique, lancez deux dés et gardez la somme ; une paire donne un nouveau critique.' },
  { id: 'impact', label: 'Impact', desc: 'Masses : ignore l’armure passive, réduit la Parade de moitié ; sur un critique, test d’Athlétisme ou repoussé de 3 m.' },
  { id: 'fluide', label: 'Fluide', desc: 'Épées courbes : attaquer avec désavantage donne avantage à la prochaine attaque du round ; la cible a désavantage à ses attaques d’opportunité contre vous.' },
  { id: 'allonge', label: 'Allonge', desc: 'Frappe à 3 m ; attaque d’opportunité quand une créature entre (1,5 m) ou sort (3 m) de la zone.' },
  { id: 'surplomb', label: 'Surplomb', desc: 'Arcs : avantage si le tireur est à 5 m ou plus au-dessus de sa cible.' },
  { id: 'perforant', label: 'Perforant', desc: 'Arbalètes : ignore l’armure passive et divise par deux la Parade de la cible.' },
  { id: 'rempart', label: 'Rempart', desc: 'Boucliers : armure passive indépendante de la Force et parade propre ; une parade parfaite en mêlée renverse l’adversaire.' },
  { id: 'contre-destoc', label: 'Contre d’Estoc', desc: 'Rapière : attaqué en mêlée, donnez avantage à l’ennemi, parez, puis attaquez immédiatement gratuitement.' },
  { id: 'entrave', label: 'Entrave', desc: 'Fouet : attaques d’opportunité avec désavantage ; si elles touchent, test d’Escamotage contre l’Athlétisme pour mettre à terre.' },
  { id: 'destabilisation', label: 'Déstabilisation', desc: 'Fléau : sur un critique, la cible a désavantage à sa prochaine attaque.' },
  { id: 'double-frappe', label: 'Double Frappe', desc: 'Twinblades : action + bonus action pour 2d8 + 2×FOR ; deux dés identiques = critique automatique.' },
  { id: 'hybride', label: 'Hybride', desc: 'L’arme compte comme Finesse pour l’Agilité (déjà comprise dans le bonus) : dégâts = dé + bonus, et chaque critique ajoute (bonus − max(Force, 0)) — une Force négative n’est pas prise en compte. L’engagement ajoute max(Force, 0) + max(Agilité, 0), et chaque critique ajoute max(Agilité, 0) de plus.' },
  { id: 'catalyseur', label: 'Catalyseur', desc: 'Utilise l’Esprit pour l’attaque et permet la canalisation.' },
  { id: 'naturelle', label: 'Naturelle', desc: 'Arme naturelle (griffes) : toujours disponible, sans équipement.' },
];

const PROPERTY_BY_ID = new Map(PROPERTY_TAGS.map((t) => [t.id, t]));
const PROPERTY_BY_LABEL = new Map(PROPERTY_TAGS.map((t) => [normalizePropertyText(t.label), t.id]));
// Free-text spellings that differ from the tag label (the catalogue had "Léger"
// for the Gantelet de combat before the property list settled on "Légère").
PROPERTY_BY_LABEL.set('leger', 'legere');

/** Accent/case/punctuation-free key used to match a legacy free-text property. */
function normalizePropertyText(text) {
  return String(text ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[’']/g, '')
    .replace(/\s*\([^)]*\)\s*/g, ' ') // "Polyvalente (1d10)" → "polyvalente"
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Tags of a weapon, as ids. New sheets store `tags: string[]`; a legacy
 * free-text `proprietes` string is parsed on the fly, so both models read the
 * same way until the sheet is migrated.
 * @param {Object} [weapon] - Weapon
 * @returns {string[]} Property tag ids
 */
export function weaponTags(weapon) {
  const stored = Array.isArray(weapon?.tags) ? weapon.tags.filter((id) => PROPERTY_BY_ID.has(id)) : [];
  if (stored.length) return stored;
  const legacy = weapon?.proprietes ?? weapon?.['propriétés'] ?? '';
  return String(legacy)
    .split(',')
    .map((part) => PROPERTY_BY_LABEL.get(normalizePropertyText(part)))
    .filter(Boolean);
}

/** Property tags with their label/description, for display. */
export function weaponTagInfo(weapon) {
  return weaponTags(weapon).map((id) => PROPERTY_BY_ID.get(id)).filter(Boolean);
}

/** Property ids → the display string ("Finesse, Légère"). */
export function tagsToText(ids = []) {
  return ids.map((id) => PROPERTY_BY_ID.get(id)?.label).filter(Boolean).join(', ');
}

/** Free-text properties → tag ids (unknown words are dropped). */
export function parsePropertyText(text) {
  return String(text ?? '')
    .split(',')
    .map((part) => PROPERTY_BY_LABEL.get(normalizePropertyText(part)))
    .filter(Boolean);
}

/**
 * Format of a weapon as stored in a sheet.
 */
export const WEAPON_FIELDS = ['nom', 'de', 'icon', 'bonus', 'degats', 'scaling', 'raretePrix', 'description'];

/**
 * Convert a weapon document to the current shape: tags + scaling + description,
 * the legacy forceAgi / avantage / critique / notes / perfection removed.
 * Idempotent — a migrated weapon is returned unchanged.
 * @param {Object} [weapon] - Weapon, possibly in the old shape
 * @returns {Object} Weapon in the current shape
 */
export function migrateWeapon(weapon = {}) {
  const w = { ...weapon };
  if (!Array.isArray(w.tags)) w.tags = parsePropertyText(w.proprietes ?? w['propriétés'] ?? '');
  if (w.scaling === undefined) w.scaling = normalizeStatName(w.forceAgi) ?? '';
  if (w.description === undefined) w.description = w.notes ?? '';
  if (typeof w.finesse !== 'boolean') {
    // One-time default from the tags; the GM's checkbox wins from then on.
    w.finesse = w.tags.includes('finesse');
  }
  delete w.proprietes;
  delete w['propriétés'];
  delete w.forceAgi;
  delete w.notes;
  delete w.avantage;
  delete w.critique;
  delete w.perfection;
  return w;
}

/**
 * Migrate every weapon of a sheet (see migrateWeapon). Returns the same sheet
 * object when nothing had to change, so callers stay allocation-free.
 * @param {Object} sheet - Character sheet
 * @returns {Object} Sheet with migrated weapons
 */
export function migrateSheet(sheet) {
  if (!sheet || !Array.isArray(sheet.weapons) || !sheet.weapons.length) return sheet;
  let changed = false;
  const weapons = sheet.weapons.map((w) => {
    const next = migrateWeapon(w);
    // Content compare, not key count: a value-only fix (a `tags` string, an
    // odd `scaling`) must also be written back.
    if (JSON.stringify(next) === JSON.stringify(w ?? {})) return w;
    changed = true;
    return next;
  });
  return changed ? { ...sheet, weapons } : sheet;
}

/**
 * Editable fields per inventory item type (order = form order). Fields not
 * listed stay in the data but are not rendered by the editor — imports carry
 * a blanket field dump (weaponName, parade, …) that mismatches most types.
 */
export const ITEM_FIELDS = {
  Arme: ['icon', 'slot', 'family', 'catalystColor', 'raretePrix', 'degats', 'attributs', 'description'],
  Équipement: ['icon', 'slot', 'family', 'raretePrix', 'attributs', 'description'],
  Consommable: ['icon', 'quantite', 'raretePrix', 'attributs', 'description'],
  Divers: ['icon', 'quantite', 'raretePrix', 'attributs', 'description'],
};

/**
 * Fields for an item type, falling back to the Divers set. The legacy
 * 'Armure' type maps onto the merged Équipement type.
 * @param {unknown} type - Item type
 * @returns {string[]}
 */
export function itemFields(type) {
  const t = normalizeItemType(String(type ?? '').trim());
  return ITEM_FIELDS[t] ?? ITEM_FIELDS.Divers;
}

/**
 * Stat fields an item must expose to fill its equipment slot.
 * Anneau/amulette carry an enchantement, the worn pieces their stat fields
 * (deflexion/armure/volonte/initiative/vitesse) — these are what
 * equipmentStats()/computeDerived() sum.
 */
export const SLOT_FIELDS = {
  anneau: ['enchantement'],
  amulette: ['enchantement'],
  casque: ['deflexion', 'volonte'],
  plastron: ['deflexion', 'armure'],
  gantelets: ['deflexion', 'initiative'],
  bottes: ['deflexion', 'vitesse'],
  cape: ['deflexion'],
};

/**
 * Fields for an item of the given type; when it is a slotted Équipement
 * piece the generic attributs field is replaced by the slot's stat fields.
 * @param {unknown} type - Item type
 * @param {unknown} slot - Equipment slot key ('' when unassigned)
 * @returns {string[]}
 */
export function itemFieldsFor(type, slot) {
  if (SLOT_FIELDS[slot]) {
    // Equipment exposes the slot's own stat fields (deflexion/armure/…): those
    // are what equipmentStats()/computeDerived() sum. The family summary is
    // deliberately absent — equipment has no family rules to read.
    return ['icon', 'slot', 'family', 'raretePrix', ...SLOT_FIELDS[slot], 'description'];
  }
  return itemFields(type);
}

/**
 * Default emoji icon per catalog family, used when a template creates an
 * item/weapon without one.
 */
export const FAMILY_ICONS = {
  'Épées droites': '🗡️',
  'Épées courbes': '🗡️',
  'Haches': '🪓',
  'Massues': '🔨',
  'Armes à allonge': '🔱',
  'Arcs': '🏹',
  'Arbalètes': '🔫',
  'Catalyseurs': '🪄',
  'Boucliers': '🛡️',
  'Armes uniques': '⚔️',
  'Équipement': '🛡️',
  'Consommables': '🧪',
};

// Default icons for the Équipement slot pieces (more specific than the family icon)
export const ITEM_ICONS = {
  Plastron: '🛡️',
  Casque: '⛑️',
  Bottes: '🥾',
  Gantelets: '🧤',
  Cape: '🧥',
  Amulette: '◈',
  Anneau: '💍',
  // Consumable templates
  'Potion de soin': '🧪',  'Potion de buff': '✨',
  'Huile d’imprégnation': '🛢️',
  'Parchemin': '📜',
  'Nourriture': '🍖',
  'Poudre': '🌫️',
  'Bombe à dégâts': '💥',
  'Bombe à effet': '💣',
  'Munition spéciale': '🎯',
  'Piège': '🪤',
  'Cristal': '💎',
  'Carte cristallisée': '🃏',
  'Ingrédient alchimique': '🌿',
  // Natural/racial weapons
  'Griffe': '🐾',
  'Gantelet de combat': '🥊',
};

/**
 * Find a catalog entry by name (returns it with its group + kind + family).
 * @param {string} [nom] - Catalog item name
 * @returns {Object|null} { nom, de, degats, proprietes, group, family, kind }
 */
export function findEquipmentTemplate(nom) {
  if (!nom) return null;
  for (const group of EQUIPMENT_CATALOG) {
    const hit = group.items.find((item) => item.nom === nom);
    if (hit) return { ...hit, group: group.group, family: group.family, kind: group.kind };
  }
  return null;
}

/**
 * Item object derived from a catalogue template (no sheet involved). This is
 * what the add popup pre-fills its form with, so the form and the creation
 * share one set of defaults.
 * @param {string} templateName - Catalogue name ('' = blank Divers item)
 * @param {number} [quantity] - Consumable quantity (1-99, defaults to the template)
 * @returns {Object} Inventory item
 */
export function itemFromTemplate(templateName, quantity) {
  const tpl = findEquipmentTemplate(templateName);
  const fam = tpl?.family ?? '';
  const consumable = tpl?.kind === 'consommable';
  const qty = Math.max(1, Math.min(99, Math.round(Number(quantity) || tpl?.quantite || 1)));
  return {
    type: tpl ? (consumable ? 'Consommable' : 'Équipement') : 'Divers',
    icon: tpl ? (ITEM_ICONS[tpl.nom] ?? FAMILY_ICONS[fam] ?? '') : '',
    slot: tpl?.slot ?? '',
    name: tpl?.nom ?? '',
    ...(consumable
      ? { quantite: qty, attributs: tpl?.effet ?? '' }
      : {
          degats: tpl?.de ? `${tpl.de}${tpl.degats ? ` ${tpl.degats}` : ''}` : '',
          family: fam,
          ...(fam === 'Catalyseurs' ? { catalystColor: '' } : {}),
          attributs: tpl?.proprietes ?? ''
        }),
    description: ''
  };
}

/**
 * Weapon object derived from a catalogue template (no sheet involved).
 * `finesse: null` means "not chosen by the GM": the attack roll then follows
 * the Finesse tag and the character's stats (Agilité ≥ Force), as the rule says.
 * @param {string} templateName - Catalogue name ('' = blank weapon)
 * @returns {Object} Weapon
 */
export function weaponFromTemplate(templateName) {
  const tpl = findEquipmentTemplate(templateName);
  const tags = tpl ? parsePropertyText(tpl.proprietes) : [];
  return {
    icon: tpl ? (ITEM_ICONS[tpl.nom] ?? FAMILY_ICONS[tpl.family] ?? '') : '',
    nom: tpl?.nom ?? '',
    de: tpl?.de ?? '',
    degats: tpl?.degats ?? '',
    bonus: '',
    scaling: '',
    finesse: null,
    tags,
    raretePrix: '',
    description: '',
    equipped: false
  };
}

/**
 * Add a catalogue item to a sheet's inventory (prepended: newest first).
 * Returns a NEW sheet; shared by the ÉDITION add-buttons, the in-sheet add
 * popup and the GM sheet modal.
 * @param {Object} sheet - Character sheet
 * @param {string} templateName - Catalogue name ('' for a blank item)
 * @param {number} [quantity] - Consumable quantity (1-99, defaults to the template)
 * @param {Object} [draft] - Values edited in the add form (win over the template)
 * @returns {Object} New sheet with the item added
 */
export function withItemFromTemplate(sheet, templateName, quantity, draft) {
  const item = { ...itemFromTemplate(templateName, quantity), ...(draft ?? {}) };
  return { ...sheet, inventoryItems: [item, ...(sheet?.inventoryItems ?? [])] };
}

/**
 * Add a catalogue weapon to a sheet (prepended, unequipped). Returns a NEW sheet.
 * @param {Object} sheet - Character sheet
 * @param {string} templateName - Catalogue name ('' for a blank weapon)
 * @param {Object} [draft] - Values edited in the add form (win over the template)
 * @returns {Object} New sheet with the weapon added
 */
export function withWeaponFromTemplate(sheet, templateName, draft) {
  const weapon = { ...weaponFromTemplate(templateName), ...(draft ?? {}) };
  return { ...sheet, weapons: [weapon, ...(sheet?.weapons ?? [])] };
}

/** Signature of the stock Khajeet griffe the game used to auto-add. */
const STOCK_GRIFFE = { nom: 'Griffe', de: '1d6', proprietes: 'Finesse, Légère, Naturelle', icon: '🐾' };

/**
 * Remove the stock Khajeet griffe from a sheet's weapons: the claws are now a
 * built-in attack option in the compact sheet (see SheetPopover), not an
 * inventory entry. Only an untouched stock entry is removed — a renamed or
 * edited one is kept.
 * @param {Object} sheet - Character sheet
 * @returns {Object} The same sheet, or a new one without the stock griffe
 */
export function stripStockGriffe(sheet) {
  const weapons = sheet?.weapons ?? [];
  const kept = weapons.filter(
    (w) =>
      !(
        w?.nom === STOCK_GRIFFE.nom &&
        w?.de === STOCK_GRIFFE.de &&
        (w?.proprietes ?? '') === STOCK_GRIFFE.proprietes &&
        (w?.icon ?? '') === STOCK_GRIFFE.icon
      )
  );
  return kept.length === weapons.length ? sheet : { ...sheet, weapons: kept };
}

/**
 * Detect the action type of a capacity from its free-text usage field.
 * "Bonus action" must be checked before "action"; "Réaction" before both.
 * @param {string} usage - Free-text usage (e.g. "Bonus action / Concentration")
 * @returns {{label: string, color: string}|null} Colored type badge or null
 */
export function capacityType(usage) {
  const u = (usage || '').toLowerCase();
  if (u.includes('réaction') || u.includes('reaction')) {
    return { label: 'RÉACTION', color: '#a83f38' };
  }
  if (u.includes('bonus')) {
    return { label: 'BONUS ACTION', color: '#2d6d36' };
  }
  if (u.includes('action')) {
    return { label: 'ACTION', color: '#275d91' };
  }
  if (u.includes('concentration')) {
    return { label: 'CONCENTRATION', color: '#754a97' };
  }
  return null;
}

/**
 * Create a default empty character sheet matching the full JSON structure
 */
export function createEmptyCharacterSheet() {
  return {
    schemaVersion: 1,
    templateId: 'cardenveil-standard',
    identity: {
      nom: '',
      joueur: '',
      niveau: 1,
      race: '',
      alignement: '',
      age: '',
      taille: '',
      poids: '',
      yeux: '',
      peau: '',
      cheveux: '',
      diceColor: ''
    },
    portrait: '',
    stats: {
      force: 10,
      agilite: 10,
      esprit: 10,
      social: 10
    },
    progression: {
      xpDepenses: 0,
      xpDisponibles: 0
    },
    derived: {
      pvMax: 0,
      bonusPv: 0,
      pvActuels: 0,
      pvTemporaires: 0,
      mouvement: 0,
      initiative: 0,
      perceptionPassive: 0,
      seuilSauvegarde: 0,
      seuilMiss: 1,
      canalisation: 0,
      bonusAttaque: 0,
      inspiration: false,
      fatigue: 0,
      mort: 0,
      volonte: 0
    },
    defense: {
      parade: 0,
      armure: 0,
      deflexion: 0,
      gardeBonus: 0,
      bonus: 0
    },
    resources: {
      or: 0,
      rations: 0,
      cartesEtTokens: '',
      tokens: {
        force: 3,
        agilite: 3,
        esprit: 3,
        social: 3
      }
    },
    skills: {
      athletisme: { trained: false, bonus: 0 },
      resilience: { trained: false, bonus: 0 },
      acrobaties: { trained: false, bonus: 0 },
      discretion: { trained: false, bonus: 0 },
      escamotage: { trained: false, bonus: 0 },
      arcanes: { trained: false, bonus: 0 },
      investigation: { trained: false, bonus: 0 },
      perception: { trained: false, bonus: 0 },
      culture: { trained: false, bonus: 0 },
      survie: { trained: false, bonus: 0 },
      persuasion: { trained: false, bonus: 0 },
      tromperie: { trained: false, bonus: 0 },
      intimidation: { trained: false, bonus: 0 },
      representation: { trained: false, bonus: 0 },
      perspicacite: { trained: false, bonus: 0 },
      dressage: { trained: false, bonus: 0 }
    },
    weapons: [],
    inventory: {
      equipement: '',
      inventaire: '',
      totem: ''
    },
    totem: {
      nom: '',
      description: '',
      image: ''
    },
    narrative: {
      background: '',
      objectif: '',
      liens: '',
      traitsSpeciaux: [],
      personnalite: '',
      reputation: '',
      education: '',
      croyances: '',
      cicatrices: '',
      pulsion: '',
      maniesEtTics: '',
      instinct: ''
    },
    capacities: [],
    abilityControls: {
      cardMin: 1,
      cardMax: 13,
      knownAbilities: 0,
      maxPreparedAbilities: 0,
      colorReductions: {
        spade: 0,
        heart: 0,
        diamond: 0,
        club: 0
      }
    },
    equipment: {
      casque: { nom: '', raretePrix: '', deflexion: '', volonte: '', enchantement: '', description: '' },
      plastron: { nom: '', raretePrix: '', deflexion: '', armure: '', enchantement: '', description: '' },
      gantelets: { nom: '', raretePrix: '', deflexion: '', initiative: '', enchantement: '', description: '' },
      bottes: { nom: '', raretePrix: '', deflexion: '', vitesse: '', enchantement: '', description: '' },
      anneau: { nom: '', raretePrix: '', enchantement: '', description: '' },
      amulette: { nom: '', raretePrix: '', enchantement: '', description: '' },
      cape: { nom: '', raretePrix: '', enchantement: '', description: '' }
    },
    actions: [],
    reactions: [],
    tokens: [],
    weaponMasteries: [],
    elementalMasteries: [],
    inventoryItems: [],
    feats: [],
    evolutions: [],
    notes: '',
    pinnedSkills: [],
    pinnedCapacities: [],
    customRolls: [],
    actionChecks: { action: false, bonus: false, reaction: false }
  };
}

/**
 * Fetch a character sheet for a specific player in a room
 * @param {string} playerId - OBR player ID
 * @param {string} roomId - OBR room ID
 * @param {{ trackBase?: boolean }} [options] - `trackBase: false` for a fetch
 *   whose row is NOT applied to the caller's local copy (a portrait or
 *   actionChecks read, the popover's reconcile poll): advancing the base to a
 *   document the caller is not using would let the caller's stale copy be
 *   written without a conflict, which is the lost update the CAS prevents.
 * @returns {Promise<Object|null>} Character sheet data or null if not found
 */
export async function fetchCharacterSheet(playerId, roomId, { trackBase = true } = {}) {
  try {
    const { data, error } = await supabase
      .from('character_sheets')
      .select('*')
      .eq('player_id', playerId)
      .eq('room_id', roomId)
      .single();

    if (error) {
      if (error.code === 'PGRST116') {
        // No rows returned - sheet doesn't exist yet. An applying caller seeds
        // its local copy from that empty sheet, so that is its base: the empty
        // document, not `{}` (against `{}` every leaf of a default sheet looks
        // like a local change, so the first-save race would overwrite the row
        // another frame just created instead of merging onto it).
        if (trackBase) healSheetBase(playerId, roomId, 0, createEmptyCharacterSheet());
        return null;
      }
      throw error;
    }

    // Fetched documents are what local edits start from: they are the base of
    // the next save's three-way merge. Only when the caller applies this row.
    // Weapons are migrated on the way in (legacy forceAgi/notes/proprietes →
    // scaling/description/tags) so every frame reads one model.
    const migrated = migrateSheet(data.data);
    const row = migrated === data.data ? data : { ...data, data: migrated };
    if (trackBase) rememberSheetBase(playerId, roomId, row.version, row.data);
    return row;
  } catch (err) {
    logError('sheet_fetch_failed', err, { roomId, playerId });
    throw err;
  }
}

// ─── Save concurrency: version + three-way merge ───────────────────────────
// A save writes the WHOLE document, so two frames that read the same sheet and
// each edit a field used to clobber each other with no error. Saves now go
// through the `apply_character_sheet` compare-and-swap RPC (migration
// 20261028): on a version conflict the local delta is re-applied on top of the
// server's newer document with `mergeSheet()` and the RPC is retried.
//
// This map remembers the document each local copy was derived from, keyed by
// player:room, so the 13 whole-document call sites keep their signature. It is
// fed by a fetch that the caller applies (`trackBase`, see
// fetchCharacterSheet), by a row the caller adopts as its local copy (realtime,
// same-origin broadcast — see healSheetBase), by a conflict snapshot and by a
// successful save — never by a fetch whose row the caller does not apply (the
// popover's reconcile poll): a base that ran ahead of the local document would
// let the stale document be written without a conflict — the very lost update
// this replaces. A base one version behind only costs one extra merge
// round-trip.
// A conflict against a base that was never recorded is refused (see
// saveCharacterSheet): merging against no base would present a silent
// whole-document overwrite as a merge.
const SHEET_BASES = new Map();
const MAX_SHEET_SAVE_ATTEMPTS = 3;
// Only PGRST202 is unambiguous: it is PostgREST's own "function not in the
// schema cache". 42883 is Postgres' undefined_function, forwarded verbatim from
// INSIDE a function body — and PGRST002 is a "cannot reach the database" outage;
// neither may downgrade a save to the unguarded upsert.
const MISSING_RPC_CODE = 'PGRST202';
let casMissingLogged = false;

const sheetBaseKey = (playerId, roomId) => `${playerId}:${roomId}`;

function rememberSheetBase(playerId, roomId, version, data) {
  if (!data) return;
  // Snapshot, not the live object: callers keep editing the document they
  // saved (Svelte $state proxies, edit buffers), and a base mutated in place
  // would look like "no local change" on the next conflict.
  let snapshot = data;
  try {
    snapshot = JSON.parse(JSON.stringify(data));
  } catch {
    /* circular / unserialisable: keep the reference rather than fail the save */
  }
  SHEET_BASES.set(sheetBaseKey(playerId, roomId), {
    version: Number.isFinite(Number(version)) ? Number(version) : 0,
    data: snapshot,
  });
}

/** Drop the remembered base (sheet deleted or re-created). */
export function forgetSheetBase(playerId, roomId) {
  SHEET_BASES.delete(sheetBaseKey(playerId, roomId));
}

/**
 * Record a base for a document the caller just adopted as its local copy (a
 * realtime row it applied, a same-origin broadcast, or the empty sheet a
 * `PGRST116` fetch stands for) — but only when this frame has no base yet.
 *
 * Healing is what makes the base-less refusal recoverable: without it a frame
 * whose mount fetch failed (or that lost the first-save race) refuses every
 * later save until it is remounted. It can never make the base run ahead of the
 * local document, because it never replaces an existing base: an existing base
 * is only advanced by a fetch the caller applies, a save, or a conflict
 * snapshot. A frame that merely refreshed (the popover's reconcile poll, which
 * applies `actionChecks` only) is not an adoption and must call neither.
 * @param {string} playerId - OBR player ID
 * @param {string} roomId - OBR room ID
 * @param {number} version - Row version the document was read at
 * @param {Object} data - The document the local copy was just set to
 */
export function healSheetBase(playerId, roomId, version, data) {
  if (SHEET_BASES.has(sheetBaseKey(playerId, roomId))) return;
  rememberSheetBase(playerId, roomId, version, data);
}

/** Denormalized columns every write carries (same values as the old upsert). */
function sheetRow(playerId, roomId, sheet) {
  return {
    player_id: playerId,
    room_id: roomId,
    name: sheet.identity?.nom || '',
    race: sheet.identity?.race || null,
    level: sheet.identity?.niveau || 1,
    data: sheet,
  };
}

/**
 * True when PostgREST says the RPC is absent — i.e. the migration has not been
 * applied yet and the caller must fall back to the plain upsert.
 */
function isMissingRpc(error) {
  if (error?.code === MISSING_RPC_CODE) return true;
  return /could not find the function/i.test(String(error?.message ?? ''));
}

function callApplySheet(row, expectedVersion) {
  if (typeof supabase.rpc !== 'function') {
    return Promise.resolve({ data: null, error: { code: 'PGRST202', message: 'rpc unavailable' } });
  }
  return supabase.rpc('apply_character_sheet', {
    p_player_id: row.player_id,
    p_room_id: row.room_id,
    p_expected_version: expectedVersion,
    p_data: row.data,
    p_name: row.name,
    p_race: row.race,
    p_level: row.level,
  });
}

/** Pre-migration write path: whole-document upsert, no concurrency guard. */
async function saveCharacterSheetUnversioned(playerId, roomId, sheet) {
  const { data, error } = await supabase
    .from('character_sheets')
    .upsert({ ...sheetRow(playerId, roomId, sheet), updated_at: new Date().toISOString() }, { onConflict: 'player_id,room_id' })
    .select()
    .single();

  if (error) throw error;

  rememberSheetBase(playerId, roomId, data?.version, data?.data ?? sheet);
  broadcastSheet({ playerId, roomId, data: sheet, version: data?.version });
  return data;
}

/**
 * Save a character sheet through the compare-and-swap RPC, merging on conflict.
 * Falls back to the plain upsert while the migration is not deployed.
 * @param {string} playerId - OBR player ID
 * @param {string} roomId - OBR room ID
 * @param {Object} sheetData - Complete character sheet data
 * @returns {Promise<Object>} Saved character sheet row
 */
export async function saveCharacterSheet(playerId, roomId, sheetData) {
  try {
    let sheet = sheetData;
    let expected = SHEET_BASES.get(sheetBaseKey(playerId, roomId))?.version ?? 0;

    for (let attempt = 0; attempt < MAX_SHEET_SAVE_ATTEMPTS; attempt++) {
      const row = sheetRow(playerId, roomId, sheet);
      const { data, error } = await callApplySheet(row, expected);

      if (error) {
        if (!isMissingRpc(error)) throw error;
        if (!casMissingLogged) {
          casMissingLogged = true;
          logEvent('warn', 'sheet_save_rpc_missing', {
            message: 'apply_character_sheet not deployed — falling back to unversioned upserts',
            roomId,
          });
        }
        return await saveCharacterSheetUnversioned(playerId, roomId, sheet);
      }

      if (!data?.conflict) {
        const saved = { ...row, version: data?.version ?? expected + 1 };
        rememberSheetBase(playerId, roomId, saved.version, sheet);
        broadcastSheet({ playerId, roomId, data: sheet, version: saved.version });
        return saved;
      }

      // Another frame saved first: keep its document and re-apply only what
      // changed locally, instead of overwriting it.
      const base = SHEET_BASES.get(sheetBaseKey(playerId, roomId));
      // No base = the local copy was never derived from a fetched document (the
      // fetch failed, or this caller only read a field). Merging against {}
      // would call every differing leaf a local change and clobber the server's
      // real sheet while logging it as a merge — refuse instead of destroying.
      if (!base) {
        logEvent('warn', 'sheet_save_no_base', {
          message: 'save refused: local copy has no known base, refetch the sheet first',
          roomId,
          playerId,
        });
        throw new Error('character sheet base unknown — refetch before saving');
      }
      const merged = mergeSheet(base.data, sheet, data.data ?? {});
      if (merged.conflicts.length) {
        const paths = merged.conflicts.slice(0, 10).map((conflict) => conflict.path).join(', ');
        logEvent('warn', 'sheet_merge_conflict', {
          message: `${merged.conflicts.length} field(s) needed a merge decision: ${paths}`,
          roomId,
          playerId,
        });
      }
      sheet = merged.sheet;
      expected = Number(data.version) || 0;
      rememberSheetBase(playerId, roomId, expected, data.data);
    }

    throw new Error(`character sheet save kept conflicting (${MAX_SHEET_SAVE_ATTEMPTS} attempts)`);
  } catch (err) {
    logError('sheet_save_failed', err, { roomId, playerId });
    throw err;
  }
}

/**
 * Delete a character sheet
 * @param {string} playerId - OBR player ID
 * @param {string} roomId - OBR room ID
 */
export async function deleteCharacterSheet(playerId, roomId) {
  try {
    const { error } = await supabase
      .from('character_sheets')
      .delete()
      .eq('player_id', playerId)
      .eq('room_id', roomId);

    if (error) throw error;
    forgetSheetBase(playerId, roomId);
  } catch (err) {
    logError('sheet_delete_failed', err, { roomId, playerId });
    throw err;
  }
}

/** Maximum serialized character sheet size accepted on import (~1 MB). */
export const MAX_SHEET_BYTES = 1_000_000;

/**
 * Recursively replace embedded base64 data URLs with empty strings.
 * External URLs (http/https) and asset paths are left untouched.
 * Mutates the passed value and returns the number of stripped values.
 * @param {unknown} value - Parsed JSON to clean
 * @returns {number} Number of stripped values
 */
export function stripBase64Images(value) {
  let stripped = 0;
  const walk = (node) => {
    if (Array.isArray(node)) {
      for (let i = 0; i < node.length; i++) {
        if (typeof node[i] === 'string') {
          if (node[i].startsWith('data:')) {
            node[i] = '';
            stripped++;
          }
        } else if (node[i] && typeof node[i] === 'object') {
          walk(node[i]);
        }
      }
    } else if (node && typeof node === 'object') {
      for (const key of Object.keys(node)) {
        if (typeof node[key] === 'string') {
          if (node[key].startsWith('data:')) {
            node[key] = '';
            stripped++;
          }
        } else if (node[key] && typeof node[key] === 'object') {
          walk(node[key]);
        }
      }
    }
  };
  walk(value);
  return stripped;
}

/**
 * Import a character sheet from JSON string
 * @param {string} playerId - OBR player ID
 * @param {string} roomId - OBR room ID
 * @param {string} jsonString - JSON string to import
 * @returns {Promise<Object>} Imported character sheet
 */
export async function importCharacterSheet(playerId, roomId, jsonString) {
  try {
    const parsed = JSON.parse(jsonString);

    // Validate basic structure
    if (!parsed.identity || !parsed.stats) {
      throw new Error('Invalid character sheet format: missing identity or stats');
    }

    // Strip embedded base64 images: they bloat payloads to tens of MB
    // and make Supabase time out. External URLs are preserved.
    const strippedImages = stripBase64Images(parsed);
    if (strippedImages > 0) {
      logEvent('info', 'sheet_import_images_stripped', { message: `${strippedImages} embedded image(s)` });
    }

    // Merge with empty template to ensure all fields exist
    const empty = createEmptyCharacterSheet();
    const merged = {
      ...empty,
      ...parsed,
      identity: { ...empty.identity, ...parsed.identity },
      stats: { ...empty.stats, ...parsed.stats },
      progression: { ...empty.progression, ...parsed.progression },
      derived: { ...empty.derived, ...parsed.derived },
      defense: { ...empty.defense, ...parsed.defense },
      resources: { ...empty.resources, ...parsed.resources },
      skills: { ...empty.skills, ...parsed.skills },
      narrative: { ...empty.narrative, ...parsed.narrative },
      equipment: { ...empty.equipment, ...parsed.equipment }
    };

    // Legacy 'Armure' item type merges into 'Équipement'; gear items flatten
    // their equipmentData onto the item itself (item = single source of truth)
    merged.inventoryItems = (merged.inventoryItems ?? []).map((raw) => {
      const item = raw?.type === 'Armure' ? { ...raw, type: 'Équipement' } : raw;
      if (
        normalizeItemType(item?.type) === 'Équipement' &&
        SLOT_FIELDS[item?.slot] &&
        item?.equipmentData &&
        item.equipmentData.nom === (item.nom || item.name)
      ) {
        const { nom, ...rest } = item.equipmentData;
        const flat = { ...item, ...rest };
        delete flat.equipmentData;
        return flat;
      }
      return item;
    });

    // Exports often carry free-text race names ("Haut Elfe") — canonize to
    // the race id so game-side race lookups keep working.
    merged.identity.race = normalizeRaceName(merged.identity.race);

    // The race's natural weapons (Khajeet claws) are a built-in attack option in
    // the compact sheet, not an inventory entry: nothing to grant here.
    const synced = syncStatsFromEquipment(syncSlotsFromItems(syncSkillBonuses(migrateSheet(merged))));

    const payloadBytes = JSON.stringify(synced).length;
    if (payloadBytes > MAX_SHEET_BYTES) {
      throw new Error(
        `Fiche trop volumineuse (${(payloadBytes / 1048576).toFixed(1)} Mo, limite 1 Mo). Retirez les images intégrées du fichier JSON.`
      );
    }

    return await saveCharacterSheet(playerId, roomId, synced);
  } catch (err) {
    logError('sheet_import_failed', err, { roomId, playerId });
    throw err;
  }
}

const STANDARD_DICE_RE = /^(\d*)\s*d\s*(\d+)\s*([+-]\s*\d+)?$/i;
const STAT_DICE_RE = /^(?:(\d+)\s*)?mod\s+([a-zàâäéèêëîïôöùûüç]+)\s*d\s*(\d+)\s*([+-]\s*\d+)?$/i;

const STAT_KEYS = ['force', 'agilite', 'esprit', 'social'];

/**
 * Normalize a stat name (case- and accent-insensitive) to a stat key.
 * @param {string} name - Stat name (e.g. "Esprit", "agilité")
 * @returns {string|null} Stat key or null when unknown
 */
function normalizeStatName(name) {
  const normalized = String(name).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  return STAT_KEYS.includes(normalized) ? normalized : null;
}

/**
 * Compute a stat modifier from a raw score (e.g. 18 → +4).
 * @param {unknown} score - Raw stat score
 * @returns {number}
 */
export function statModifier(score) {
  return Math.floor((Number(score) - 10) / 2);
}

/**
 * Coerce any value to a finite number, defaulting to 0.
 * Sheet fields are often "" or numeric strings.
 * @param {unknown} value - Value to coerce
 * @returns {number}
 */
/**
 * Sanitize imported HTML for {@html} rendering: keeps a whitelist of
 * formatting tags (b/strong/i/em/u/s/br/p/ul/ol/li/span/h1-h6) with ALL
 * attributes stripped; every other tag is removed entirely.
 * @param {unknown} html - Raw description text, possibly containing HTML
 * @returns {string} Safe HTML string
 */
const SAFE_HTML_TAGS = /^(b|strong|i|em|u|s|br|p|ul|ol|li|span|h[1-6])$/i;
export function sanitizeHtml(html) {
  return String(html ?? '').replace(/<\/?([a-z0-9]+)[^>]*>/gi, (tag, name) =>
    SAFE_HTML_TAGS.test(name) ? `<${tag[1] === '/' ? '/' : ''}${name.toLowerCase()}>` : ''
  );
}

export function toNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

// Weapon categories are free-text fields, so they are detected by keyword.
// ponytail: keyword matching on weapon text, structured `categorie` field if misclassification bites
const SHIELD_RE = /\b(bouclier|rempart)\b/;
const STRAIGHT_SWORD_RE = /\b(epees? droites?|garde)\b/;
const RANGED_RE = /\b(distance|tir|lancer|javelot|fronde|arbalete|arc)\b/;

/**
 * Join all string values of a weapon into normalized (lowercase,
 * accent-free) text for keyword detection.
 * @param {Object} [weapon]
 * @returns {string}
 */
function weaponText(weapon) {
  // Tags are stored as ids (an array), so include them explicitly: keyword
  // detection (bouclier/épée droite/allonge) must see the properties.
  return [Object.values(weapon ?? {}).filter((v) => typeof v === 'string').join(' '), weaponTags(weapon).join(' ')]
    .join(' ')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

/**
 * Garde contribution of one equipped melee weapon: its die / 2
 * (e.g. "1d8" → 4, "2d6" → 6). Ranged weapons contribute nothing.
 * Dual wield naturally sums via equipmentStats.
 * @param {Object} [weapon]
 * @returns {number}
 */
function weaponGarde(weapon) {
  if (!weapon?.equipped || RANGED_RE.test(weaponText(weapon))) return 0;
  const match = String(weapon?.de ?? '').match(/(\d*)\s*d\s*(\d+)/i);
  if (!match) return 0;
  const count = match[1] === '' ? 1 : parseInt(match[1], 10);
  const sides = parseInt(match[2], 10);
  if (!(count >= 1) || !(sides >= 2)) return 0;
  return Math.floor((count * sides) / 2);
}

/**
 * Derive stats from equipped gear. Only the 7 equipment slots and weapons
 * flagged as equipped count; inventory items never contribute.
 * Garde = sum of equipped melee weapons' die / 2 (dual wield sums both).
 * @param {Object} [equipment] - Equipment slots object
 * @param {Array} [weapons] - Weapons array (each may carry `equipped: true`)
 * @returns {{deflexion: number, armure: number, volonte: number, garde: number}}
 */
export function equipmentStats(equipment = {}, weapons = []) {
  const slots = Object.values(equipment ?? {});
  const sum = (field) => slots.reduce((total, slot) => total + toNumber(slot?.[field]), 0);
  const garde = (weapons ?? []).reduce((total, w) => total + weaponGarde(w), 0);
  return {
    deflexion: sum('deflexion'),
    armure: sum('armure'),
    volonte: sum('volonte'),
    garde,
  };
}

/**
 * Parade modifier from the equipped weapons: Agilité, except with a
 * shield (Force) or a straight sword / "Garde" weapon (Force + Agilité).
 * @param {Array} [weapons] - Weapons array
 * @param {Object} [stats] - Raw stat scores
 * @returns {number}
 */
export function paradeModifier(weapons = [], stats = {}) {
  const equipped = (weapons ?? []).filter((w) => w?.equipped);
  const mod = (key) => statModifier(weaponStatScore(stats, key));
  if (equipped.some((w) => SHIELD_RE.test(weaponText(w)))) return mod('force');
  if (equipped.some((w) => STRAIGHT_SWORD_RE.test(weaponText(w)))) {
    return mod('force') + mod('agilite');
  }
  return mod('agilite');
}

/**
 * Stat score with missing values treated as 10 (modifier 0).
 * @param {Object} [stats]
 * @param {string} key - Stat key
 * @returns {number}
 */
function weaponStatScore(stats, key) {
  const score = Number(stats?.[key]);
  return Number.isFinite(score) ? score : 10;
}

/**
 * Attack bonus of one weapon: modifier of its governing stat (the
 * free-text `forceAgi` field: force / agilité / esprit) + the weapon's
 * tier (its `bonus` field) — what gets added to the weapon's die.
 * @param {Object} [weapon]
 * @param {Object} [stats] - Raw stat scores
 * @returns {number}
 */
export function attackBonus(weapon, stats = {}) {
  const key = normalizeStatName(weapon?.scaling ?? weapon?.forceAgi);
  const statMod = key ? statModifier(weaponStatScore(stats, key)) : 0;
  return statMod + toNumber(weapon?.bonus);
}

/**
 * Default for the weapon form's "Finesse" checkbox: a Finesse weapon is
 * assumed to scale with Agilité when the character's Agilité reaches its Force.
 * @param {Object} [stats] - Raw stat scores
 * @returns {boolean}
 */
export function finesseDefault(stats = {}) {
  return toNumber(stats?.agilite ?? 10) >= toNumber(stats?.force ?? 10);
}

/** Computed values a player may override with a manual value (ÉDITION STATS). */
export const OVERRIDABLE_DERIVED = ['parade', 'initiative', 'mouvement', 'seuilMiss', 'bonusAttaque', 'canalisation', 'volonte'];

/**
 * Stats with racial stat rules applied before any modifier is read.
 * Gnome « Faiblesse physique atténuée » : a Force of 5–9 gives no malus, so
 * the score is read as 10 everywhere (score ≤ 4 keeps its real malus).
 * @param {Object} [sheet] - Character sheet
 * @returns {Object} Stats object (the original when no rule applies)
 */
export function effectiveStats(sheet = {}) {
  const stats = sheet?.stats ?? {};
  if (normalizeRaceName(sheet?.identity?.race) !== 'gnome') return stats;
  const force = Number(stats.force);
  if (!Number.isFinite(force) || force < 5 || force >= 10) return stats;
  return { ...stats, force: 10 };
}

/**
 * Nain « Points de vie supplémentaires » : bonus PV = score de Force. The
 * sheet's PV max is a manual field, so this is shown as a PV source next to
 * the total — never written back into `derived.pvMax`.
 * @param {Object} [sheet] - Character sheet
 * @returns {number} Bonus PV (0 when the race is not Nain)
 */
export function racePvBonus(sheet = {}) {
  if (normalizeRaceName(sheet?.identity?.race) !== 'nain') return 0;
  return Math.max(0, Math.trunc(Number(effectiveStats(sheet).force) || 0));
}

/**
 * Compute all rule-derived combat values from a sheet.
 * - parade      = déflexion (equipped items) + garde (melee die/2) + modificateur
 * - initiative  = Agilité - 10 + initiative des gantelets
 * - mouvement   = 5 + Agilité/2 + vitesse des bottes
 * - volonte     = modificateur de Résilience + volonté du casque
 * - seuilMiss   = max(1, 1 - mod Agilité)
 * - canalisation = modificateur d'Esprit
 * - bonusAttaque = attack bonus of the main-hand weapon
 * Racial gear rules (Drakéide armour, Demi-Orque survival armour, Centaure
 * speed) are applied here too; manual overrides still win.
 * @param {Object} [sheet] - Character sheet data
 * @returns {Object} Computed values
 */
export function computeDerived(sheet = {}) {
  const stats = effectiveStats(sheet);
  const race = normalizeRaceName(sheet?.identity?.race);
  const equipment = sheet?.equipment ?? {};
  const weapons = sheet?.weapons ?? [];
  const eq = equipmentStats(equipment, weapons);
  const agiMod = statModifier(weaponStatScore(stats, 'agilite'));
  const gantelets = toNumber(equipment.gantelets?.initiative);
  const bottes = toNumber(equipment.bottes?.vitesse);
  const casque = toNumber(equipment.casque?.volonte);
  // legacy sheets: equipped without hand = main-hand occupant
  const firstEquipped =
    (weapons ?? []).find((w) => w?.equipped && (w?.hand ?? 'main') === 'main') ??
    (weapons ?? []).find((w) => w?.equipped);
  const paradeBonus = paradeModifier(weapons, stats);
  const base = {
    ...eq,
    // Rule value: resilience modifier + casque. (eq.volonte above is the raw slot sum.)
    volonte: skillModifier(stats, 'resilience') + casque,
    paradeBonus,
    parade: eq.deflexion + eq.garde + paradeBonus,
    initiative: weaponStatScore(stats, 'agilite') - 10 + gantelets,
    mouvement: 5 + Math.floor(weaponStatScore(stats, 'agilite') / 2) + bottes,
    seuilMiss: Math.max(1, 1 - agiMod),
    canalisation: statModifier(weaponStatScore(stats, 'esprit')),
    bonusAttaque: firstEquipped ? attackBonus(firstEquipped, stats) : 0,
  };
  // Racial gear rules (applied before the manual overrides so those still win).
  if (race === 'drakeide') {
    // Écailles draconiques : armure naturelle de 1, cumulable.
    base.armure = toNumber(base.armure) + 1;
  } else if (race === 'demi-orque') {
    // Armure de survie : double sous 50 % des PV.
    const pvMax = toNumber(sheet?.derived?.pvMax);
    const pvActuels = toNumber(sheet?.derived?.pvActuels);
    if (pvMax > 0 && pvActuels < pvMax / 2) base.armure = toNumber(base.armure) * 2;
  }
  if (race === 'centaure') {
    // Vitesse équine : déplacement ×1,5.
    base.mouvement = Math.floor(toNumber(base.mouvement) * 1.5);
  }
  // Manual overrides (typed in ÉDITION); empty/absent = rule value applies.
  const overrides = sheet?.derived?.overrides ?? {};
  for (const key of OVERRIDABLE_DERIVED) {
    const v = overrides[key];
    if (v !== undefined && v !== null && v !== '') base[key] = toNumber(v);
  }
  return base;
}

/**
 * Overwrite stored defense/derived fields with computed values.
 * All combat values are rule-derived; none are manual anymore.
 * @param {Object} sheet - Character sheet data
 * @returns {Object} New sheet object with synced fields
 */
/**
 * Push each slotted item's equipmentData into the matching equipment slot,
 * keeping the two copies in sync (the item is the editable source).
 * @param {Object} [sheet] - Character sheet
 * @returns {Object} New sheet with synced equipment slots
 */
/**
 * Build an equipment-slot object from an item's flattened stat fields
 * (deflexion, armure, volonte, initiative, vitesse, enchantement, …).
 * @param {Object} [item] - Inventory item
 * @returns {Object} Slot-shaped data ({nom, raretePrix, deflexion, …})
 */
export function slotDataFromItem(item = {}) {
  const nom = item?.nom || item?.name || '';
  const data = {
    nom,
    raretePrix: item?.raretePrix ?? '',
    deflexion: item?.deflexion ?? '',
    armure: item?.armure ?? '',
    volonte: item?.volonte ?? '',
    initiative: item?.initiative ?? '',
    vitesse: item?.vitesse ?? '',
    enchantement: item?.enchantement ?? '',
    description: item?.description ?? '',
  };
  return data.nom ? data : { ...data, nom: item?.equipmentData?.nom || '' };
}

export function syncSlotsFromItems(sheet = {}) {
  if (!sheet) return sheet;
  const equipment = { ...(sheet.equipment ?? {}) };
  for (const item of sheet.inventoryItems ?? []) {
    const slot = item?.slot;
    const nom = item?.nom || item?.name;
    if (!slot || !nom || !SLOT_FIELDS[slot]) continue;
    const current = equipment[slot];
    if (current?.nom === nom) equipment[slot] = slotDataFromItem(item);
  }
  return { ...sheet, equipment };
}

export function syncStatsFromEquipment(sheet) {
  if (!sheet) return sheet;
  const c = computeDerived(sheet);
  return {
    ...sheet,
    defense: {
      ...(sheet.defense ?? {}),
      deflexion: c.deflexion,
      armure: c.armure,
      gardeBonus: c.garde,
      bonus: c.paradeBonus,
    },
    derived: {
      ...(sheet.derived ?? {}),
      volonte: c.volonte,
      initiative: c.initiative,
      mouvement: c.mouvement,
      seuilMiss: c.seuilMiss,
      canalisation: c.canalisation,
      bonusAttaque: c.bonusAttaque,
    },
  };
}

/**
 * Parse a dice formula into { count, sides, modifier, formula }.
 * Supports standard ("4d6", "4D6", "2d8+3", "d6") and stat-based
 * ("Mod Esprit D6" → Esprit modifier dice, "3 Mod Esprit D6" → 3 ×
 * modifier dice) forms. For stat-based forms, `stats` must provide the
 * raw score; the dice count is the stat modifier times the optional
 * leading multiplier (minimum 1). Returns null when unparseable.
 * @param {unknown} value - Formula to parse
 * @param {Object} [stats] - Raw stat scores ({ force, agilite, esprit, social })
 * @returns {{count: number, sides: number, modifier: number, formula: string}|null}
 */
export function parseDiceFormula(value, stats = {}) {
  if (typeof value !== 'string') return null;
  const text = value.trim();
  const format = (count, sides, modifier) =>
    `${count}d${sides}${modifier ? `${modifier > 0 ? '+' : ''}${modifier}` : ''}`;

  let match = text.match(STANDARD_DICE_RE);
  if (match) {
    const count = match[1] === '' ? 1 : parseInt(match[1], 10);
    const sides = parseInt(match[2], 10);
    const modifier = match[3] ? parseInt(match[3].replace(/\s+/g, ''), 10) : 0;
    if (!(count >= 1) || !(sides >= 2)) return null;
    return { count, sides, modifier, formula: format(count, sides, modifier) };
  }

  match = text.match(STAT_DICE_RE);
  if (match) {
    const key = normalizeStatName(match[2]);
    const score = Number(stats?.[key]);
    if (!key || !Number.isFinite(score)) return null;
    const multiplier = match[1] === undefined ? 1 : parseInt(match[1], 10);
    if (!(multiplier >= 1)) return null;
    const count = Math.max(1, multiplier * statModifier(score));
    const sides = parseInt(match[3], 10);
    if (!(sides >= 2)) return null;
    const modifier = match[4] ? parseInt(match[4].replace(/\s+/g, ''), 10) : 0;
    return { count, sides, modifier, formula: format(count, sides, modifier) };
  }

  return null;
}

/**
 * Check whether a string is a rollable dice formula
 * (e.g. "4d6", "4D6", "2d8+3", "d6", "Mod Esprit D6" with stats).
 * Capacity values like "X" or "20 PVs Temporaires" are not rollable.
 * @param {unknown} value - Value to check
 * @param {Object} [stats] - Raw stat scores, required for stat-based formulas
 * @returns {boolean}
 */
export function isDiceFormula(value, stats = {}) {
  if (parseDiceFormula(value, stats) !== null) return true;
  // compound formulas: every '+' term must roll
  if (typeof value === 'string' && value.includes('+')) {
    const parts = value.split('+').map((p) => p.trim()).filter(Boolean);
    if (parts.length > 1 && parts.every((p) => parseDiceFormula(p, stats) !== null)) return true;
  }
  return false;
}

// ─── Dice color (gem themes for the 3D dice popup) ───
/** stat → gem name when the stat color governs the dice (max-stat rule) */
export const STAT_GEM = { force: 'ruby', agilite: 'emerald', esprit: 'sapphire', social: 'amethyst' };
/** Player-selectable dice colors (ÉDITION IDENTITÉ) */
export const DICE_GEMS = {
  obsidian: '#312e81',
  ruby: '#e11d48',
  emerald: '#059669',
  sapphire: '#3b82f6',
  amethyst: '#a855f7',
};
export const DICE_GEM_LABELS = {
  obsidian: 'Obsidienne',
  ruby: 'Rubis',
  emerald: 'Émeraude',
  sapphire: 'Saphir',
  amethyst: 'Améthyste',
};

/**
 * Resolve the dice color for a sheet:
 * explicit choice (identity.diceColor) > max-stat gem (random pick on ties)
 * > obsidian (no meaningful stats). A random pick among tied gems gives a
 * mixed color across rolls.
 * @param {Object} [sheet]
 * @returns {string} gem key ('obsidian' | 'ruby' | 'emerald' | 'sapphire' | 'amethyst')
 */
export function diceGem(sheet = {}) {
  const chosen = sheet?.identity?.diceColor;
  if (chosen && DICE_GEMS[chosen]) return chosen;
  const keys = ['force', 'agilite', 'esprit', 'social'];
  const values = keys.map((k) => Number(sheet?.stats?.[k]));
  if (values.some((v) => !Number.isFinite(v)) || values.every((v) => v === values[0])) {
    return 'obsidian';
  }
  const max = Math.max(...values);
  const tied = keys.filter((k) => Number(sheet.stats[k]) === max).map((k) => STAT_GEM[k]);
  return tied.length > 1 ? tied[Math.floor(Math.random() * tied.length)] : tied[0];
}

/** Resolved dice color as a hex string. */
export function diceGemColor(sheet) {
  return DICE_GEMS[diceGem(sheet)];
}

/**
 * Token counts derived from raw stats: stat modifier + 1 (min 0).
 * These are the values a sheet import syncs into game state; the GM's
 * REST resets tokens to them (maxTokens).
 * @param {Object} [stats] - Raw stat scores ({ force, agilite, esprit, social })
 * @returns {{force: number, agilite: number, esprit: number, social: number}}
 */
export function tokensFromStats(stats = {}) {
  const out = {};
  for (const key of ['force', 'agilite', 'esprit', 'social']) {
    out[key] = Math.max(0, statModifier(Number(stats?.[key]) || 10) + 1);
  }
  return out;
}

/**
 * Compute a skill's modifier from its governing stat.
 * Falls back to `fallback` for unknown skills or missing scores.
 * @param {Object} [stats] - Raw stat scores ({ force, agilite, esprit, social })
 * @param {string} skill - Skill key (e.g. "arcanes")
 * @param {number} [fallback] - Value when the skill has no governing stat
 * @returns {number}
 */
export function skillModifier(stats, skill, fallback = 0) {
  const key = SKILL_TO_STAT[String(skill ?? '').toLowerCase()];
  if (!key) return fallback;
  const score = Number(stats?.[key]);
  if (!Number.isFinite(score)) return fallback;
  return statModifier(score);
}

/**
 * Roll modifier for a skill: governing-stat modifier, doubled when the
 * skill is mastered (trained).
 * @param {Object} stats - Character stats
 * @param {string} skill - Skill key
 * @param {Object} [skillData] - Skill entry ({trained, bonus})
 * @returns {number}
 */
export function skillRollModifier(stats, skill, skillData = {}) {
  const base = skillModifier(stats, skill, skillData?.bonus ?? 0);
  return skillData?.trained ? base * 2 : base;
}

/**
 * True when a weapon is two-handed (free-text keyword match, same approach
 * as paradeModifier's shield/distance detection).
 * @param {Object} weapon - Weapon entry (nom/de/propriétés/notes)
 * @returns {boolean}
 */
export function isTwoHanded(weapon, race) {
  // Goliath « Force colossale » : une arme à deux mains tient dans une main
  // (et donc n'occupe qu'un emplacement).
  if (/goliath/i.test(String(race ?? ''))) return false;
  if (weaponTags(weapon).includes('deux-mains')) return true;
  const text = [weapon?.nom, weapon?.propriétés, weapon?.proprietes, weapon?.notes]
    .map((v) => String(v ?? ''))
    .join(' ');
  return /deux\s*mains|2\s*mains|two[-\s]?handed/i.test(text);
}

/**
 * Derive the two hand slots from the weapons array. Legacy sheets have
 * `equipped` without `hand` — the first equipped weapon then counts as main.
 * @param {Object} sheet - Character sheet
 * @returns {{main: Object|null, off: Object|null, twoHanded: boolean}}
 */
export function handSlots(sheet = {}) {
  const eq = (sheet?.weapons ?? []).filter((w) => w?.nom && w?.equipped);
  const taggedMain = eq.find((w) => w?.hand === 'main');
  const taggedOff = eq.find((w) => w?.hand === 'off');
  const untagged = eq.filter((w) => !w?.hand);
  let main = null;
  let off = null;
  if (taggedMain) {
    main = taggedMain;
    off = taggedOff ?? untagged[0] ?? null;
  } else if (taggedOff) {
    off = taggedOff;
    main = untagged[0] ?? null;
  } else {
    // no tags at all: legacy equipped weapons keep their array order
    main = untagged[0] ?? null;
    off = untagged[1] ?? null;
  }
  return { main, off, twoHanded: main ? isTwoHanded(main) : false };
}

/**
 * Equip a weapon into a hand slot (pure). A two-handed weapon clears both
 * hands; a one-handed weapon replaces whatever occupied the target hand
 * (including a two-hander) and leaves the other hand untouched.
 * @param {Object} sheet - Character sheet
 * @param {Object} weapon - Weapon entry from sheet.weapons (by reference)
 * @param {'main'|'off'} hand - Target hand slot
 * @returns {Object} New sheet with updated weapons
 */
export function equipWeapon(sheet, weapon, hand = 'main') {
  if (!weapon?.nom) return sheet;
  const race = sheet?.identity?.race;
  const two = isTwoHanded(weapon, race);
  return {
    ...sheet,
    weapons: (sheet?.weapons ?? []).map((w) => {
      if (w === weapon) return { ...w, equipped: true, hand: two ? 'main' : hand };
      if (!w?.equipped && !w?.hand) return w;
      // legacy sheets: equipped without hand = main-hand occupant
      const wHand = w?.hand ?? 'main';
      if (two || wHand === hand || isTwoHanded(w, race)) return { ...w, equipped: false, hand: null };
      return { ...w, hand: wHand };
    }),
  };
}

/**
 * Unequip whatever occupies a hand slot (pure).
 * @param {Object} sheet - Character sheet
 * @param {'main'|'off'} hand - Hand slot to clear
 * @returns {Object} New sheet
 */
export function unequipHand(sheet, hand) {
  // resolve the actual occupant of the hand slot; legacy untagged equipped
  // weapons default to 'main', so a name/hand fallback would evict the
  // off-hand weapon too (Vider bug) — match the occupant by reference
  const slots = handSlots(sheet);
  const occupant = slots[hand];
  const other = slots[hand === 'main' ? 'off' : 'main'];
  return {
    ...sheet,
    weapons: (sheet?.weapons ?? []).map((w) => {
      if (!w?.equipped) return w;
      if (occupant && w === occupant) return { ...w, equipped: false, hand: null };
      // pin the other hand's (untagged) occupant so it keeps its slot after the clear
      if (other && w === other && !w?.hand) return { ...w, hand: hand === 'main' ? 'off' : 'main' };
      // no distinct off occupant: an equipped two-hander occupies both hands
      if (!occupant && isTwoHanded(w) && w?.hand !== 'off') return { ...w, equipped: false, hand: null };
      return w;
    }),
  };
}

/**
 * Overwrite stored skill bonuses from governing stat modifiers.
 * Skills without a governing stat keep their stored bonus.
 * @param {Object} sheet - Character sheet data
 * @returns {Object} New sheet object with synced bonuses
 */
export function syncSkillBonuses(sheet) {
  if (!sheet?.skills) return sheet;
  const skills = {};
  for (const [skill, data] of Object.entries(sheet.skills)) {
    skills[skill] = {
      ...data,
      bonus: SKILL_TO_STAT[skill] ? skillModifier(sheet.stats, skill, data?.bonus ?? 0) : (data?.bonus ?? 0),
    };
  }
  return { ...sheet, skills };
}

/**
 * Roll dice based on a formula like "4d6", "2d8+3" or "Mod Esprit D6"
 * @param {string} formula - Dice formula
 * @param {Object} [stats] - Raw stat scores, required for stat-based formulas
 * @returns {{total: number, rolls: number[], modifier: number, formula: string}}
 */
/**
 * Resolve a formula into explicit dice terms for the physics roller:
 * { terms: [{count, sides}...], modifier, formula }. Single terms, stat
 * formulas ("Mod Esprit D6" — resolved with stats) and compounds
 * ("1d6+1d4", "2d6+3") are supported. Returns null when not rollable.
 * @param {string} formula
 * @param {Object} [stats]
 * @returns {{terms: {count: number, sides: number}[], modifier: number, formula: string} | null}
 */
export function parseDiceSpec(formula, stats = {}) {
  if (typeof formula !== 'string') return null;
  const text = formula.trim();
  if (!text.includes('+')) {
    const parsed = parseDiceFormula(text, stats);
    if (!parsed) return null;
    return { terms: [{ count: parsed.count, sides: parsed.sides }], modifier: parsed.modifier, formula: parsed.formula };
  }
  const parts = text.split('+').map((p) => p.trim()).filter(Boolean);
  if (!parts.length) return null;
  const terms = [];
  let modifier = 0;
  const parts_ = [];
  for (const part of parts) {
    const parsed = parseDiceFormula(part, stats);
    if (parsed) {
      terms.push({ count: parsed.count, sides: parsed.sides });
      parts_.push(parsed.formula);
      modifier += parsed.modifier;
    } else if (/^[+-]?\s*\d+$/.test(part)) {
      modifier += parseInt(part.replace(/\s+/g, ''), 10);
    } else {
      return null;
    }
  }
  if (!terms.length) return null;
  return { terms, modifier, formula: parts.join('+') };
}

/**
 * Flat avantage/désavantage roll for a d20 check: 2d20, one die kept.
 * Takes the same `d20±X` formula the normal path uses and rewrites the die
 * count, so callers only flip `keep`.
 * @param {string} formula - d20 check formula ("d20+3")
 * @param {Object} [stats] - Stat scores for stat formulas
 * @param {'high'|'low'} keep - Avantage (high) / désavantage (low)
 * @returns {Object} rollDice-shaped result
 */
export function rollD20Keep(formula, stats = {}, keep = 'high') {
  const base = parseDiceSpec(formula, stats);
  if (!base) throw new Error(`Invalid dice formula: ${formula}`);
  const mod = base.modifier;
  return rollDice(`2d20${mod >= 0 ? '+' + mod : mod}`, stats, { keep });
}

export function rollDice(formula, stats = {}, opts = {}) {
  // Avantage/désavantage racial: 2 dés, seul le meilleur/pire compte (le
  // modificateur du jet est conservé tel quel).
  const keep = opts?.keep;
  const applyKeep = (rolls, total) => {
    if (!keep || rolls.length < 2) return total;
    const kept = keep === 'low' ? Math.min(...rolls) : Math.max(...rolls);
    return kept + (total - rolls.reduce((a, b) => a + b, 0));
  };
  // compound formulas ("1d6+1d4"): roll each term, concat rolls in order
  if (typeof formula === 'string' && formula.includes('+')) {
    const parts = formula.split('+').map((p) => p.trim()).filter(Boolean);
    if (parts.length > 1) {
      const parsed = parts.map((p) => parseDiceFormula(p, stats));
      if (parsed.every(Boolean)) {
        const rolls = [];
        const diceTypes = [];
        let total = 0;
        for (const part of parsed) {
          for (let i = 0; i < part.count; i++) {
            const v = Math.floor(Math.random() * part.sides) + 1;
            rolls.push(v);
            diceTypes.push(part.sides);
            total += v;
          }
          total += part.modifier;
        }
        return { total: applyKeep(rolls, total), rolls, diceTypes, modifier: 0, formula: parts.join('+'), keep };
      }
    }
  }

  const parsed = parseDiceFormula(formula, stats);
  if (!parsed) {
    throw new Error(`Invalid dice formula: ${formula}`);
  }

  const { count, sides, modifier } = parsed;
  const rolls = [];
  for (let i = 0; i < count; i++) {
    rolls.push(Math.floor(Math.random() * sides) + 1);
  }

  const sum = rolls.reduce((a, b) => a + b, 0);
  const total = applyKeep(rolls, sum + modifier);

  return { total, rolls, diceTypes: Array(count).fill(sides), modifier, formula: parsed.formula, keep };
}

/**
 * Subscribe to realtime updates for a character sheet
 * @param {string} playerId - OBR player ID
 * @param {string} roomId - OBR room ID
 * @param {Function} callback - Callback when sheet changes
 * @returns {Function} Unsubscribe function
 */
// ─── Same-origin instant sheet sync (BroadcastChannel) ───
// Supabase Realtime alone is slow/unreliable between the main sheet and the
// compact popover (same browser, different frames) — this makes every save
// apply instantly on the other frame. Cross-client sync stays on Realtime.
let sheetChannel = null;
const sheetListeners = new Set();

function sheetChannelInstance() {
  if (!sheetChannel && typeof BroadcastChannel !== 'undefined') {
    sheetChannel = new BroadcastChannel('cardenveil-sheet');
  }
  return sheetChannel;
}

/**
 * Broadcast a saved sheet to same-origin frames (main ↔ compact popover).
 * JSON round-trip strips Svelte $state reactivity before posting.
 * @param {{playerId: string, roomId: string, data: Object, version?: number}} message
 */
export function broadcastSheet(message) {
  try {
    sheetChannelInstance()?.postMessage(JSON.parse(JSON.stringify(message)));
  } catch (err) {
    logEvent('warn', 'sheet_broadcast_failed', { message: err?.message ?? String(err) });
  }
}

/**
 * Listen for sheet broadcasts. Returns an unsubscribe function.
 * @param {(message: {playerId: string, roomId: string, data: Object, version?: number}) => void} callback
 * @returns {() => void}
 */
export function onSheetBroadcast(callback) {
  const channel = sheetChannelInstance();
  if (!channel) return () => {};
  // One shared channel, many listeners: assigning channel.onmessage directly
  // made the last subscriber replace the previous one (GMDashboard lost the
  // GM frame's instant diamond updates) and its unsubscribe could never match.
  sheetListeners.add(callback);
  channel.onmessage = (event) => {
    for (const cb of [...sheetListeners]) cb(event.data);
  };
  return () => {
    sheetListeners.delete(callback);
    if (sheetListeners.size === 0) channel.onmessage = null;
  };
}

export function subscribeToCharacterSheet(playerId, roomId, callback) {
  const channel = supabase
    .channel(`character_sheet:${playerId}:${roomId}`)
    .on(
      'postgres_changes',
      {
        event: '*',
        schema: 'public',
        table: 'character_sheets',
        filter: `player_id=eq.${playerId},room_id=eq.${roomId}`
      },
      (payload) => {
        callback(payload.new);
      }
    )
    .subscribe();

  return () => {
    supabase.removeChannel(channel);
  };
}

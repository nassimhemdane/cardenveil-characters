const SUITS = [
  { symbol: '♠', isRed: false, id: 'S' },
  { symbol: '♣', isRed: false, id: 'C' },
  { symbol: '♥', isRed: true,  id: 'H' },
  { symbol: '♦', isRed: true,  id: 'D' },
];
const VALUES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'];

const SUIT_BY_ID = {
  S: { symbol: '♠', isRed: false },
  C: { symbol: '♣', isRed: false },
  H: { symbol: '♥', isRed: true  },
  D: { symbol: '♦', isRed: true  },
};

const SUIT_SORT_ORDER = { '♥': 0, '♣': 1, '♦': 2, '♠': 3 };

/** Fatigue level → card penalty mapping: level 0=0, 1=-1, 2=-2, 3=-4, 4=-6 */
export const FATIGUE_PENALTY = [0, 1, 2, 3, 4];

/**
 * Fatigue malus for a race: Mort-vivant « Fatigue » ignores it below level 5.
 * @param {string|null|undefined} race - Race id
 * @param {unknown} level - Fatigue level
 * @returns {number} Penalty to display/apply
 */
export function fatiguePenaltyFor(race, level) {
  const raw = Math.max(0, Math.trunc(Number(level) || 0));
  if (race === 'mort-vivant' && raw < 5) return 0;
  return FATIGUE_PENALTY[Math.min(FATIGUE_PENALTY.length - 1, raw)] ?? 0;
}

export function sortCards(cards) {
  return [...cards].sort((a, b) => {
    if (a._pending && !b._pending) return 1;
    if (!a._pending && b._pending) return -1;
    if (a._pending && b._pending) return 0;
    return (SUIT_SORT_ORDER[a.suit] - SUIT_SORT_ORDER[b.suit]) || (a.numericValue - b.numericValue);
  });
}

function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
}

let _pendingUid = 0;

/** Create a placeholder card shown while waiting for the server to confirm a draw. */
export function makePendingCard() {
  return { id: `pending-${Date.now()}-${++_pendingUid}`, _pending: true, suit: '', value: '?', numericValue: 0, isRed: false };
}

/** Create a specific card (by suit symbol + value) with a fresh unique ID. */
export function makeCard(suitSymbol, value, prefix = 'n') {
  const suit = SUITS.find(s => s.symbol === suitSymbol);
  const i    = VALUES.indexOf(value);
  return { id: `${prefix}-${suit.id}-${value}-${uid()}`, suit: suit.symbol, value, numericValue: i + 1, isRed: suit.isRed };
}

/** Draw one random card from the full 52-card set (normal pool, infinite). */
export function drawNormal(min = 1, max = 13) {
  const pool   = VALUES.filter((_, i) => i + 1 >= min && i + 1 <= max);
  const arr    = pool.length > 0 ? pool : VALUES;
  const suit   = SUITS[Math.floor(Math.random() * SUITS.length)];
  const value  = arr[Math.floor(Math.random() * arr.length)];
  const i      = VALUES.indexOf(value);
  return { id: `n-${suit.id}-${value}-${uid()}`, suit: suit.symbol, value, numericValue: i + 1, isRed: suit.isRed };
}

/** Draw one random card from the 13 cards of the given suit (specialized pool, infinite). */
export function drawSpecialized(suitSymbol, min = 1, max = 13) {
  const pool   = VALUES.filter((_, i) => i + 1 >= min && i + 1 <= max);
  const arr    = pool.length > 0 ? pool : VALUES;
  const suit   = SUITS.find(s => s.symbol === suitSymbol);
  const value  = arr[Math.floor(Math.random() * arr.length)];
  const i      = VALUES.indexOf(value);
  return { id: `s-${suit.id}-${value}-${uid()}`, suit: suit.symbol, value, numericValue: i + 1, isRed: suit.isRed };
}

/** All 52 cards of the standard deck (for swap picker UI). */
export function fullDeck() {
  return SUITS.flatMap(suit =>
    VALUES.map((value, i) => ({
      id: `pick-${suit.id}-${value}`,
      suit: suit.symbol, value, numericValue: i + 1, isRed: suit.isRed,
    }))
  );
}

/** All 13 cards of a given suit (for swap picker UI). */
export function fullSuit(suitSymbol) {
  const suit = SUITS.find(s => s.symbol === suitSymbol);
  return VALUES.map((value, i) => ({
    id: `pick-${suit.id}-${value}`,
    suit: suit.symbol, value, numericValue: i + 1, isRed: suit.isRed,
  }));
}

/** Reconstruct a full card object from its ID string. */
export function cardFromId(id) {
  // id format: "{prefix}-{suitId}-{value}-{copy}"  e.g. "n-S-10-1"
  const parts = String(id).split('-');
  const suitId = parts[1];
  const value  = parts[2];
  // Unknown/legacy ids must not throw: one bad id in the stored row would
  // break hydration for every client in the room.
  const { symbol, isRed } = SUIT_BY_ID[suitId] ?? { symbol: '?', isRed: false };
  return { id, suit: symbol, value: value ?? '?', numericValue: VALUES.indexOf(value) + 1, isRed };
}

/** Accept an ID string or an already-hydrated card object. */
function toCard(item) {
  return typeof item === 'string' ? cardFromId(item) : item;
}

/** Reserved ID for the optional GM player-character */
export const GM_CHAR_ID = '__gm_char__';

/** Suit display info shared by the hand/GM UIs (labels in French). */
export const SUITS_INFO = [
  { symbol: '♠', label: 'Piques', isRed: false },
  { symbol: '♣', label: 'Trèfles', isRed: false },
  { symbol: '♥', label: 'Cœurs', isRed: true },
  { symbol: '♦', label: 'Carreaux', isRed: true },
];

/**
 * Playable races (document order from the Cardenveil rulebook). The reducer
 * only needs the ids; the trait text lives in `RACE_TRAITS`
 * (characterSheet.js) to keep this file — bundled server-side — lean.
 */
export const RACES = [
  { id: 'humain',       label: 'Humain' },
  { id: 'haut-elfe',    label: 'Haut-Elfe' },
  { id: 'elfe-des-bois', label: 'Elfe des Bois' },
  { id: 'elfe-noir',    label: 'Elfe Noir' },
  { id: 'demi-elfe',    label: 'Demi-Elfe' },
  { id: 'tieffelin',    label: 'Tieffelin' },
  { id: 'aasimar',      label: 'Aasimar' },
  { id: 'demi-orque',   label: 'Demi-Orque' },
  { id: 'nain',         label: 'Nain' },
  { id: 'gobelin',      label: 'Gobelin' },
  { id: 'gnome',        label: 'Gnome' },
  { id: 'halfling',     label: 'Halfling' },
  { id: 'goliath',      label: 'Goliath' },
  { id: 'drakeide',     label: 'Drakéide' },
  { id: 'sporelin',     label: 'Sporelin' },
  { id: 'mort-vivant',  label: 'Mort-vivant' },
  { id: 'khajeet',      label: 'Khajiit' },
  { id: 'troll',        label: 'Troll' },
  { id: 'homme-poisson', label: 'Homme-Poisson' },
  { id: 'hobgoblin',    label: 'Hobgoblin' },
  { id: 'centaure',     label: 'Centaure' },
  { id: 'mecha',        label: 'Mécha' },
  { id: 'illithid',     label: 'Illithid' },
  { id: 'firbolg',      label: 'Firbolg' },
  { id: 'nimbri',       label: 'Nimbri' },
];

const RACE_IDS = new Set(RACES.map(r => r.id));

/** Valid token keys — an unknown key used to write NaN into `tokens`. */
const TOKEN_KEYS = new Set(['force', 'agilite', 'esprit', 'social']);

export function createEmptyPlayer(name = '') {
  return {
    name,
    hand: [],
    crystallized: [],
    maxHandSize: 3,
    tokens:       { force: 3, agilite: 3, esprit: 3, social: 3 },
    maxTokens:    { force: 3, agilite: 3, esprit: 3, social: 3 },
    minDrawValue:  1,
    maxDrawValue:  13,
    grayedCards:   [],
    spiritBounds:  0,
    fatigue:       0,
    race:          null,
    tieflingDrawEligible: true,
    pendingHalfling: null,
    lastDevourAt:  0,
    /** Nimbri « Compréhension abstraite de la magie »: one split per
     *  *explicit* draw (Piocher / pioche par token Force). No timer: the
     *  once-per-round limit is the table's business (issue #15). */
    splitAvailable: false,
  };
}

export function createInitialGameState() {
  return {
    discard:          [],
    pendingExchanges: [],
    lastActionIds:    [],
    gmId:             null,
    gmCharacterId:    null,
    players:          {},
    logs:             [],
    initiativeUrl:    null,
  };
}

const LOG_LIMIT = 200;

/**
 * Append a log entry to state. Trims to the last LOG_LIMIT entries.
 * @param {object} state
 * @param {string} playerId
 * @param {string} playerName
 * @param {string} msg
 */
export function addLog(state, playerId, playerName, msg) {
  const entry = { id: uid(), ts: Date.now(), playerId, playerName, msg };
  const logs = [...(state.logs ?? []), entry];
  return { ...state, logs: logs.length > LOG_LIMIT ? logs.slice(-LOG_LIMIT) : logs };
}

function isGM(state, playerId) {
  return state.gmId === playerId;
}

function clamp(val, min, max) {
  return Math.max(min, Math.min(max, val));
}

/** Effective hand cap including racial bonus. */
export function handCap(player) {
  const raceBonus = player.race === 'haut-elfe' ? 1 : 0;
  return (player.maxHandSize ?? 3) + (player.spiritBounds ?? 0) + raceBonus;
}

/** Cooldown of the Illithid's Dévoration mentale (rule: once per 30 min). */
export const DEVOUR_COOLDOWN_MS = 30 * 60 * 1000;

/** Face value of a card as the players read it: 2..10, J=11, Q=12, K=13, A=14. */
const faceValue = (card) => (card?.numericValue ?? 0) + 1;

/** Racial token-cap bonuses (Humain: +2 Social). */
export function tokenCapBonus(race) {
  return race === 'humain' ? { social: 2 } : {};
}

/**
 * Effective token cap = stored base + racial bonus. `maxTokens` stays the
 * base (what the GM/sheet sends); every cap check and refill goes through
 * here, so a race change can never desync the pool.
 */
export function maxTokensFor(player) {
  const base = player?.maxTokens ?? { force: 3, agilite: 3, esprit: 3, social: 3 };
  const bonus = tokenCapBonus(player?.race);
  let out = base;
  for (const [key, value] of Object.entries(bonus)) out = { ...out, [key]: (out[key] ?? 0) + value };
  return out;
}

/** Aasimar « Cœur supplémentaire »: spending a token also invokes a normal
 *  Heart card. It joins the hand; if the hand is full the card is discarded
 *  (the hand cap stays the hard limit).
 * @returns {{player: object, discarded: Array}} */
function maybeAasimarHeart(player) {
  if (player.race !== 'aasimar') return { player, discarded: [] };
  const heart = drawSpecialized('♥');
  const cap = handCap(player);
  if ((player.hand?.length ?? 0) < cap) {
    return { player: { ...player, hand: [...player.hand, heart] }, discarded: [] };
  }
  return { player, discarded: [heart] };
}

export function applyAction(state, action) {
  const { type } = action;

  switch (type) {
    case 'INIT_GAME': {
      const fresh = createInitialGameState();
      return { state: { ...fresh, gmId: action.playerId }, log: null };
    }

    case 'REGISTER_PLAYER': {
      if (state.players[action.playerId]) return { state, log: null };
      const s = {
        ...state,
        players: { ...state.players, [action.playerId]: createEmptyPlayer(action.name) },
      };
      return { state: s, log: null };
    }

    case 'REGISTER_PARTY': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      let players = { ...state.players };
      for (const p of (action.players ?? [])) {
        if (!players[p.id]) {
          players[p.id] = createEmptyPlayer(p.name);
        }
      }
      return { state: { ...state, players }, log: null };
    }

    case 'DRAW': {
      const p = state.players[action.playerId];
      if (!p || p.pendingHalfling) return { state, log: null };
      const cap = handCap(p);
      if (p.hand.length >= cap) return { state, log: null };
      const mn = p.minDrawValue ?? 1, mx = p.maxDrawValue ?? 13;

      // HALFLING: draw 2, store in pendingHalfling
      if (p.race === 'halfling') {
        const cardA = drawNormal(mn, mx);
        const cardB = drawNormal(mn, mx);
        const s = {
          ...state,
          players: { ...state.players, [action.playerId]: {
            ...p,
            pendingHalfling: [cardA, cardB],
            tieflingDrawEligible: p.race === 'tieffelin' ? true : p.tieflingDrawEligible,
          }},
        };
        return { state: addLog(s, action.playerId, p.name, `pioche Halfling : choisissez une carte`), log: null };
      }

      const card = drawNormal(mn, mx);
      const s = {
        ...state,
        players: { ...state.players, [action.playerId]: {
          ...p,
          hand: [...p.hand, card],
          tieflingDrawEligible: p.race === 'tieffelin' ? true : p.tieflingDrawEligible,
          splitAvailable: true,
        }},
      };
      return { state: addLog(s, action.playerId, p.name, `pioche ${card.value}${card.suit}`), log: null };
    }

    case 'DRAW_FORCE': {
      const p = state.players[action.playerId];
      if (!p || p.tokens.force <= 0 || p.pendingHalfling) return { state, log: null };
      const mn = p.minDrawValue ?? 1, mx = p.maxDrawValue ?? 13;
      let updatedPlayer;

      if (p.race === 'halfling') {
        const cardA = drawNormal(mn, mx);
        const cardB = drawNormal(mn, mx);
        updatedPlayer = {
          ...p,
          tokens: { ...p.tokens, force: p.tokens.force - 1 },
          pendingHalfling: [cardA, cardB],
        };
      } else {
        const card = drawNormal(mn, mx);
        updatedPlayer = {
          ...p,
          tokens: { ...p.tokens, force: p.tokens.force - 1 },
          hand: [...p.hand, card],
          splitAvailable: true,
        };
      }

      // AASIMAR: a normal Heart card joins the hand after full token resolution
      const aasimar = maybeAasimarHeart(updatedPlayer);
      updatedPlayer = aasimar.player;

      const s = {
        ...state,
        discard: [...state.discard, ...aasimar.discarded],
        players: { ...state.players, [action.playerId]: updatedPlayer },
      };
      return { state: addLog(s, action.playerId, p.name, `token Force : pioche ${p.race === 'halfling' ? '(Halfling : choix)' : ''}`), log: null };
    }

    case 'GIVE_CARDS': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const target = state.players[action.targetId];
      if (!target) return { state, log: null };
      const crystal = !!action.crystal;
      const prefix = crystal ? 's' : 'n';
      let cards;
      if (action.mode === 'specific' && Array.isArray(action.cards) && action.cards.length > 0) {
        const valid = action.cards
          .filter(c => c && VALUES.includes(c.value) && SUITS.some(s => s.symbol === c.suit))
          .slice(0, 10);
        if (valid.length === 0) return { state, log: null };
        cards = valid.map(c => makeCard(c.suit, c.value, prefix));
      } else {
        const count = clamp(action.count ?? 1, 1, 10);
        const mn = target.minDrawValue ?? 1, mx = target.maxDrawValue ?? 13;
        cards = Array.from({ length: count }, () => drawNormal(mn, mx));
      }
      const dest = crystal ? 'crystallized' : 'hand';
      const s = {
        ...state,
        players: { ...state.players, [action.targetId]: {
          ...target, [dest]: [...target[dest], ...cards],
        }},
      };
      const label = crystal ? 'cristallisée(s)' : 'normale(s)';
      return { state: addLog(s, 'gm', 'MJ', `donne ${cards.length} carte(s) ${label} à ${target.name} : ${cards.map(c => c.value + c.suit).join(', ')}`), log: null };
    }

    case 'DEAL_ALL': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const updatedPlayers = { ...state.players };
      const dealtTo = [];
      for (const [id, pl] of Object.entries(state.players)) {
        if (id === action.playerId) continue;
        const cap = handCap(pl);
        if (pl.hand.length >= cap) continue;
        if (pl.pendingHalfling) continue;
        const hasExchange = (state.pendingExchanges ?? [])
          .some(e => e.from === id || e.to === id);
        if (hasExchange) continue;
        const mn = pl.minDrawValue ?? 1, mx = pl.maxDrawValue ?? 13;

        if (pl.race === 'halfling') {
          const cardA = drawNormal(mn, mx);
          const cardB = drawNormal(mn, mx);
          updatedPlayers[id] = { ...pl, pendingHalfling: [cardA, cardB] };
          dealtTo.push(pl.name + ' (Halfling)');
        } else {
          const card = drawNormal(mn, mx);
          updatedPlayers[id] = { ...pl, hand: [...pl.hand, card] };
          dealtTo.push(pl.name);
        }
      }
      const s = { ...state, players: updatedPlayers };
      return { state: addLog(s, 'gm', 'MJ', `distribue 1 carte à tous (${dealtTo.join(', ') || 'aucun'})`), log: null };
    }

    case 'DISCARD': {
      const p = state.players[action.playerId];
      if (!p) return { state, log: null };
      const from = action.from ?? 'hand';
      if (from === 'hand') {
        const isGrayed = (p.grayedCards ?? []).includes(action.cardId);
        const spiritLocked = p.hand.length <= (p.spiritBounds ?? 0);
        if (isGrayed || spiritLocked) return { state, log: null };
        const card = p.hand.find(c => c.id === action.cardId);
        if (!card) return { state, log: null };
        const s = {
          ...state,
          discard: [...state.discard, card],
          players: { ...state.players, [action.playerId]: {
            ...p, hand: p.hand.filter(c => c.id !== action.cardId),
          }},
        };
        return { state: addLog(s, action.playerId, p.name, `défausse ${card.value}${card.suit}`), log: null };
      } else {
        const card = p.crystallized.find(c => c.id === action.cardId);
        if (!card) return { state, log: null };
        const s = {
          ...state,
          discard: [...state.discard, card],
          players: { ...state.players, [action.playerId]: {
            ...p, crystallized: p.crystallized.filter(c => c.id !== action.cardId),
          }},
        };
        return { state: addLog(s, action.playerId, p.name, `joue/défausse cristallisée ${card.value}${card.suit}`), log: null };
      }
    }

    case 'CRYSTALLIZE': {
      const p = state.players[action.playerId];
      if (!p || (p.spiritBounds ?? 0) <= 0) return { state, log: null };
      const card = p.hand.find(c => c.id === action.cardId);
      if (!card) return { state, log: null };
      const s = {
        ...state,
        players: { ...state.players, [action.playerId]: {
          ...p,
          hand: p.hand.filter(c => c.id !== action.cardId),
          crystallized: [...p.crystallized, card],
          grayedCards: (p.grayedCards ?? []).filter(id => id !== action.cardId),
          spiritBounds: (p.spiritBounds ?? 0) - 1,
        }},
      };
      return { state: addLog(s, action.playerId, p.name, `cristallise ${card.value}${card.suit} (−1 Spirit Slot)`), log: null };
    }

    case 'USE_AGILITE': {
      const p = state.players[action.playerId];
      if (!p || p.tokens.agilite <= 0 || p.pendingHalfling) return { state, log: null };
      const actionCard = p.hand.find(c => c.id === action.cardId);
      if (!actionCard) return { state, log: null };
      const mn = p.minDrawValue ?? 1, mx = p.maxDrawValue ?? 13;
      const newCard = drawSpecialized(action.suit, mn, mx);
      let updatedPlayer = {
        ...p,
        tokens: { ...p.tokens, agilite: p.tokens.agilite - 1 },
        hand: [...p.hand.filter(c => c.id !== action.cardId), newCard],
      };
      const aasimar = maybeAasimarHeart(updatedPlayer);
      updatedPlayer = aasimar.player;
      const s = {
        ...state,
        discard: [...state.discard, actionCard, ...aasimar.discarded],
        players: { ...state.players, [action.playerId]: updatedPlayer },
      };
      return { state: addLog(s, action.playerId, p.name, `token Agilité : défausse ${actionCard.value}${actionCard.suit}, pioche ${newCard.value}${newCard.suit} (${action.suit})`), log: null };
    }

    case 'USE_ESPRIT': {
      const p = state.players[action.playerId];
      if (!p || p.tokens.esprit <= 0 || p.pendingHalfling) return { state, log: null };
      let updatedPlayer = {
        ...p,
        tokens: { ...p.tokens, esprit: p.tokens.esprit - 1 },
        spiritBounds: (p.spiritBounds ?? 0) + 1,
      };
      const aasimar = maybeAasimarHeart(updatedPlayer);
      updatedPlayer = aasimar.player;
      const s = {
        ...state,
        discard: [...state.discard, ...aasimar.discarded],
        players: { ...state.players, [action.playerId]: updatedPlayer },
      };
      return { state: addLog(s, action.playerId, p.name, `token Esprit : +1 Spirit Slot (total ${(p.spiritBounds ?? 0) + 1})`), log: null };
    }

    case 'PROPOSE_EXCHANGE': {
      const p = state.players[action.playerId];
      if (!p || p.tokens.social <= 0 || p.pendingHalfling) return { state, log: null };
      const card = p.hand.find(c => c.id === action.cardId);
      if (!card) return { state, log: null };
      if (!state.players[action.targetId]) return { state, log: null };
      const exchange = {
        id: `${action.playerId}-${Date.now()}`,
        from: action.playerId,
        fromCard: card,
        to: action.targetId,
      };
      let updatedPlayer = {
        ...p,
        tokens: { ...p.tokens, social: p.tokens.social - 1 },
        hand: p.hand.filter(c => c.id !== action.cardId),
      };
      const s = {
        ...state,
        pendingExchanges: [...(state.pendingExchanges ?? []), exchange],
        players: { ...state.players, [action.playerId]: updatedPlayer },
      };
      const targetName = state.players[action.targetId]?.name ?? action.targetId.slice(0, 8);
      return { state: addLog(s, action.playerId, p.name, `token Social : propose échange ${card.value}${card.suit} → ${targetName}`), log: null };
    }

    case 'ACCEPT_EXCHANGE': {
      const ex = (state.pendingExchanges ?? []).find(e => e.id === action.exchangeId);
      // Only the recipient may accept: exchange ids and every card id are
      // public in the broadcast state.
      if (!ex || action.playerId !== ex.to) return { state, log: null };
      const recipient = state.players[ex.to];
      const sender = state.players[ex.from];
      if (!recipient || !sender) return { state, log: null };
      const myCard = recipient.hand.find(c => c.id === action.cardId);
      if (!myCard) return { state, log: null };
      let updatedSender = { ...sender, hand: [...sender.hand, myCard] };
      const aasimar = maybeAasimarHeart(updatedSender);
      updatedSender = aasimar.player;
      const s = {
        ...state,
        discard: [...state.discard, ...aasimar.discarded],
        pendingExchanges: state.pendingExchanges.filter(e => e.id !== ex.id),
        players: {
          ...state.players,
          [ex.from]: updatedSender,
          [ex.to]: { ...recipient, hand: [...recipient.hand.filter(c => c.id !== myCard.id), ex.fromCard] },
        },
      };
      return { state: addLog(s, ex.to, recipient.name, `accepte échange avec ${sender.name} : donne ${myCard.value}${myCard.suit}, reçoit ${ex.fromCard.value}${ex.fromCard.suit}`), log: null };
    }

    case 'DECLINE_EXCHANGE': {
      const ex = (state.pendingExchanges ?? []).find(e => e.id === action.exchangeId);
      if (!ex || action.playerId !== ex.to) return { state, log: null };
      const sender = state.players[ex.from];
      if (!sender) return { state, log: null };
      // Refund the Social token spent to propose, clamped to the effective cap:
      // REST_ALL or a SET_RACE away from Humain can refill/shrink the Social
      // pool while the exchange is pending, so a bare +1 could push the sender
      // over their cap. Mirrors CANCEL_EXCHANGE. A missing cap key falls back to
      // what they held: a refund must never destroy the token.
      const socialCap = maxTokensFor(sender).social ?? sender.tokens.social;
      const s = {
        ...state,
        pendingExchanges: state.pendingExchanges.filter(e => e.id !== ex.id),
        players: {
          ...state.players,
          [ex.from]: {
            ...sender,
            hand: [...sender.hand, ex.fromCard],
            tokens: { ...sender.tokens, social: Math.min(sender.tokens.social + 1, socialCap) },
          },
        },
      };
      const recipient = state.players[action.playerId];
      return { state: addLog(s, action.playerId, recipient?.name ?? '', `refuse échange de ${sender.name} (${ex.fromCard.value}${ex.fromCard.suit})`), log: null };
    }

    case 'CANCEL_EXCHANGE': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const ex = (state.pendingExchanges ?? []).find(e => e.id === action.exchangeId);
      if (!ex) return { state, log: null };
      const sender = state.players[ex.from];
      if (!sender) return { state, log: null };
      // Same refund as DECLINE_EXCHANGE (card + the Social token spent to
      // propose), clamped to the effective cap: REST_ALL or a SET_RACE away
      // from Humain can refill/shrink the Social pool while the exchange is
      // pending, so a bare +1 could push the sender over their cap. A missing
      // cap key falls back to what they held: never destroy the token.
      const socialCap = maxTokensFor(sender).social ?? sender.tokens.social;
      const s = {
        ...state,
        pendingExchanges: state.pendingExchanges.filter(e => e.id !== ex.id),
        players: {
          ...state.players,
          [ex.from]: {
            ...sender,
            hand: [...sender.hand, ex.fromCard],
            tokens: { ...sender.tokens, social: Math.min(sender.tokens.social + 1, socialCap) },
          },
        },
      };
      return { state: s, log: null };
    }

    case 'SPEND_TOKEN': {
      // A player spends their own; a GM may spend for a target (the table
      // referee consumes a token without impersonating the player — the actor
      // stays the GM so the write guard accepts it).
      const targetId = action.targetId ?? action.playerId;
      if (targetId !== action.playerId && !isGM(state, action.playerId)) return { state, log: null };
      const p = state.players[targetId];
      if (!p || !TOKEN_KEYS.has(action.token) || p.tokens[action.token] <= 0 || p.pendingHalfling) return { state, log: null };
      let updatedPlayer = {
        ...p,
        tokens: { ...p.tokens, [action.token]: p.tokens[action.token] - 1 },
      };
      const aasimar = maybeAasimarHeart(updatedPlayer);
      updatedPlayer = aasimar.player;
      const s = {
        ...state,
        discard: [...state.discard, ...aasimar.discarded],
        players: { ...state.players, [targetId]: updatedPlayer },
      };
      const msg = targetId === action.playerId
        ? `token ${action.token} : usage combat`
        : `token ${action.token} de ${p.name} : usage par le MJ`;
      return { state: addLog(s, targetId, p.name, msg), log: null };
    }

    case 'ADD_TOKEN': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const p = state.players[action.targetId];
      if (!p || !TOKEN_KEYS.has(action.token) || p.tokens[action.token] >= maxTokensFor(p)[action.token]) return { state, log: null };
      const s = {
        ...state,
        players: { ...state.players, [action.targetId]: {
          ...p,
          tokens: { ...p.tokens, [action.token]: p.tokens[action.token] + 1 },
        }},
      };
      return { state: s, log: null };
    }

    case 'GIVE_TOKEN': {
      // Hobgoblin « Commandement tactique » : the player hands one of their
      // own tokens to an ally (the GM can do it too, as a table referee).
      const giver = state.players[action.playerId];
      const target = state.players[action.targetId];
      if (!giver || !target || action.playerId === action.targetId) return { state, log: null };
      if (!TOKEN_KEYS.has(action.token)) return { state, log: null };
      if (giver.race !== 'hobgoblin' && !isGM(state, action.playerId)) return { state, log: null };
      if ((giver.tokens[action.token] ?? 0) <= 0) return { state, log: null };
      if ((target.tokens[action.token] ?? 0) >= (maxTokensFor(target)[action.token] ?? 0)) return { state, log: null };
      const s = {
        ...state,
        players: { ...state.players,
          [action.playerId]: { ...giver, tokens: { ...giver.tokens, [action.token]: giver.tokens[action.token] - 1 } },
          [action.targetId]: { ...target, tokens: { ...target.tokens, [action.token]: (target.tokens[action.token] ?? 0) + 1 } },
        },
      };
      return { state: addLog(s, action.playerId, giver.name, `donne 1 jeton ${action.token} à ${target.name}`), log: null };
    }

    case 'DEVOUR_MIND': {
      // Illithid « Dévoration mentale » : +1 Esprit, throttled by the rule's
      // 30-minute cooldown (the once-per-combat half is table-side).
      const p = state.players[action.playerId];
      if (!p || p.race !== 'illithid') return { state, log: null };
      if (p.lastDevourAt && Date.now() - p.lastDevourAt < DEVOUR_COOLDOWN_MS) return { state, log: null };
      const cap = maxTokensFor(p).esprit ?? 0;
      if ((p.tokens.esprit ?? 0) >= cap) return { state, log: null };
      const s = {
        ...state,
        players: { ...state.players, [action.playerId]: {
          ...p,
          tokens: { ...p.tokens, esprit: (p.tokens.esprit ?? 0) + 1 },
          lastDevourAt: Date.now(),
        }},
      };
      return { state: addLog(s, action.playerId, p.name, 'dévoration mentale : +1 jeton Esprit'), log: null };
    }

    case 'TOGGLE_GRAY': {
      const p = state.players[action.playerId];
      if (!p) return { state, log: null };
      const grayed = p.grayedCards ?? [];
      const next = grayed.includes(action.cardId)
        ? grayed.filter(id => id !== action.cardId)
        : [...grayed, action.cardId];
      const s = {
        ...state,
        players: { ...state.players, [action.playerId]: { ...p, grayedCards: next } },
      };
      return { state: s, log: null };
    }

    case 'SWAP_CARD': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const p = state.players[action.targetId];
      if (!p) return { state, log: null };
      const oldCard = p.hand.find(c => c.id === action.oldCardId);
      if (!oldCard) return { state, log: null };
      const prefix = action.source === 'normal' ? 'n' : 's';
      const newCard = makeCard(action.suit, action.value, prefix);
      const s = {
        ...state,
        discard: [...state.discard, oldCard],
        players: {
          ...state.players,
          [action.targetId]: { ...p, hand: p.hand.map(c => c.id === oldCard.id ? newCard : c) },
        },
      };
      return { state: addLog(s, 'gm', 'MJ', `remplace ${oldCard.value}${oldCard.suit} → ${newCard.value}${newCard.suit} dans la main de ${p.name}`), log: null };
    }

    case 'SET_MAX_HAND': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const p = state.players[action.targetId];
      if (!p) return { state, log: null };
      const s = {
        ...state,
        players: { ...state.players, [action.targetId]: {
          ...p, maxHandSize: clamp(Number(action.val), 0, 15),
        }},
      };
      return { state: s, log: null };
    }

    case 'SET_DRAW_RANGE': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      // Allowlist: a free-form field name could overwrite `hand`/`tokens` and
      // brick the room for every client.
      if (action.field !== 'minDrawValue' && action.field !== 'maxDrawValue') return { state, log: null };
      const p = state.players[action.targetId];
      if (!p) return { state, log: null };
      const s = {
        ...state,
        players: { ...state.players, [action.targetId]: {
          ...p, [action.field]: clamp(Number(action.val), 1, 13),
        }},
      };
      return { state: s, log: null };
    }

    case 'SET_MAX_TOKENS': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const p = state.players[action.targetId];
      if (!p || !TOKEN_KEYS.has(action.token)) return { state, log: null };
      const maxTokens = { ...p.maxTokens, [action.token]: clamp(Math.floor(Number(action.val) || 0), 0, 10) };
      // Lowering the cap must bring the pool down with it, otherwise the sheet
      // showed 4/2 and the next refill silently "found" the extra token.
      const cap = maxTokensFor({ ...p, maxTokens })[action.token] ?? 0;
      const s = {
        ...state,
        players: { ...state.players, [action.targetId]: {
          ...p,
          maxTokens,
          tokens: { ...p.tokens, [action.token]: Math.min(p.tokens[action.token] ?? 0, cap) },
        }},
      };
      return { state: s, log: null };
    }

    case 'SET_TOKENS': {
      // GM: set a player's current pool directly (the "consume one token at the
      // table" gesture). Clamped to that player's effective cap.
      if (!isGM(state, action.playerId)) return { state, log: null };
      const p = state.players[action.targetId];
      if (!p || !TOKEN_KEYS.has(action.token)) return { state, log: null };
      const cap = maxTokensFor(p)[action.token] ?? 0;
      const next = clamp(Math.floor(Number(action.val) || 0), 0, cap);
      const s = {
        ...state,
        players: { ...state.players, [action.targetId]: {
          ...p,
          tokens: { ...p.tokens, [action.token]: next },
        }},
      };
      return { state: addLog(s, 'gm', 'MJ', `jetons ${action.token} de ${p.name} → ${next}/${cap}`), log: null };
    }

    case 'REST_ALL': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const updated = {};
      for (const [id, p] of Object.entries(state.players)) {
        updated[id] = { ...p, tokens: { ...maxTokensFor(p) } };
      }
      return { state: { ...state, players: updated }, log: null };
    }

    case 'HARD_RESET': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const fresh = createInitialGameState();
      const players = {};
      for (const [id, p] of Object.entries(state.players)) {
        const np = createEmptyPlayer(p.name);
        np.race = p.race ?? null;
        players[id] = np;
      }
      return { state: { ...fresh, gmId: state.gmId, players }, log: null };
    }

    case 'IMPORT_STATE': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const imported = action.state;
      if (!imported || typeof imported !== 'object' || !imported.players || typeof imported.players !== 'object') {
        return { state, log: null };
      }
      // Normalise through the hydrator: an unhydrated payload used to reach
      // dehydrateState() and throw, breaking the room for every client.
      return { state: hydrateState(imported), log: null };
    }

    case 'CREATE_GM_CHAR': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const s = {
        ...state,
        gmCharacterId: GM_CHAR_ID,
        players: { ...state.players, [GM_CHAR_ID]: createEmptyPlayer('Personnage MJ') },
      };
      return { state: s, log: null };
    }

    case 'REMOVE_GM_CHAR': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const players = { ...state.players };
      delete players[GM_CHAR_ID];
      const pendingExchanges = (state.pendingExchanges ?? []).filter(
        e => e.from !== GM_CHAR_ID && e.to !== GM_CHAR_ID,
      );
      return { state: { ...state, gmCharacterId: null, pendingExchanges, players }, log: null };
    }

    case 'SET_FATIGUE': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const p = state.players[action.targetId];
      if (!p) return { state, log: null };
      const level = clamp(Number(action.level), 0, 4);
      const s = {
        ...state,
        players: { ...state.players, [action.targetId]: {
          ...p, fatigue: level,
        }},
      };
      return { state: addLog(s, 'gm', 'MJ', `fatigue de ${p.name} → niveau ${level}`), log: null };
    }

    case 'SET_RACE': {
      // GM may set any player's race; a player may set their own
      // (character-sheet import / edit syncs the race into game state).
      const isSelf = action.playerId === action.targetId;
      if (!isGM(state, action.playerId) && !isSelf) return { state, log: null };
      const p = state.players[action.targetId];
      if (!p) return { state, log: null };
      const race = action.race && RACE_IDS.has(action.race) ? action.race : null;
      // Runnable token caps are base + racial bonus: entering a race grants
      // the bonus tokens once, leaving it clamps them back down.
      const next = { ...p, race };
      const tokens = { ...p.tokens };
      for (const key of TOKEN_KEYS) {
        const delta = (tokenCapBonus(race)[key] ?? 0) - (tokenCapBonus(p.race)[key] ?? 0);
        tokens[key] = clamp((tokens[key] ?? 0) + delta, 0, maxTokensFor(next)[key] ?? 0);
      }
      // A pending Halfling choice holds 2 real drawn cards — don't vaporise them.
      const s = {
        ...state,
        discard: [...state.discard, ...(p.pendingHalfling ?? [])],
        players: { ...state.players, [action.targetId]: {
          ...next,
          tokens,
          tieflingDrawEligible: true,
          pendingHalfling: null,
        }},
      };
      const label = race ? RACES.find(r => r.id === race)?.label ?? race : 'aucune';
      return { state: addLog(s, 'gm', 'MJ', `race de ${p.name} → ${label}`), log: null };
    }

    case 'SYNC_TOKENS': {
      // Sheet import/edit sync: caps = stat mods + 1. `counts` (optional) sets
      // the current pool instead of a full refill, so an imported sheet can say
      // "2 tokens left" — a refill-only sync made a decreased pool impossible.
      // GM may sync any player, a player their own.
      const isSelf = action.playerId === action.targetId;
      if (!isGM(state, action.playerId) && !isSelf) return { state, log: null };
      const p = state.players[action.targetId];
      if (!p) {
        // A player with no game-state record (room not initialised, or joined
        // after INIT_GAME) used to fail silently: the import looked broken.
        // The GM gets the notice; a player's own retry must not be able to fill
        // the shared log with it.
        if (!isGM(state, action.playerId)) return { state, log: null };
        return { state: addLog(state, 'gm', 'MJ', 'tokens non synchronisés : joueur non enregistré'), log: null };
      }
      const values = action.tokens ?? {};
      const norm = (v) => clamp(Math.floor(Number(v) || 0), 0, 10);
      const max = {
        force: norm(values.force),
        agilite: norm(values.agilite),
        esprit: norm(values.esprit),
        social: norm(values.social),
      };
      const caps = maxTokensFor({ ...p, maxTokens: max });
      const countFor = (v, cap) => clamp(Math.floor(Number(v ?? cap) || 0), 0, cap ?? 0);
      const tokens = action.counts
        ? {
            force: countFor(action.counts.force, caps.force),
            agilite: countFor(action.counts.agilite, caps.agilite),
            esprit: countFor(action.counts.esprit, caps.esprit),
            social: countFor(action.counts.social, caps.social),
          }
        : { ...caps };
      const s = {
        ...state,
        players: { ...state.players, [action.targetId]: {
          ...p,
          tokens,
          maxTokens: max,
        }},
      };
      return { state: addLog(s, action.playerId, p.name, `tokens synchronisés (F ${max.force} · A ${max.agilite} · E ${max.esprit} · S ${max.social})`), log: null };
    }

    case 'DRAW_SPADE': {
      const p = state.players[action.playerId];
      if (!p || p.race !== 'tieffelin' || !p.tieflingDrawEligible) return { state, log: null };
      if (p.pendingHalfling) return { state, log: null };
      const cap = handCap(p);
      if (p.hand.length >= cap) return { state, log: null };
      const mn = p.minDrawValue ?? 1, mx = p.maxDrawValue ?? 13;
      const card = drawSpecialized('♠', mn, mx);
      const s = {
        ...state,
        players: { ...state.players, [action.playerId]: {
          ...p,
          hand: [...p.hand, card],
          tieflingDrawEligible: false,
        }},
      };
      return { state: addLog(s, action.playerId, p.name, `pioche Pique ${card.value}${card.suit} (Tieffelin)`), log: null };
    }

    case 'HALFLING_CHOOSE': {
      const p = state.players[action.playerId];
      if (!p || !p.pendingHalfling) return { state, log: null };
      const chosen = p.pendingHalfling.find(c => c.id === action.cardId);
      if (!chosen) return { state, log: null };
      const discarded = p.pendingHalfling.find(c => c.id !== action.cardId);
      const s = {
        ...state,
        discard: discarded ? [...state.discard, discarded] : state.discard,
        players: { ...state.players, [action.playerId]: {
          ...p,
          hand: [...p.hand, chosen],
          pendingHalfling: null,
        }},
      };
      return { state: addLog(s, action.playerId, p.name, `Halfling : choisit ${chosen.value}${chosen.suit}`), log: null };
    }

    case 'SPLIT_CARD': {
      // Nimbri « Compréhension abstraite de la magie »: split one card of the
      // hand into two equal halves (11 → 5 + 5), once per explicit draw and
      // with no time limit (issue #15). The remainder is lost, as the rule says.
      const p = state.players[action.playerId];
      if (!p || p.race !== 'nimbri' || p.pendingHalfling) return { state, log: null };
      // No cooldown: the rule's "once per round" is managed at the table
      // (issue #15). The draw is the only gate.
      if (p.hand.length >= handCap(p)) return { state, log: null };
      const card = p.hand.find(c => c.id === action.cardId);
      if (!card) return { state, log: null };
      const half = Math.floor(faceValue(card) / 2);
      // A value of 2 or less cannot be halved into a playable card.
      if (half < 2) return { state, log: null };
      const value = VALUES[half - 2];
      const first = makeCard(card.suit, value, 's');
      const second = makeCard(card.suit, value, 's');
      const hand = p.hand.flatMap(c => (c.id === card.id ? [first, second] : [c]));
      const s = {
        ...state,
        players: { ...state.players, [action.playerId]: {
          ...p,
          hand,
          splitAvailable: false,
        }},
      };
      return {
        state: addLog(s, action.playerId, p.name, `division : ${card.value}${card.suit} → ${value}${card.suit} + ${value}${card.suit}`),
        log: null,
      };
    }

    case 'SPORELIN_EXCHANGE': {
      const p = state.players[action.playerId];
      if (!p || p.race !== 'sporelin' || p.pendingHalfling) return { state, log: null };
      const hasExchange = (state.pendingExchanges ?? [])
        .some(e => e.from === action.playerId || e.to === action.playerId);
      if (hasExchange) return { state, log: null };
      const card = p.hand.find(c => c.id === action.cardId);
      if (!card) return { state, log: null };
      const exchange = {
        id: `${action.playerId}-${Date.now()}`,
        from: action.playerId,
        fromCard: card,
        to: action.targetId,
      };
      const s = {
        ...state,
        pendingExchanges: [...(state.pendingExchanges ?? []), exchange],
        players: { ...state.players, [action.playerId]: {
          ...p,
          hand: p.hand.filter(c => c.id !== action.cardId),
        }},
      };
      const targetName = state.players[action.targetId]?.name ?? action.targetId.slice(0, 8);
      return { state: addLog(s, action.playerId, p.name, `échange Sporelin : propose ${card.value}${card.suit} → ${targetName}`), log: null };
    }

    case 'SET_INITIATIVE_URL': {
      if (!isGM(state, action.playerId)) return { state, log: null };
      const url = action.url ? String(action.url).slice(0, 2048) : null;
      const s = { ...state, initiativeUrl: url };
      const msg = url ? `a défini l'URL du tracker d'initiative` : `a retiré l'URL du tracker d'initiative`;
      return { state: addLog(s, 'gm', 'MJ', msg), log: null };
    }

    case 'USE_CAPACITY': {
      // Log-only: capacity costs are visual (card value + suit), no hand/token changes.
      const p = state.players[action.playerId];
      if (!p) return { state, log: null };
      const capacityName = typeof action.capacityName === 'string' ? action.capacityName.slice(0, 120) : '';
      const formula = typeof action.formula === 'string' ? action.formula.slice(0, 32) : '';
      const total = Number(action.total);
      if (!capacityName || !formula || !Number.isFinite(total)) return { state, log: null };
      const rolls = Array.isArray(action.rolls)
        ? action.rolls.map((n) => Number(n)).filter((n) => Number.isFinite(n)).slice(0, 64)
        : [];
      const detail = rolls.length > 0 ? ` [${rolls.join(', ')}]` : '';
      return { state: addLog(state, action.playerId, p.name, `utilise « ${capacityName} » (${formula}) : ${total}${detail}`), log: null };
    }

    default:
      return { state, log: null };
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Hydration / Dehydration
//
// OBR room metadata has a limited payload size. Storing full card objects
// (id + suit + value + numericValue + isRed) for 156 + 156 cards would
// exceed that limit. Instead we store only card ID strings (~9 chars each)
// and reconstruct full objects on the client side.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Convert raw OBR-stored state (ID strings everywhere) back to runtime state
 * (full card objects). Also handles legacy formats where full objects were stored.
 */
export function hydrateState(raw) {
  const players = {};
  for (const [id, p] of Object.entries(raw.players ?? {})) {
    players[id] = {
      ...p,
      maxHandSize:  p.maxHandSize  ?? 3,
      hand:         (p.hand        ?? []).map(toCard),
      crystallized: (p.crystallized ?? []).map(toCard),
      tokens:       p.tokens    ?? { force: 3, agilite: 3, esprit: 3, social: 3 },
      maxTokens:    p.maxTokens ?? { force: 3, agilite: 3, esprit: 3, social: 3 },
      minDrawValue: p.minDrawValue ?? 1,
      maxDrawValue: p.maxDrawValue ?? 13,
      grayedCards:  p.grayedCards  ?? [],
      spiritBounds: p.spiritBounds ?? 0,
      race:         p.race ?? null,
      tieflingDrawEligible: p.tieflingDrawEligible ?? true,
      pendingHalfling: p.pendingHalfling ?? null,
      lastDevourAt: p.lastDevourAt ?? 0,
      splitAvailable: p.splitAvailable ?? false,
    };
  }

  const pendingExchanges = (raw.pendingExchanges ?? []).map(ex => ({
    ...ex,
    fromCard: toCard(ex.fromCard),
  }));

  return {
    discard:          (raw.discard ?? []).map(toCard),
    pendingExchanges,
    lastActionIds:    raw.lastActionIds ?? [],
    gmId:             raw.gmId          ?? null,
    gmCharacterId:    raw.gmCharacterId ?? null,
    players,
    logs:             raw.logs ?? [],
    initiativeUrl:    raw.initiativeUrl ?? null,
  };
}

/**
 * Convert runtime state (full card objects) to compact storage state (ID strings only).
 * This is what gets written to OBR metadata.
 */
export function dehydrateState(state) {
  const toId = c => c.id;

  const players = {};
  for (const [id, p] of Object.entries(state.players)) {
    players[id] = {
      ...p,
      hand:         p.hand.map(toId),
      crystallized: p.crystallized.map(toId),
    };
  }

  return {
    discard:          state.discard.map(toId),
    pendingExchanges: state.pendingExchanges.map(ex => ({ ...ex, fromCard: ex.fromCard.id })),
    lastActionIds:    state.lastActionIds ?? [],
    gmId:             state.gmId,
    gmCharacterId:    state.gmCharacterId,
    players,
    logs:             state.logs ?? [],
    initiativeUrl:    state.initiativeUrl ?? null,
  };
}

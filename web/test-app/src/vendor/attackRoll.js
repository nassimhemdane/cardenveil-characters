// Attack roll engine — implements docs/Reglejetdattaque.md (+ its patch).
// One roll, kept die = damage die; each avantage/désavantage level adds 2
// dice keeping max/min; they cancel first, then engagement adds its levels
// as désavantages + its stat mod to damage. Crit = kept die at max face →
// explosion chains (advantage decays one level per explosion; désavantage
// explosions are always plain 1dX; Hache/Brutalité explodes 2dX summed with
// doubles chaining). Finesse repeats weapon + engagement bonuses once per
// crit. Stat keys follow the sheet convention (agilite, unaccented).
// Gobelin: crit threshold dé − 1 and a 3-crit cap per basic attack (doc §16).
import { statModifier, toNumber, weaponTags } from './characterSheet.js';

const FINESS_RE = /finesse/i;
const LONG_SWORD_RE = /épée\s*longue|epee\s*longue|longsword/i;
const CATALYSEUR_RE = /catalyseur/i;
const HACHE_RE = /brutalité|hache/i;
const BRUTE_RE = /\bbrute\b/i;
const STAT_LABELS_FR = { force: 'Force', agilite: 'Agilité', esprit: 'Esprit' };

/** Gobelin racial cap (doc §16): at most 3 crits on a basic (⚔️) attack. */
export const GOBELIN_MAX_CRITS = 3;

/** Race check tolerant to id/label/accent casing ('Gobelin', 'gobelin'). */
export function isGobelin(race) {
  return /gobelin/i.test(String(race ?? ''));
}

/** Goliath « Force colossale » : les épées longues comptent comme Finesse. */
export function isGoliath(race) {
  return /goliath/i.test(String(race ?? ''));
}

/** Weapon flags from the tag list (+ the legacy free-text `proprietes` and the
 *  name, for sheets not migrated yet). `race` adds the racial weapon rules
 *  (Goliath longsword = Finesse).
 */
export function weaponFlags(weapon, race) {
  const tags = weaponTags(weapon);
  const props = weapon?.proprietes ?? weapon?.['propriétés'] ?? '';
  const text = `${weapon?.nom ?? ''} ${props}`;
  const taggedFinesse =
    tags.includes('finesse') || FINESS_RE.test(text) || (isGoliath(race) && LONG_SWORD_RE.test(text));
  // The GM's checkbox (weapon.finesse) wins over the tag; an unchecked box is
  // how a Finesse weapon stops scaling with Agilité.
  const explicit = typeof weapon?.finesse === 'boolean' ? weapon.finesse : null;
  return {
    finesse: explicit ?? taggedFinesse,
    taggedFinesse,
    catalyseur: tags.includes('catalyseur') || CATALYSEUR_RE.test(text),
    hache: tags.includes('brutalite') || HACHE_RE.test(text),
    hybride: tags.includes('hybride'),
    amplitude: tags.includes('amplitude'),
    // « Brute » : l'arme ne peut pas infliger de coup critique (issue #11).
    brute: tags.includes('brute') || BRUTE_RE.test(text),
  };
}

/** Stat whose modifier engagement adds to damage (Finesse→agilite, Catalyseur→esprit, else force). */
export function engagementStat(weapon, race) {
  const { finesse, catalyseur } = weaponFlags(weapon, race);
  if (finesse) return 'agilite';
  if (catalyseur) return 'esprit';
  return 'force';
}

function statMod(stats, stat) {
  const score = Number(stats?.[stat]);
  return statModifier(Number.isFinite(score) ? score : 10);
}

const fmtMod = (value) => (value >= 0 ? `+${value}` : String(value));

function rollDice(count, sides, rng = Math.random) {
  return Array.from({ length: count }, () => 1 + Math.floor(rng() * sides));
}

const keepValue = (dice, keep) =>
  keep === 'max' ? Math.max(...dice) : keep === 'min' ? Math.min(...dice) : dice[0];

/**
 * Resolve which equipped weapon the attack panel targets. Falls back through
 * the saved name → main hand → first equipped, so a stale/missing selection
 * never leaves the panel blank (e.g. after re-equipping). Duplicate names
 * resolve to array order.
 * @param {Array} [weapons] - Sheet weapons array
 * @param {string} [preferredName] - Last used / saved weapon name
 * @returns {{weapon: Object|null, equipped: Array}} Selected weapon + equipped list
 */
export function pickAttackWeapon(weapons = [], preferredName = '') {
  const equipped = weapons.filter((w) => w?.equipped);
  if (!equipped.length) return { weapon: null, equipped };
  const preferred = preferredName ? equipped.find((w) => w?.nom === preferredName) : null;
  const weapon = preferred ?? equipped.find((w) => (w?.hand ?? 'main') === 'main') ?? equipped[0] ?? null;
  return { weapon, equipped };
}

/**
 * Static parts of an attack (no dice): die count, keep rule, bonuses,
 * engagement stat. Powers the live preview in SheetPopover.
 * @param {Object} weapon - Equipped weapon ({ de, bonus, proprietes, nom })
 * @param {Object} [stats] - Raw stats ({ force, agilite, esprit, social })
 * @param {{advantage?: number, engagement?: number, bonus?: number, rng?: Function, amplitude?: boolean, finesse?: boolean}} [opts]
 *   advantage: −7…+7 (− = désavantage, + = avantage); engagement: 0…7 levels;
 *   bonus: optional bonus override (the BONUS ATT. stat) — undefined/empty
 *   falls back to the weapon's `bonus` field; rng: injectable die source
 *   for tests (default Math.random); amplitude: attacking at the weapon's max
 *   range, which grants Finesse for that attack; finesse: the attack panel's
 *   checkbox (issue #10), which overrides the weapon's own answer
 * @returns {null|{level, diceCount, keep, sides, weaponBonus, engagementMod,
 *   engagementStat, finesse, hache}}
 */
export function attackPreview(weapon, stats = {}, { advantage = 0, engagement = 0, bonus, race, amplitude = false, finesse: finesseOption } = {}) {
  const match = String(weapon?.de ?? '').match(/(\d*)\s*d\s*(\d+)/i);
  if (!match) return null;
  const sides = parseInt(match[2], 10);
  if (!(sides >= 2)) return null;
  const gobelin = isGobelin(race);
  const flags = weaponFlags(weapon, race);
  // Amplitude grants Finesse at max range (a rule, so it wins); otherwise the
  // attack panel's checkbox overrides the weapon's own answer (issue #10).
  const finesse = amplitude && flags.amplitude
    ? true
    : typeof finesseOption === 'boolean' ? finesseOption : flags.finesse;
  const eStat = finesse ? 'agilite' : flags.catalyseur ? 'esprit' : 'force';
  // Hybride: the engagement adds BOTH modifiers (only their positive part),
  // and each crit adds the Agility one on top (issue #17). The preview shows
  // the non-crit value; the crit correction happens in runAttack.
  const hybrideEngagement = flags.hybride
    ? { force: Math.max(statMod(stats, 'force'), 0), agilite: Math.max(statMod(stats, 'agilite'), 0) }
    : null;
  const eng = Math.max(0, Math.round(Number(engagement) || 0));
  const adv = Math.round(Number(advantage) || 0);
  // Avantage/désavantage cancel BEFORE engagement applies (patch §1).
  const level = adv - eng;
  const kept = level > 0 ? 'max' : level < 0 ? 'min' : null;
  return {
    level,
    diceCount: 1 + 2 * Math.abs(level),
    keep: kept,
    sides,
    // Gobelin (doc §16): crit from dé − 1, capped at 3 crits per basic attack
    critFrom: gobelin ? Math.max(2, sides - 1) : sides,
    maxCrits: gobelin ? GOBELIN_MAX_CRITS : null,
    gobelin,
    weaponBonus: bonus === undefined || bonus === null || bonus === '' ? toNumber(weapon?.bonus) : toNumber(bonus),
    engagementMod: hybrideEngagement ? hybrideEngagement.force + hybrideEngagement.agilite : statMod(stats, eStat),
    engagementStat: eStat,
    hybrideEngagement,
    ...flags,
    finesse,
    // `amplitude` (from the flags) = the weapon HAS the property; this is the
    // effect applied to this attack.
    amplitudeApplied: Boolean(amplitude && flags.amplitude),
    advantage: adv,
    engagement: eng
  };
}

/**
 * Walk the attack stage-by-stage, taking dice from {@link rollStage}.
 * The walk holds ALL rule logic (seuil miss, explosion decay, Hache
 * doubles, Finesse repeats); {@link rollStage}(pool, sides, keep) supplies
 * the dice for each stage — synchronously (rng) or as a Promise (3D
 * physics driver). Returns the same result object as rollAttack.
 * @param {Object} weapon - Equipped weapon ({ de, bonus, proprietes, nom, seuilMiss })
 * @param {Object} [stats] - Raw stats
 * @param {{advantage?: number, engagement?: number, bonus?: number}} [opts]
 *   bonus: BONUS ATT. stat override (see attackPreview)
 * @param {(pool: number, sides: number, keep: string|null) => number[]|Promise<number[]>} rollStage
 * @returns {Promise<Object|null>} Same shape as rollAttack's result
 */
export async function runAttack(weapon, stats = {}, opts = {}, rollStage) {
  const p = attackPreview(weapon, stats, opts);
  if (!p) return null;
  const optEngagement = opts.engagement ?? 0;
  const { sides, level, finesse, hache, hybride, amplitude, brute, weaponBonus, engagementMod, engagementStat: eStat, engagement: engLevel, critFrom, maxCrits, gobelin } = p;
  // null = no racial cap (Infinity would break JSON payloads)
  const critCap = maxCrits ?? Infinity;
  const critNote = gobelin ? ` (seuil ${critFrom}+, max ${maxCrits})` : '';
  const keepMode = level > 0 ? 'max' : level < 0 ? 'min' : null;
  const stages = [];
  const breakdown = [];

  const stage = async (pool, keep) => {
    const dice = await rollStage(pool, sides, keep);
    const kept = keepValue(dice, keep);
    stages.push({ label: `${pool}d${sides} · garder ${keep ?? 'seul'}`, pool, keep, dice, kept, sides });
    return kept;
  };

  const levelNote = level === 0 ? '' : ` (${level > 0 ? '+' : '−'}${Math.abs(level)} ${Math.abs(level) === 1 ? 'niveau' : 'niveaux'})`;
  const keepNote = keepMode ? ` · garder ${keepMode}` : '';

  const initial = await stage(p.diceCount, keepMode);
  breakdown[0] = `Jet : ${p.diceCount}d${sides}${levelNote}${keepNote} [${stages[0].dice.join(', ')}] — gardé ${initial}`;
  let critCount = 0;
  const seuilMiss = toNumber(weapon?.seuilMiss);
  if (initial <= seuilMiss) {
    breakdown[0] = `Jet : ${p.diceCount}d${sides}${levelNote} [${stages[0].dice.join(', ')}] — gardé ${initial} ≤ seuil ${seuilMiss} → MISS`;
    breakdown.push('Dégâts : 0');
    return result(0, true);
  }

  let kept = initial;
  if (brute) {
    // Brute: the max face is just a high roll — no explosion, no crit.
    breakdown.push('Brute : pas de critique');
  } else if (hache) {
    if (initial >= critFrom) breakdown[0] += ' → CRIT';
    // Hache: advantage applies only to the initial roll (doc §18); each
    // explosion is 2dX summed, a double chains a new crit (§17-18).
    while (kept >= critFrom && critCount < critCap) {
      critCount++;
      await stage(2, 'somme');
      const pair = stages[stages.length - 1].dice;
      const sum = pair[0] + pair[1];
      stages[stages.length - 1].kept = sum;
      breakdown.push(`Explosion : 2d${sides} [${pair[0]}, ${pair[1]}] = ${sum}${pair[0] === pair[1] ? ' → CRIT (double)' : ''}`);
      kept = pair[0] === pair[1] ? sides : 0;
    }
  } else {
    let remainingLevel = level;
    while (kept >= critFrom && critCount < critCap) {
      critCount++;
      // Advantage decays one level per explosion (§8); désavantage explosions
      // are always a plain 1dX (§9).
      const keepNext = level > 0 && remainingLevel - 1 > 0 ? 'max' : null;
      const pool = keepNext ? 1 + 2 * (Math.abs(remainingLevel) - 1) : 1;
      const kept2 = await stage(pool, keepNext);
      breakdown.push(`Explosion : ${pool}d${sides} [${stages[stages.length - 1].dice.join(', ')}] — gardé ${kept2}${kept2 === sides ? ' → CRIT' : ''}`);
      kept = kept2;
      remainingLevel -= 1;
    }
    breakdown.push(`Critiques : ${critCount}${critNote}`);
  }

  // Bonuses. Finesse: (weapon bonus + engagement mods) × (1 + crit count)
  // (patch §2); otherwise weapon bonus once + engagement mods flat.
  //
  // Hybride (issue #17, the GM's later rule — it supersedes #12): the weapon
  // counts as Finesse for Agility only — the Agility modifier already sits
  // inside the weapon bonus, so nothing is added on top. Each crit repeats the
  // bonus, REDUCED by the POSITIVE Force modifier; a negative Force is simply
  // not taken into account (max(Force, 0)). The engagement adds both modifiers
  // (positive parts only) and each crit adds the Agility one on top.
  const forceMod = statMod(stats, 'force');
  const agiMod = statMod(stats, 'agilite');
  let engagementMods = engLevel * engagementMod;
  let hybrideBonus = 0;
  if (hybride) {
    hybrideBonus = critCount * (weaponBonus - Math.max(forceMod, 0));
    const perLevel = Math.max(forceMod, 0) + Math.max(agiMod, 0) + critCount * Math.max(agiMod, 0);
    engagementMods = engLevel * perLevel;
  }
  const flatBonus = hybride
    ? weaponBonus + hybrideBonus + engagementMods
    : finesse
      ? (weaponBonus + engagementMods) * (1 + critCount)
      : weaponBonus + engagementMods;
  const diceTotal = stages.reduce((sum, s) => sum + s.kept, 0);
  const total = diceTotal + flatBonus;

  // §20 equation — one term per contribution, so the sum reads at a glance.
  const parts = stages.map((s) => String(s.kept));
  if (hybride) {
    if (weaponBonus) parts.push(String(weaponBonus));
    if (hybrideBonus) parts.push(hybrideBonus > 0 ? String(hybrideBonus) : fmtMod(hybrideBonus));
    if (engagementMods) parts.push(engagementMods > 0 ? String(engagementMods) : fmtMod(engagementMods));
  } else if (flatBonus > 0) {
    parts.push(String(flatBonus));
  } else if (flatBonus < 0) {
    parts.push(fmtMod(flatBonus));
  }
  breakdown.push(`Calcul : ${parts.join(' + ')}`);
  breakdown.push(`Dégâts : ${total}`);
  if (!hybride && finesse && critCount > 0) {
    breakdown.splice(-2, 0, `Bonus répété ×${1 + critCount} (Finesse)`);
  }
  if (hybride) {
    breakdown.splice(-2, 0, critCount > 0
      ? `Hybride : bonus ×${1 + critCount} (Force positive soustraite), engagement Force + Agilité + Agilité par critique`
      : 'Hybride : dé + bonus (Agilité déjà comprise), engagement Force + Agilité');
  }
  return result(total, false, engagementMods, hybrideBonus);

  function result(total, miss, engagementTotal = engLevel * engagementMod, hybrideTotal = 0) {
    return {
      total,
      miss,
      critCount,
      kept: initial,
      stages,
      breakdown,
      finesse,
      hache,
      hybride,
      amplitude,
      brute,
      level,
      sides,
      weaponBonus,
      engagementMod,
      engagementTotal,
      hybrideBonus: hybrideTotal,
      engagementStat: eStat,
      advantage: level + optEngagement,
      engagement: optEngagement,
      critFrom,
      maxCrits,
      gobelin
    };
  }
}

/**
 * Resolve a full attack locally with an rng — thin sync-style wrapper over
 * {@link runAttack} (returns a Promise). The 3D pipeline drives runAttack
 * itself, feeding physics-read dice per stage.
 * @param {Object} weapon - Equipped weapon ({ de, bonus, proprietes, nom, seuilMiss })
 * @param {Object} [stats] - Raw stats
 * @param {{advantage?: number, engagement?: number, bonus?: number, rng?: Function}} [opts]
 * @returns {Promise<Object|null>} { total (0 on miss), miss, critCount, kept,
 *   stages: [{label, pool, keep, dice, kept, sides}], breakdown (§20 lines),
 *   finesse, hache, level, sides, weaponBonus, engagementMod, engagementStat,
 *   advantage, engagement }
 */
export function rollAttack(weapon, stats = {}, opts = {}) {
  const rng = opts.rng ?? Math.random;
  return runAttack(weapon, stats, opts, (pool, sides) => rollDice(pool, sides, rng));
}

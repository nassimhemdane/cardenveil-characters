/**
 * Three-way merge for character-sheet documents.
 *
 * `saveCharacterSheet` writes the WHOLE document, so two frames that each read
 * a sheet and edit a different field used to clobber each other (the later
 * write silently dropped the earlier edit). Saves now go through the
 * `apply_character_sheet` compare-and-swap RPC; when it reports a conflict the
 * intended local edit is re-applied on top of the server's newer document with
 * this merge, so both edits survive.
 *
 *   base   = the document the local edit started from
 *   mine   = the local document (the intended edit)
 *   theirs = the server's newer document
 *
 * Policy
 * - Objects are merged key by key, recursively.
 * - A key removed on one side and untouched on the other stays removed.
 * - A key removed on one side and EDITED on the other is a conflict: `mine`
 *   wins (the player's own latest action) and the path is recorded — never
 *   dropped silently.
 * - A leaf changed on both sides to different values is a conflict: `mine`
 *   wins and the path is recorded.
 * - Arrays of scalars (pinnedSkills, pinnedCapacities, narrative.traitsSpeciaux)
 *   are unioned: a one-sided removal does not survive a concurrent edit of the
 *   same list (re-pinning is one click; dropping a pin is not recoverable).
 * - Arrays of objects (weapons, inventoryItems, capacities, actions, feats…)
 *   are merged per item, by identity (`id`, else `nom`/`name`, else the item's
 *   JSON), so two frames editing different items — or different fields of the
 *   same item — both survive. Same-named items are paired positionally within
 *   their group and all occurrences are kept; a disagreement there is recorded
 *   as a `duplicate-key` conflict. A one-sided deletion only wins if the other
 *   side did not edit that item.
 *
 * Pure: no Supabase, no logging. The caller applies the result and reports
 * `conflicts`.
 */

const isPlainObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

const has = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

function deepEqual(a, b) {
  if (a === b) return true;
  if (Array.isArray(a) || Array.isArray(b)) {
    return Array.isArray(a) && Array.isArray(b) && a.length === b.length
      && a.every((value, index) => deepEqual(value, b[index]));
  }
  if (isPlainObject(a) && isPlainObject(b)) {
    const keys = Object.keys(a);
    return keys.length === Object.keys(b).length
      && keys.every((key) => has(b, key) && deepEqual(a[key], b[key]));
  }
  return false;
}

function mergeValue(base, mine, theirs, path, conflicts) {
  if (deepEqual(mine, theirs)) return mine;
  if (deepEqual(base, mine)) return theirs;
  if (deepEqual(base, theirs)) return mine;
  if (Array.isArray(mine) && Array.isArray(theirs)) return mergeArray(base, mine, theirs, path, conflicts);
  if (isPlainObject(mine) && isPlainObject(theirs)) return mergeObject(base, mine, theirs, path, conflicts);
  conflicts.push({ path, reason: 'both-changed' });
  return mine;
}

function mergeObject(base, mine, theirs, path, conflicts) {
  const b = isPlainObject(base) ? base : {};
  const out = {};
  const keys = new Set([...Object.keys(b), ...Object.keys(mine), ...Object.keys(theirs)]);

  for (const key of keys) {
    const keyPath = path ? `${path}.${key}` : key;
    const inBase = has(b, key);
    const inMine = has(mine, key);
    const inTheirs = has(theirs, key);

    if (inMine && inTheirs) {
      out[key] = mergeValue(inBase ? b[key] : undefined, mine[key], theirs[key], keyPath, conflicts);
      continue;
    }
    if (inMine) {
      if (inBase && deepEqual(mine[key], b[key])) continue; // removed on both sides
      out[key] = mine[key];
      if (inBase) conflicts.push({ path: keyPath, reason: 'delete-vs-edit' });
      continue;
    }
    if (inTheirs) {
      if (!inBase) out[key] = theirs[key]; // added on the server only
      else if (!deepEqual(theirs[key], b[key])) conflicts.push({ path: keyPath, reason: 'delete-vs-edit' });
      // else: untouched on the server, removed locally → stays removed
    }
  }
  return out;
}

function itemKey(item) {
  if (isPlainObject(item)) {
    for (const field of ['id', 'nom', 'name']) {
      const value = item[field];
      if (typeof value === 'number' || (typeof value === 'string' && value)) return `${field}:${value}`;
    }
  }
  return `json:${JSON.stringify(item)}`;
}

/**
 * Index items by identity, keeping EVERY occurrence: same-named items (13 live
 * sheets have two "Serpe") are paired positionally within their group as
 * `nom:Serpe`, `nom:Serpe#2`, … — keying by name alone silently dropped all but
 * the first.
 * @param {Array} list - Items to index
 * @returns {{ index: Map, bare: Map, totals: Map }} occurrence key → item,
 *   occurrence key → shared key, shared key → occurrences in this list
 */
function indexByKey(list) {
  const index = new Map();
  const bare = new Map();
  const totals = new Map();
  for (const item of list) {
    const key = itemKey(item);
    const occurrence = (totals.get(key) ?? 0) + 1;
    totals.set(key, occurrence);
    const occurrenceKey = occurrence === 1 ? key : `${key}#${occurrence}`;
    index.set(occurrenceKey, item);
    bare.set(occurrenceKey, key);
  }
  return { index, bare, totals };
}

function mergeArray(base, mine, theirs, path, conflicts) {
  const b = Array.isArray(base) ? base : [];

  // Scalar list: union, base order first, then local additions, then the rest.
  if ([...b, ...mine, ...theirs].every((value) => value === null || typeof value !== 'object')) {
    const out = [];
    for (const value of [...b, ...mine, ...theirs]) {
      if (!out.some((seen) => deepEqual(seen, value))) out.push(value);
    }
    return out;
  }

  const baseIndex = indexByKey(b);
  const mineIndex = indexByKey(mine);
  const theirsIndex = indexByKey(theirs);
  const out = [];

  // Shared keys with more than one item on any side: their pairing is
  // positional, so a disagreement there is recorded even when one side wins.
  const collisions = new Set();
  for (const { totals } of [baseIndex, mineIndex, theirsIndex]) {
    for (const [key, count] of totals) if (count > 1) collisions.add(key);
  }

  for (const key of new Set([...baseIndex.index.keys(), ...mineIndex.index.keys(), ...theirsIndex.index.keys()])) {
    const itemPath = `${path}[${key}]`;
    const inBase = baseIndex.index.has(key);
    const inMine = mineIndex.index.has(key);
    const inTheirs = theirsIndex.index.has(key);

    if (inMine && inTheirs) {
      const local = mineIndex.index.get(key);
      const remote = theirsIndex.index.get(key);
      const shared = mineIndex.bare.get(key);
      if (!deepEqual(local, remote) && collisions.has(shared)) {
        conflicts.push({ path: itemPath, reason: 'duplicate-key' });
      }
      out.push(mergeValue(
        inBase ? baseIndex.index.get(key) : undefined,
        local,
        remote,
        itemPath,
        conflicts,
      ));
      continue;
    }
    if (inMine) {
      if (!inBase) out.push(mineIndex.index.get(key)); // added locally
      else if (!deepEqual(mineIndex.index.get(key), baseIndex.index.get(key))) {
        out.push(mineIndex.index.get(key)); // edited locally, deleted on the server
        conflicts.push({ path: itemPath, reason: 'delete-vs-edit' });
      }
      continue;
    }
    if (inTheirs) {
      if (!inBase) out.push(theirsIndex.index.get(key)); // added on the server
      else if (!deepEqual(theirsIndex.index.get(key), baseIndex.index.get(key))) {
        conflicts.push({ path: itemPath, reason: 'delete-vs-edit' }); // deleted locally, edited on the server
      }
    }
  }
  return out;
}

/**
 * Merge a local edit onto a newer server document.
 * @param {Object} base - document the local edit started from ({} if unknown)
 * @param {Object} mine - local document
 * @param {Object} theirs - newer server document
 * @returns {{ sheet: Object, conflicts: Array<{ path: string, reason: string }> }}
 */
export function mergeSheet(base, mine, theirs) {
  const conflicts = [];
  const sheet = mergeObject(base ?? {}, mine ?? {}, theirs ?? {}, '', conflicts);
  return { sheet, conflicts };
}

export * from './sheetEngine.js';
import { createEmptyCharacterSheet, migrateSheet, normalizeRaceName, syncSkillBonuses, syncSlotsFromItems, syncStatsFromEquipment } from './sheetEngine.js';
import { read, write, listen } from '../storage.js';
export const healSheetBase = () => {};
export const onSheetBroadcast = () => () => {};
export async function fetchCharacterSheet() { return read('sheet'); }
export async function saveCharacterSheet(playerId, roomId, data) {
  const previous = await read('sheet');
  return write('sheet', { data, player_id: playerId, room_id: roomId, version: (previous?.version ?? 0) + 1 });
}
export async function deleteCharacterSheet(playerId, roomId) { return saveCharacterSheet(playerId, roomId, createEmptyCharacterSheet()); }
export function subscribeToCharacterSheet(playerId, roomId, callback) { return listen('sheet', callback); }
export async function importCharacterSheet(playerId, roomId, json) {
  const parsed = JSON.parse(json);
  if (!parsed || !parsed.identity || !parsed.stats || Array.isArray(parsed)) throw new Error('Fiche invalide : identité et caractéristiques requises.');
  for (const key of ['capacities', 'weapons', 'inventoryItems']) if (parsed[key] != null && !Array.isArray(parsed[key])) throw new Error(`Fiche invalide : ${key} doit être une liste.`);
  const merged = { ...createEmptyCharacterSheet(), ...parsed };
  const empty = createEmptyCharacterSheet();
  for (const key of ['identity','stats','progression','derived','defense','resources','skills','narrative','equipment','totem','actionChecks']) merged[key] = { ...empty[key], ...parsed[key] };
  merged.resources.tokens = { ...empty.resources.tokens, ...parsed.resources?.tokens };
  merged.identity.race = normalizeRaceName(merged.identity.race);
  return saveCharacterSheet(playerId, roomId, syncStatsFromEquipment(syncSlotsFromItems(syncSkillBonuses(migrateSheet(merged)))));
}

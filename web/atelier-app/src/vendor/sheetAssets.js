import { unzipSync, strFromU8 } from 'fflate';
import { importCharacterSheet } from './characterSheet.js';
export async function importSheetArchive(playerId, roomId, buffer) {
  const files = unzipSync(new Uint8Array(buffer), { filter: file => {
    if (file.originalSize > 25 * 1024 * 1024) throw new Error('Un fichier de cette archive dépasse 25 Mo.');
    return !file.name.includes('__MACOSX');
  } });
  const names = Object.keys(files);
  if (names.reduce((n, name) => n + files[name].length, 0) > 80 * 1024 * 1024) throw new Error('Archive décompressée trop volumineuse (80 Mo maximum).');
  const json = names.find(n => n.endsWith('.rpsheet.json')) ?? names.find(n => n.endsWith('.json') && !n.endsWith('metadata.json'));
  if (!json) throw new Error('Aucune fiche JSON dans cette archive.');
  const sheet = JSON.parse(strFromU8(files[json]));
  const image = value => {
    if (typeof value !== 'string' || !value.startsWith('/assets/')) return value;
    const name = names.find(n => n.toLowerCase() === value.slice(1).toLowerCase());
    if (!name) return '';
    const ext = name.split('.').pop().toLowerCase();
    const mime = {png:'image/png',jpg:'image/jpeg',jpeg:'image/jpeg',webp:'image/webp',gif:'image/gif'}[ext];
    if (!mime) return '';
    let binary = ''; const bytes = files[name];
    for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
    return `data:${mime};base64,${btoa(binary)}`;
  };
  sheet.portrait = image(sheet.portrait);
  if (sheet.totem) sheet.totem.image = image(sheet.totem.image);
  for (const cap of sheet.capacities ?? []) cap.image = image(cap.image);
  return importCharacterSheet(playerId, roomId, JSON.stringify(sheet));
}

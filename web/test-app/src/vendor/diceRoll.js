export const SIDES_TO_TYPE = { 4: 'd4', 6: 'd6', 8: 'd8', 10: 'd10', 12: 'd12', 20: 'd20', 100: 'd100' };

export function meshDefsFor(spec) {
  const defs = [];
  let rollIndex = 0;
  for (const { count, sides } of spec) {
    for (let i = 0; i < count; i++) {
      const index = rollIndex++;
      if (sides === 100) {
        defs.push({ type: 'd100', rollIndex: index, sides });
        defs.push({ type: 'd10', rollIndex: index, sides });
      } else {
        defs.push({ type: SIDES_TO_TYPE[sides], rollIndex: index, sides });
      }
    }
  }
  return defs;
}

export function groupDiceByRoll(dice) {
  const groups = [];
  for (const die of dice) (groups[die.def.rollIndex] ??= []).push(die);
  return groups;
}

export function rollValueForGroup(group, readFace) {
  if (group[0].def.sides === 100) {
    const tens = parseInt(readFace(group.find(({ def }) => def.type === 'd100')) ?? '0', 10);
    const ones = parseInt(readFace(group.find(({ def }) => def.type === 'd10')) ?? '0', 10);
    return tens === 0 && ones === 0 ? 100 : tens + ones;
  }
  const die = group[0];
  const value = readFace(die) ?? '1';
  return die.def.type === 'd10' && value === '0' ? 10 : parseInt(value, 10);
}

export const MAX_VISIBLE_DICE = 15;

export function visibleRollChip(value, sides, index, count, critFrom = sides) {
  if (index < MAX_VISIBLE_DICE) {
    return { value, crit: Number(value) >= critFrom, fail: Number(value) === 1 };
  }
  if (index === MAX_VISIBLE_DICE && count > MAX_VISIBLE_DICE) {
    return { more: count - MAX_VISIBLE_DICE };
  }
  return null;
}

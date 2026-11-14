import { applyAction, createInitialGameState, handCap, maxTokensFor, addLog } from './vendor/deck.js';
export const ACTOR = 'local-mj';
export const PARTNER = 'simulation';
export function freshGame() {
  let game = applyAction(createInitialGameState(), {type:'INIT_GAME', playerId:ACTOR}).state;
  game = applyAction(game, {type:'REGISTER_PLAYER', playerId:ACTOR, name:'Mon personnage'}).state;
  game.players[ACTOR].tokens = {force:1,agilite:1,esprit:1,social:1};
  game.players[ACTOR].maxTokens = {force:1,agilite:1,esprit:1,social:1};
  return game;
}
export function reduce(game, action) {
  if (action.type === 'SET_FATIGUE' && action.val != null) action = {...action, level:action.val};
  return applyAction(game, {playerId:ACTOR,targetId:ACTOR,...action}).state;
}
export function rest(game, kind, discardIds = []) {
  let next = JSON.parse(JSON.stringify(game));
  let p = next.players[ACTOR];
  // Slots crystallize at rest. Pick cards explicitly in the UI before this step.
  for (const card of p.hand.slice(0, p.spiritBounds)) next = reduce(next, {type:'CRYSTALLIZE',cardId:card.id});
  for (const cardId of discardIds) next = reduce(next, {type:'DISCARD',cardId,from:'hand'});
  p = next.players[ACTOR];
  p.tokens = {...maxTokensFor(p)};
  p.fatigue = Math.max(0, p.fatigue - (kind === 'long' ? 2 : 1));
  // Rest draw is a refill, not a new explicit racial draw on each iteration.
  const missing = Math.max(0, handCap(p) - p.hand.length);
  if (missing) next = reduce(next, {type:'GIVE_CARDS',count:missing});
  return addLog(next, ACTOR, 'MJ', `Repos ${kind === 'long' ? 'long' : 'court'} : jetons restaurés, main complétée, fatigue réduite.`);
}

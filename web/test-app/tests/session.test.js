import test from 'node:test';
import assert from 'node:assert/strict';
import {ACTOR, PARTNER, freshGame, reduce, rest} from '../src/session.js';
import {handCap, fatiguePenaltyFor} from '../src/vendor/deck.js';

test('a fresh local MJ draws up to hand cap; GM override can give a precise card', () => {
  let g = freshGame();
  for(let i=0;i<6;i++) g=reduce(g,{type:'DRAW'});
  assert.equal(g.players[ACTOR].hand.length,handCap(g.players[ACTOR]));
  g=reduce(g,{type:'GIVE_CARDS',mode:'specific',cards:[{suit:'♥',value:'A'}]});
  assert.equal(g.players[ACTOR].hand.at(-1).value,'A');
});
test('spirit slot and crystallization preserve capacity and card identity', () => {
  let g=reduce(freshGame(),{type:'DRAW'});
  const card=g.players[ACTOR].hand[0];
  g=reduce(g,{type:'USE_ESPRIT'});
  assert.equal(g.players[ACTOR].spiritBounds,1);
  g=reduce(g,{type:'CRYSTALLIZE',cardId:card.id});
  assert.equal(g.players[ACTOR].spiritBounds,0);
  assert.equal(g.players[ACTOR].crystallized[0].value,card.value);
});
test('simulated social exchange can be declined and refunds its token', () => {
  let g=reduce(freshGame(),{type:'DRAW'});
  g=reduce(g,{type:'REGISTER_PLAYER',playerId:PARTNER,name:'Allié fictif'});
  const card=g.players[ACTOR].hand[0];
  g=reduce(g,{type:'PROPOSE_EXCHANGE',cardId:card.id,targetId:PARTNER});
  assert.equal(g.players[ACTOR].tokens.social,0);
  g=reduce(g,{type:'DECLINE_EXCHANGE',playerId:PARTNER,exchangeId:g.pendingExchanges[0].id});
  assert.equal(g.players[ACTOR].tokens.social,1);
  assert.equal(g.players[ACTOR].hand[0].id,card.id);
});
test('rest consumes slots, refills hand and tokens and lowers linear fatigue', () => {
  let g=reduce(freshGame(),{type:'DRAW'});
  g=reduce(g,{type:'USE_ESPRIT'});
  g=reduce(g,{type:'SET_FATIGUE',val:2});
  g=rest(g,'court');
  const p=g.players[ACTOR];
  assert.equal(p.fatigue,1); assert.equal(p.spiritBounds,0);
  assert.equal(p.hand.length,3); assert.equal(p.crystallized.length,1);
  assert.equal(p.tokens.esprit,1); assert.equal(fatiguePenaltyFor('humain',2),2);
});
test('halfling must choose one of two cards before another draw', () => {
  let g=reduce(freshGame(),{type:'SET_RACE',race:'halfling'});
  g=reduce(g,{type:'DRAW'}); const choices=g.players[ACTOR].pendingHalfling;
  assert.equal(choices.length,2);
  g=reduce(g,{type:'HALFLING_CHOOSE',cardId:choices[0].id});
  assert.equal(g.players[ACTOR].hand[0].id,choices[0].id);
  assert.equal(g.discard.length,1);
});
test('Nimbri split is allowed without another draw but never exceeds hand cap', () => {
  let g=reduce(freshGame(),{type:'SET_RACE',race:'nimbri'});
  g=reduce(g,{type:'GIVE_CARDS',mode:'specific',cards:[{suit:'♠',value:'K'}]});
  g=reduce(g,{type:'SPLIT_CARD',cardId:g.players[ACTOR].hand[0].id});
  assert.equal(g.players[ACTOR].hand.length,2);
  g=reduce(g,{type:'DRAW'});
  const full=reduce(g,{type:'SPLIT_CARD',cardId:g.players[ACTOR].hand[0].id});
  assert.equal(full.players[ACTOR].hand.length,3);
});

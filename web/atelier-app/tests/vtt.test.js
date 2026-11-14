import test from 'node:test';
import assert from 'node:assert/strict';
import { freshTable, normalizeTable, moveItem, reorderItem, snap } from '../src/vttState.js';

test('la table locale démarre avec une grille métrique carrée', () => {
  const table = freshTable();
  assert.equal(table.grid.unit, 'm');
  assert.equal(table.grid.scale, 1);
  assert.equal(table.grid.visible, true);
});

test('une ancienne sauvegarde est normalisée sans perdre ses éléments', () => {
  const table = normalizeTable({ version: 1, grid: { size: 80 }, items: [{ id: 'a' }] });
  assert.equal(table.grid.size, 80);
  assert.equal(table.grid.unit, 'm');
  assert.equal(table.items[0].id, 'a');
});

test('le clipping reste optionnel', () => {
  assert.equal(snap(94, 64, false), 94);
  assert.equal(snap(94, 64, true), 64);
  const items = moveItem([{ id:'a', x:0, y:0 }], 'a', 98, 129, { size:64, snap:true });
  assert.deepEqual([items[0].x, items[0].y], [128, 128]);
});

test('l’outliner peut réordonner les éléments', () => {
  const items = [{id:'a'},{id:'b'},{id:'c'}];
  assert.deepEqual(reorderItem(items,'a','front').map(i=>i.id), ['b','c','a']);
  assert.deepEqual(reorderItem(items,'c','back').map(i=>i.id), ['c','a','b']);
});

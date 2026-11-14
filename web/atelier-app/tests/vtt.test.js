import test from 'node:test';
import assert from 'node:assert/strict';
import { freshTable, normalizeTable, moveItem, reorderItem, snap, snapPoint, screenToWorldPoint, worldToScreenPoint, worldToGrid, gridToWorld, translateGroup, itemsInRect, clampFloatingPosition } from '../src/vttState.js';

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
  const items = moveItem([{ id:'a', x:0, y:0 }], 'a', 98, 129, { size:64, snap:true, snapAnchor:'intersection' });
  assert.deepEqual([items[0].x, items[0].y], [128, 128]);
});

test('l’outliner peut réordonner les éléments', () => {
  const items = [{id:'a'},{id:'b'},{id:'c'}];
  assert.deepEqual(reorderItem(items,'a','front').map(i=>i.id), ['b','c','a']);
  assert.deepEqual(reorderItem(items,'c','back').map(i=>i.id), ['c','a','b']);
});

test('les coordonnées écran et monde restent réversibles avec pan et zoom', () => {
  const camera={x:37,y:-22,zoom:2.5},rect={left:100,top:50,width:900,height:600};
  const world=screenToWorldPoint(640,330,rect,camera);
  const screen=worldToScreenPoint(world.x,world.y,rect.width,rect.height,camera);
  assert.ok(Math.abs(screen.x-(640-rect.left))<1e-9);
  assert.ok(Math.abs(screen.y-(330-rect.top))<1e-9);
});

test('le snapping off, soft, strong, décalé et temporairement désactivé est prévisible', () => {
  const grid={size:64,originX:10,originY:6,snapSensitivity:.25,snapAnchor:'intersection'};
  assert.deepEqual(snapPoint({x:70,y:69},{...grid,snapMode:'off'}),{x:70,y:69,snapped:false});
  assert.deepEqual(snapPoint({x:70,y:69},{...grid,snapMode:'strong'}),{x:74,y:70,snapped:true});
  assert.equal(snapPoint({x:42,y:38},{...grid,snapMode:'soft'}).snapped,false);
  assert.equal(snapPoint({x:70,y:69},{...grid,snapMode:'soft'}).snapped,true);
  assert.equal(snapPoint({x:70,y:69},{...grid,snapMode:'strong'},{disabled:true}).snapped,false);
});

test('les centres, intersections et grilles tournées utilisent le même espace géométrique', () => {
  const centered={size:64,originX:0,originY:0,rotation:0,snapMode:'strong',snapAnchor:'center'};
  assert.deepEqual(snapPoint({x:14,y:18},centered),{x:32,y:32,snapped:true});
  const rotated={...centered,originX:10,originY:20,rotation:30};
  const world=gridToWorld({x:2.25,y:-1.5},rotated),roundTrip=worldToGrid(world,rotated);
  assert.ok(Math.abs(roundTrip.x-2.25)<1e-9&&Math.abs(roundTrip.y+1.5)<1e-9);
  const snapped=snapPoint(gridToWorld({x:1.47,y:2.53},rotated),rotated);
  const local=worldToGrid(snapped,rotated);
  assert.ok(Math.abs(local.x-1.5)<1e-9&&Math.abs(local.y-2.5)<1e-9);
});

test('les groupes conservent leurs écarts et les objets verrouillés restent hors sélection collective', () => {
  const items=[{id:'a',x:0,y:0,w:20,h:20},{id:'b',x:50,y:30,w:20,h:20},{id:'locked',x:10,y:10,w:20,h:20,locked:true}];
  const moved=translateGroup(items,{a:{x:0,y:0},b:{x:50,y:30}},15,-8);
  assert.deepEqual(moved.slice(0,2).map(({x,y})=>[x,y]),[[15,-8],[65,22]]);
  assert.deepEqual(itemsInRect(items,{left:-20,right:80,top:-20,bottom:60}).map(item=>item.id),['a','b']);
});

test('les menus contextuels restent entièrement dans le viewport', () => {
  assert.deepEqual(clampFloatingPosition(-30,590,240,60,800,600),{x:8,y:532});
  assert.deepEqual(clampFloatingPosition(700,-20,240,60,800,600),{x:552,y:8});
});

test('100 tokens peuvent être déplacés pendant 600 frames sans calcul long', () => {
  const items=Array.from({length:100},(_,i)=>({id:String(i),x:i*3,y:i*2,w:64,h:64}));
  const origins=Object.fromEntries(items.map(item=>[item.id,{x:item.x,y:item.y}]));
  const started=performance.now();let frame=items;
  for(let i=0;i<600;i++)frame=translateGroup(items,origins,i/3,i/5);
  const elapsed=performance.now()-started;
  assert.equal(frame.length,100);
  assert.ok(elapsed<250,`déplacement collectif trop lent: ${elapsed.toFixed(1)} ms`);
});

test('le snapping doux garde brièvement sa cible pour éviter les oscillations', () => {
  const grid={size:100,originX:0,originY:0,snapSensitivity:.2,snapMode:'soft'};
  const previous={x:100,y:100,snapped:true};
  assert.deepEqual(snapPoint({x:124,y:100},grid,{previous}),previous);
  assert.equal(snapPoint({x:140,y:100},grid,{previous}).snapped,false);
});

test('la migration conserve les anciennes préférences de snapping', () => {
  assert.equal(normalizeTable({version:1,grid:{snap:true},items:[]}).grid.snapMode,'strong');
  assert.equal(normalizeTable({version:1,grid:{snap:false},items:[]}).grid.snapMode,'off');
});

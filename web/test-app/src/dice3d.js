// Dice roll popup with deterministic Rapier physics, matching the official
// Owlbear dice plugin: every client simulates the same seeded throw. Flat (GM
// Classique) mode keeps pre-rolled CSS dice.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import RAPIER from '@dimforge/rapier3d-compat';
import { groupDiceByRoll, meshDefsFor, rollValueForGroup, SIDES_TO_TYPE, MAX_VISIBLE_DICE, visibleRollChip } from './vendor/diceRoll.js';
import { reportRollResult, DICE_POPOVER_ID } from './vendor/diceResult.js';
import OBR from '@owlbear-rodeo/sdk';
import { initLogging, logEvent, logError } from './vendor/appLog.js';

initLogging('dice');

// The popover ignores click-away (a roll must not be dismissed before it can be
// read): it closes by itself after 8 s, or through this ✕ which only appears
// once the dice have settled.
const CLOSE_BUTTON_AFTER_MS = 3000;
const closeButton = document.getElementById('dice-close');
if (closeButton && OBR.isAvailable) {
  setTimeout(() => {
    closeButton.hidden = false;
  }, CLOSE_BUTTON_AFTER_MS);
  closeButton.addEventListener('click', () => {
    OBR.popover
      .close(DICE_POPOVER_ID)
      .catch((err) => logEvent('warn', 'dice_popup_close_failed', { message: err?.message ?? String(err) }));
  });
}

const params = new URLSearchParams(location.search);
const label = params.get('label') || 'Lancer de dés';
const formula = params.get('formula') || '';
const playerName = params.get('playerName') || '';
const portrait = params.get('portrait') || '';
const portraitIsImage = params.get('portraitImage') === '1';
const totalParam = params.get('total');
const rollsParam = (params.get('rolls') || '').split(',').filter(Boolean);
const typesParam = (params.get('types') || '').split(',').filter(Number);
const error = params.get('error');
const color = params.get('color') || '#181818';
const stagedParam = params.get('staged') === '1';
const zoomCritParam = params.get('zoomCrit') === '1'; // crit camera punch-in allowed (attack/stat/skill rolls)
// Explicit crit threshold (Gobelin: dé − 1); absent = the die's max face
const critFromParam = parseInt(params.get('critFrom') || '', 10);
// « Brute » : the weapon cannot crit, so no chip glows and no crit zoom.
const noCritParam = params.get('noCrit') === '1';
const critAt = (sides) => (noCritParam ? Infinity : Number.isFinite(critFromParam) ? Math.min(critFromParam, sides) : sides);
// Avantage/désavantage racial d'un jet: 'high' | 'low' — total = meilleur/pire
// dé + modificateur, et le crit ne regarde que le dé conservé.
const keepParam = params.get('keep');
const keptIndex = (rolls) => {
  if (!keepParam || rolls.length < 2) return -1;
  let idx = 0;
  for (let i = 1; i < rolls.length; i++) {
    if (keepParam === 'low' ? rolls[i] < rolls[idx] : rolls[i] > rolls[idx]) idx = i;
  }
  return idx;
};
const rollTotal = (rolls) => {
  const idx = keptIndex(rolls);
  return (idx >= 0 ? rolls[idx] : rolls.reduce((a, b) => a + b, 0)) + modifierParam;
};
const rollCrit = (rolls, types) => {
  const idx = keptIndex(rolls);
  if (idx >= 0) return rolls[idx] >= critAt(types[idx] ?? 20);
  return rolls.some((r, i) => r >= critAt(types[i] ?? 20));
};
const rollFail = (rolls) => {
  const idx = keptIndex(rolls);
  return idx >= 0 ? rolls[idx] === 1 : rolls.some((r) => r === 1);
};
const isSelf = params.get('self') === '1';
const specParam = params.get('diceSpec'); // JSON [{count, sides}...]
const seedParam = params.get('seed');
const modifierParam = parseInt(params.get('modifier') || '0', 10) || 0;
const playerId = params.get('playerId') || '';
const rollId = params.get('rollId') || '';
let breakdownLines = [];
try {
  breakdownLines = JSON.parse(params.get('breakdown') || '[]');
} catch {
  breakdownLines = [];
}
if (breakdownLines.length) {
  const el = document.createElement('div');
  el.className = 'breakdown';
  breakdownLines.forEach((line, index) => {
    const row = document.createElement('div');
    // The last line is the final damage: highlighted so it reads first.
    row.className = index === breakdownLines.length - 1 ? 'breakdown-line breakdown-final' : 'breakdown-line';
    row.textContent = line;
    el.appendChild(row);
  });
  document.querySelector('.card').appendChild(el);
}

const tagsParam = params.get('tags') || '';
const tagsEl = document.getElementById('tags');
if (tagsParam && tagsEl) {
  for (const label of tagsParam.split(',').map((t) => t.trim()).filter(Boolean)) {
    const chip = document.createElement('span');
    chip.className = 'tag';
    chip.textContent = label;
    tagsEl.appendChild(chip);
  }
}
const plainLabel = () => params.get('plainLabel') || 'Jet';

document.getElementById('label').textContent = label;
const portraitEl = document.getElementById('portrait');
portraitEl.textContent = playerName.trim().charAt(0).toUpperCase() || '👤';
if (portrait) {
  if (portraitIsImage) {
    const img = document.createElement('img');
    img.src = portrait;
    img.alt = '';
    img.onerror = () => img.remove();
    portraitEl.appendChild(img);
  } else {
    portraitEl.textContent = portrait;
  }
}
const row = document.getElementById('dice-row');
const totalEl = document.getElementById('total');
const formulaEl = document.getElementById('formula');

function appendRollChip(value, sides, index, count, delay = 0) {
  const result = visibleRollChip(value, sides, index, count, critAt(sides));
  if (!result) return;
  const chip = document.createElement('div');
  if (result.more != null) {
    chip.className = 'die more';
    chip.textContent = `+${result.more}`;
  } else {
    chip.className = result.crit ? 'die crit' : result.fail ? 'die fail' : 'die';
    chip.textContent = String(result.value);
  }
  if (delay) chip.style.animationDelay = `${delay}s`;
  const more = row.querySelector('.more');
  if (more && result.more == null) row.insertBefore(chip, more);
  else row.appendChild(chip);
}

// official Owlbear dice plugin collider hulls (raw GLB units)
const COLLIDER_VERTICES = {
  d4: [0.0, -0.635828, -1.269768, 0.0, 1.159624, 0.0, 1.099651, -0.635829, 0.634884, -1.099651, -0.635829, 0.634884],
  d6: [-0.8, -0.8, 0.8, -0.8, 0.8, 0.8, -0.8, -0.8, -0.8, -0.8, 0.8, -0.8, 0.8, -0.8, 0.8, 0.8, 0.8, 0.8, 0.8, -0.8, -0.8, 0.8, 0.8, -0.8],
  d10: [0.0, -1.172751, 0.0, 0.0, 1.172751, 0.0, 1.122302, -0.123811, 0.364658, 0.693621, 0.123811, 0.954687, 0.0, -0.123811, 1.180058, 0.69362, -0.123811, -0.954687, 1.122302, 0.123811, -0.364658, 0.0, 0.123811, -1.180058, -0.693621, -0.123811, -0.954687, -1.122301, 0.123811, 0.364658, -1.122301, 0.123811, -0.364658, -0.693621, 0.12381, 0.954687],
  d20: [-1.355243, -0.262864, 0.0, -0.415876, -1.09821, 0.725756, -0.678737, 0.257012, 1.174309, -0.841197, 1.094606, 0.0, -0.678737, 0.257012, -1.174309, -0.415876, -1.09821, -0.725756, 0.678737, -0.257012, 1.174309, 0.415876, 1.09821, 0.725756, 0.415876, 1.09821, -0.725756, 0.678737, -0.257012, -1.174309, 0.841197, -1.094606, 0.0, 1.355243, 0.262864, 0.0]
};
COLLIDER_VERTICES.d8 = COLLIDER_VERTICES.d10;
COLLIDER_VERTICES.d12 = COLLIDER_VERTICES.d20;
COLLIDER_VERTICES.d100 = COLLIDER_VERTICES.d10;

const critPre = rollsParam.some((r, i) => parseInt(r, 10) >= critAt(parseInt(typesParam[i], 10)));
const failPre = rollsParam.some((r) => parseInt(r, 10) === 1);

if (error) {
  formulaEl.textContent = formula;
  totalEl.style.display = 'none';
  const el = document.createElement('div');
  el.className = 'error';
  el.textContent = 'Formule invalide : ' + error;
  row.replaceWith(el);
} else if (rollsParam.length && rollsParam.length === typesParam.length) {
  showPreRolled();
} else {
  let spec = null;
  try {
    spec = JSON.parse(specParam || 'null');
  } catch {
    spec = null;
  }
  const playable = Array.isArray(spec) && spec.length && spec.every((t) => SIDES_TO_TYPE[t.sides]);
  if (!playable) {
    fallbackFromSpec(spec, modifierParam);
  } else {
    formulaEl.textContent = formula;
    startSim(spec, parseInt(seedParam, 10), modifierParam).catch((err) => {
      logError('dice_sim_failed', err);
      fallbackFromSpec(spec, modifierParam);
    });
  }
}

function showPreRolled() {
  formulaEl.textContent = formula;
  rollsParam.forEach((r, i) => appendRollChip(r, typesParam[i], i, rollsParam.length, i * 0.08));
  totalEl.style.animationDelay = `${0.45 + Math.min(rollsParam.length, MAX_VISIBLE_DICE + 1) * 0.08}s`;
  if (critPre) totalEl.classList.add('crit');
  else if (failPre) totalEl.classList.add('fail');
  totalEl.textContent = totalParam != null && totalParam !== '' ? totalParam : '—';
  if(isSelf)reportRollResult({playerId,rollId,label:plainLabel(),formula,rolls:rollsParam.map(Number),diceTypes:typesParam.map(Number),total:Number(totalParam),staged:stagedParam});
}

// Fallback: unusable spec or crashed sim → random values from the spec,
// displayed as CSS dice and still reported so the log stays consistent.
function fallbackFromSpec(spec, modifier) {
  document.body.dataset.renderer = 'fallback';
  const notice=document.createElement('p');notice.className='fallback-notice';notice.textContent='3D indisponible sur ce navigateur — résultat calculé localement.';document.querySelector('.card').append(notice);
  if (!spec) {
    totalEl.textContent = '—';
    return;
  }
  const rolls = [];
  const diceTypes = [];
  const rng = mulberry32(Number(seedParam) || 0);
  for (const term of spec) {
    for (let i = 0; i < term.count; i++) {
      rolls.push(Math.floor(rng() * term.sides) + 1);
      diceTypes.push(term.sides);
    }
  }
  const total = rollTotal(rolls);
  if (isSelf) reportRollResult({ playerId, rollId, label: plainLabel(), formula, rolls, diceTypes, staged: stagedParam, total });
  const crit = rollCrit(rolls, diceTypes);
  const fail = rollFail(rolls);
  rolls.forEach((r, i) => appendRollChip(r, diceTypes[i], i, rolls.length, i * 0.08));
  totalEl.style.animationDelay = `${0.45 + Math.min(rolls.length, MAX_VISIBLE_DICE + 1) * 0.08}s`;
  if (crit) totalEl.classList.add('crit');
  else if (fail) totalEl.classList.add('fail');
  totalEl.textContent = String(total);
}

// ─── Seeded RNG (deterministic rotations across the roller's throws) ─────
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function randomRotation(rng) {
  // uniform random quaternion (adapted from the official plugin)
  let x, y, z, u, v, w, s;
  do {
    x = rng() * 2 - 1;
    y = rng() * 2 - 1;
    z = x * x + y * y;
  } while (z > 1);
  do {
    u = rng() * 2 - 1;
    v = rng() * 2 - 1;
    w = u * u + v * v;
  } while (w > 1);
  s = Math.sqrt((1 - z) / w);
  return { x, y, z: s * u, w: s * v };
}

const THROW_MIN_Y = 2.6;
const THROW_MAX_Y = 3.2;
const MIN_LAUNCH_VELOCITY = 3;
const MAX_LAUNCH_VELOCITY = 6;
const MIN_ANGULAR_VELOCITY = 4;
const MAX_ANGULAR_VELOCITY = 9;
const MIN_ROLL_FINISHED_SPEED = 0.015;
const SLOW_FRAMES_REQUIRED = 8;
const HARD_STOP_MS = 9500; // absolute deadline: read the best face
const SNAP_DURATION_MS = 600; // slower face snap — readable toppling onto the final face

// ponytail: one synthesized clack avoids audio assets; use recordings if it sounds too synthetic.
function createClackSound() {
  if (!window.AudioContext) return () => {};
  let context;
  try {
    context = new AudioContext();
  } catch {
    return () => {};
  }
  const buffer = context.createBuffer(1, context.sampleRate * 0.05, context.sampleRate);
  const noise = buffer.getChannelData(0);
  for (let i = 0; i < noise.length; i++) noise[i] = Math.random() * 2 - 1;
  // autoplay policy: the roll gesture happens in ANOTHER frame (the sheet
  // popover), never inside this popup — hook pointerdown on every reachable
  // window so the context resumes on the user's click; self-removes once
  // running
  const hooked = [];
  const resume = () => context.state === 'suspended' && context.resume().catch(() => {});
  const hookResume = () => {
    resume();
    if (context.state === 'running') {
      for (const w of hooked) { try { w.removeEventListener('pointerdown', hookResume); } catch {} }
    }
  };
  for (const w of [window, window.parent, window.top]) {
    try { w.addEventListener('pointerdown', hookResume); hooked.push(w); } catch { /* cross-origin */ }
  }
  return (speed) => {
    resume();
    if (context.state !== 'running') return;
    const source = context.createBufferSource();
    const filter = context.createBiquadFilter();
    const gain = context.createGain();
    const now = context.currentTime;
    source.buffer = buffer;
    filter.type = 'bandpass';
    filter.frequency.value = 1400 + Math.min(speed * 250, 1800);
    gain.gain.setValueAtTime(0.001, now);
    gain.gain.exponentialRampToValueAtTime(0.18, now + 0.003);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
    source.connect(filter).connect(gain).connect(context.destination);
    source.start(now);
    source.stop(now + 0.05);
  };
}

// ─── Visual mesh layout: one def per mesh; a d100 = percentile + ones ────

// Jittered-grid spawn positions: dice can never spawn interpenetrating
// (grid spacing ≥ die size by construction); deterministic draw order.
function spawnGrid(rng, count, cols, spacing) {
  const rows = Math.ceil(count / cols);
  const positions = [];
  for (let row = 0; row < rows; row++) {
    const inRow = Math.min(count - row * cols, cols);
    for (let col = 0; col < inRow; col++) {
      positions.push({
        x: (col - (inRow - 1) / 2) * spacing + (rng() - 0.5) * 0.2,
        y: THROW_MIN_Y + rng() * (THROW_MAX_Y - THROW_MIN_Y),
        z: (row - (rows - 1) / 2) * spacing + (rng() - 0.5) * 0.2
      });
    }
  }
  return positions;
}

// printed face numbers (canvas textures at the locator anchors)
const numberTextureCache = new Map();

function numberTexture(text) {
  if (numberTextureCache.has(text)) return numberTextureCache.get(text);
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');
  ctx.font = `bold ${text.length > 1 ? 248 : 312}px system-ui, Arial, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineWidth = 24;
  ctx.strokeStyle = 'rgba(12,12,12,0.95)';
  ctx.strokeText(text, 256, 272);
  ctx.fillStyle = '#ffffff';
  ctx.fillText(text, 256, 272);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  numberTextureCache.set(text, texture);
  return texture;
}

// per-type face geometry from the loaded GLB (locator world directions)
function typeGeometry(gltfScene) {
  gltfScene.updateMatrixWorld(true);
  const dieNode = gltfScene.children[0];
  if (!dieNode) return null;
  const bbox = new THREE.Box3().setFromObject(gltfScene);
  const size = bbox.getSize(new THREE.Vector3());
  const faces = new Map();
  for (const locator of dieNode.children) {
    const match = locator.name.match(/_locator_(.+)$/);
    if (!match) continue;
    const world = new THREE.Vector3();
    locator.getWorldPosition(world);
    faces.set(match[1], { dir: world.clone().normalize(), dist: world.length() });
  }
  return { radius: Math.max(size.x, size.y, size.z) / 2, faces };
}

function addFaceNumbers(dieGroup, geom) {
  const geometry = new THREE.PlaneGeometry(0.85, 0.85);
  for (const [num, { dir, dist }] of geom.faces) {
    const text = num.length === 1 ? num : num.length === 2 ? num : num;
    const plane = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({
      map: numberTexture(text),
      transparent: true,
      depthWrite: false
    }));
    plane.position.copy(dir).multiplyScalar(dist * 1.02 + 0.04);
    plane.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
    dieGroup.add(plane);
  }
}

// shared stage: top-down tray view
function buildStage(canvas, width, height, materialColor) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1, 3));
  renderer.setSize(width, height, true);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
  camera.up.set(0, 0, -1);
  camera.position.set(0, 8.2, 0.01);
  camera.lookAt(0, 0, 0);
  scene.add(new THREE.AmbientLight(0xffffff, 1.5));
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(2.5, 8, 3);
  scene.add(key);
  return { renderer, scene, camera };
}

// visible world rectangle on the tray plane (y=0) for a top-down camera
function visibleRect(width, height) {
  const cameraHeight = 8.2;
  const halfH = cameraHeight * Math.tan(THREE.MathUtils.degToRad(40 / 2));
  const halfW = halfH * (width / height);
  return { halfW, halfH };
}

// tray floor covering the full canvas + a visible frame AT the wall line
function buildTray(scene, halfW, halfH) {
  const tray = new THREE.Mesh(
    new THREE.PlaneGeometry(halfW * 2, halfH * 2),
    new THREE.MeshStandardMaterial({ color: '#f1f2ed', roughness: 0.9 })
  );
  tray.rotation.x = -Math.PI / 2;
  tray.position.y = -0.8;
  scene.add(tray);
  // chunky visible border (thin boxes) exactly on the wall inner faces
  const borderMat = new THREE.MeshStandardMaterial({ color: '#b6c1ad', roughness: 0.4, metalness: 0.2 });
  const t = 0.08, h = 0.16;
  for (const [w, d, x, z] of [
    [halfW * 2 + t, t, 0, halfH],
    [halfW * 2 + t, t, 0, -halfH],
    [t, halfH * 2 + t, halfW, 0],
    [t, halfH * 2 + t, -halfW, 0]
  ]) {
    const bar = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), borderMat);
    bar.position.set(x, -0.78, z);
    scene.add(bar);
  }
}

function makeHostCanvas(hostHeight) {
  const host = document.createElement('div');
  host.className='dice-host';
  host.style.cssText = `width:100%;min-height:64px;flex:1;display:flex;justify-content:center;overflow:hidden`;
  row.parentNode.insertBefore(host, row);
  const canvas = document.createElement('canvas');
  host.appendChild(canvas);
  const width = host.clientWidth || 420;
  return { host, canvas, width, height: host.clientHeight||hostHeight };
}

// ─── Every client's seeded Rapier simulation ────────────────────────────
async function startSim(spec, seed, modifier) {
  const meshDefs = meshDefsFor(spec);
  const { host, canvas, width, height } = makeHostCanvas(180);
  let stage;
  try {
    stage = buildStage(canvas, width, height, color);
  } catch (err) {
    logEvent('warn', 'dice_webgl_unavailable', { message: err?.message ?? String(err) });
    host.remove();
    fallbackFromSpec(spec, modifier);
    return;
  }
  const { renderer, scene, camera } = stage;
  const resizeObserver=new ResizeObserver(()=>{const w=host.clientWidth,h=host.clientHeight;if(w>0&&h>0){renderer.setSize(w,h,true);camera.aspect=w/h;camera.updateProjectionMatrix();}});
  resizeObserver.observe(host);

  try {
    await RAPIER.init();
  } catch (err) {
    logError('dice_rapier_init_failed', err);
    host.remove();
    fallbackFromSpec(spec, modifier);
    return;
  }

  const world = new RAPIER.World({ x: 0, y: -14, z: 0 });
  world.timestep = 1 / 60;
  const T = 50; // huge wall half-extents so nothing teleports through
  const floorBody = world.createRigidBody(RAPIER.RigidBodyDesc.fixed());
  world.createCollider(RAPIER.ColliderDesc.cuboid(T, T, T).setTranslation(0, -0.8 - T, 0), floorBody);
  // Walls rise above the floor so airborne dice cannot escape the visible tray.
  const rect = visibleRect(width, height);
  buildTray(scene, rect.halfW, rect.halfH);
  const n0 = meshDefs.length;
  const cols0 = Math.min(n0, Math.ceil(Math.sqrt(n0)));
  const rows0 = Math.ceil(n0 / cols0);
  // die size also constrained by the visible depth (rows stack along z)
  const diam0 = Math.min(n0<=2?3.2:2.3, 5.8 / cols0, (rect.halfH * 2 - 0.5) / (1.2 * rows0 + 0.5));
  const wallX = Math.max(1, rect.halfW - (diam0 / 2 + 0.15));
  const wallZ = Math.max(1, rect.halfH - (diam0 / 2 + 0.15));
  const wallBody = world.createRigidBody(RAPIER.RigidBodyDesc.fixed());
  const wallHeight = 6;
  const wallThickness = 0.16;
  const wallY = -0.8 + wallHeight / 2;
  for (const [shape, x, z] of [
    [RAPIER.ColliderDesc.cuboid(wallX + wallThickness, wallHeight / 2, wallThickness / 2), 0, wallZ + wallThickness / 2],
    [RAPIER.ColliderDesc.cuboid(wallX + wallThickness, wallHeight / 2, wallThickness / 2), 0, -wallZ - wallThickness / 2],
    [RAPIER.ColliderDesc.cuboid(wallThickness / 2, wallHeight / 2, wallZ + wallThickness), wallX + wallThickness / 2, 0],
    [RAPIER.ColliderDesc.cuboid(wallThickness / 2, wallHeight / 2, wallZ + wallThickness), -wallX - wallThickness / 2, 0]
  ]) {
    world.createCollider(shape.setTranslation(x, wallY, z).setFriction(0.12).setRestitution(0.45), wallBody);
  }

  const loader = new GLTFLoader();
  const needTypes = [...new Set(meshDefs.map((m) => m.type))];
  const loaded = await Promise.all(
    needTypes.map(
      (t) =>
        new Promise((resolve) => {
          loader.load(`/test/dice/${t}.glb`, (gltf) => resolve([t, gltf.scene]), undefined, () => resolve([t, null]));
        })
    )
  );
  const byType = Object.fromEntries(loaded);
  if (loaded.some(([, s]) => !s)) {
    host.remove();
    fallbackFromSpec(spec, modifier);
    return;
  }
  const eventQueue = new RAPIER.EventQueue(true);
  document.body.dataset.renderer = 'three-rapier';
  const playClack = createClackSound();
  let lastClack = 0;
  const geometries = new Map(needTypes.map((t) => [t, typeGeometry(byType[t])]));

  const rng = mulberry32(seed);
  const n = meshDefs.length;
  const cols = cols0;
  const rows = rows0;
  const renderedDiameter = diam0;
  const spacing = renderedDiameter * 1.2;
  const spawnPositions = spawnGrid(rng, n, cols, spacing);
  const throws = meshDefs.map(() => ({
    rotation: randomRotation(rng),
    angularVelocity: {
      x: MIN_ANGULAR_VELOCITY + rng() * (MAX_ANGULAR_VELOCITY - MIN_ANGULAR_VELOCITY),
      y: MIN_ANGULAR_VELOCITY + rng() * (MAX_ANGULAR_VELOCITY - MIN_ANGULAR_VELOCITY),
      z: MIN_ANGULAR_VELOCITY + rng() * (MAX_ANGULAR_VELOCITY - MIN_ANGULAR_VELOCITY)
    }
  }));
  const up = new THREE.Vector3(0, 1, 0);

  const dice = meshDefs.map((def, i) => {
    const geom = geometries.get(def.type) ?? typeGeometry(byType[def.type]);
    const scale = Math.min(n0<=2?0.9:0.62, renderedDiameter / (2 * geom.radius));
    const die = byType[def.type].clone(true);
    die.scale.setScalar(scale);
    const material = new THREE.MeshPhysicalMaterial({
      color,
      metalness: 0.02,
      roughness: 0.42,
      clearcoat: 0.2,
      clearcoatRoughness: 0.25
    });
    die.traverse((o) => {
      if (o.isMesh) o.material = material;
    });
    addFaceNumbers(die, geom);
    scene.add(die);

    // spawn on the jittered grid (no interpenetration by construction) and
    // launch toward the tray center (official throwing motion)
    const spawn = spawnPositions[i];
    const toCenter = Math.hypot(spawn.x, spawn.z) || 1;
    const speed = MIN_LAUNCH_VELOCITY + rng() * (MAX_LAUNCH_VELOCITY - MIN_LAUNCH_VELOCITY);
    const body = world.createRigidBody(
      RAPIER.RigidBodyDesc.dynamic()
        .setTranslation(spawn.x, spawn.y, spawn.z)
        .setRotation(throws[i].rotation)
        .setLinvel((-spawn.x / toCenter) * speed, 0, (-spawn.z / toCenter) * speed)
        .setAngvel(throws[i].angularVelocity) // desc API takes a vector object
        .setGravityScale(1.6)
        .setCanSleep(false) // rapier can freeze an unstable edge-balance — never let it
    );
    const verts = new Float32Array(COLLIDER_VERTICES[def.type].map((v) => v * scale));
    world.createCollider(
      RAPIER.ColliderDesc.convexHull(verts)
        .setFriction(0.12)
        .setRestitution(0.45)
        .setDensity(1)
        .setActiveEvents(RAPIER.ActiveEvents.COLLISION_EVENTS),
      body
    );
    return { def, geom, die, material, body, glow: null, chipDone: false, slowFrames: 0, snap: null };
  });

  const rollGroups = groupDiceByRoll(dice);
  let critZoom = null; // { pos, from, start } — camera punch-in on a crit face
  const diceByBody = new Map(dice.map((d) => [d.body.handle, d]));
  const settled = new Set();
  let pendingMs = 0;
  let lastTick = performance.now();
  let reported = false;
  const startMs = lastTick;
  const STEP_MS = 1000 / 60;

  function readFace(die) {
    let bestDot = -Infinity;
    let best = null;
    for (const [num, { dir }] of die.geom.faces) {
      const world = dir.clone().applyQuaternion(die.die.quaternion);
      const dot = world.dot(up);
      if (dot > bestDot) {
        bestDot = dot;
        best = num;
      }
    }
    return best;
  }

  // how clearly the top locator faces up (1 = face perfectly flat up)
  function readFaceDot(die) {
    let bestDot = -Infinity;
    for (const [, { dir }] of die.geom.faces) {
      const dot = dir.clone().applyQuaternion(die.die.quaternion).dot(up);
      if (dot > bestDot) bestDot = dot;
    }
    return bestDot;
  }

  function lockDie(d) {
    d.body.setEnabledRotations(false, false, false);
    d.body.setEnabledTranslations(false, false, false);
    d.body.setAngvel({ x: 0, y: 0, z: 0 }, false);
    d.body.setLinvel({ x: 0, y: 0, z: 0 }, false);
    settled.add(d);
  }

  function playCollision(first, second, started) {
    // ponytail: global cooldown caps dense pools; use per-die cooldowns if too sparse.
    if (!started || performance.now() - lastClack < 85) return;
    for (const handle of [first, second]) {
      const body = world.getCollider(handle).parent();
      const die = body && diceByBody.get(body.handle);
      if (!die) continue;
      const velocity = die.body.linvel();
      playClack(Math.hypot(velocity.x, velocity.y, velocity.z));
      lastClack = performance.now();
      break;
    }
  }

  function snapDie(d, now) {
    const face = d.geom.faces.get(readFace(d));
    if (!face) return lockDie(d);
    // drama: a die snapping onto its max face zooms the camera onto it
    if (!critZoom && zoomCritParam && rollValueForGroup(rollGroups[d.def.rollIndex], readFace) >= critAt(d.def.sides)) {
      critZoom = { pos: d.die.position.clone(), from: camera.position.clone(), start: now };
    }
    const from = d.die.quaternion.clone();
    const facing = face.dir.clone().applyQuaternion(from).normalize();
    const correction = new THREE.Quaternion().setFromUnitVectors(facing, up);
    d.snap = { from, to: correction.multiply(from), start: now };
    d.body.setEnabledRotations(false, false, false);
    d.body.setEnabledTranslations(false, false, false);
    d.body.setAngvel({ x: 0, y: 0, z: 0 }, false);
    d.body.setLinvel({ x: 0, y: 0, z: 0 }, false);
  }

  function animate() {
    // fixed timestep accumulator driven by REAL elapsed time: the same
    // simulated duration passes regardless of the display's frame rate
    const now = performance.now();
    const elapsed = Math.min(now - lastTick, 100);
    lastTick = now;
    if (!reported) {
      pendingMs += elapsed;
      while (pendingMs >= STEP_MS) {
        world.step(eventQueue);
        eventQueue.drainCollisionEvents(playCollision);
        pendingMs -= STEP_MS;
      }
    }
    const wallNow = now - startMs;
    for (const d of dice) {
      if (d.snap) {
        const t = d.body.translation();
        d.die.position.set(t.x, t.y, t.z);
        const progress = Math.min(1, (now - d.snap.start) / SNAP_DURATION_MS);
        const ease = 1 - Math.pow(1 - progress, 3);
        d.die.quaternion.slerpQuaternions(d.snap.from, d.snap.to, ease);
        if (progress >= 1) {
          d.body.setRotation(d.snap.to, false);
          d.snap = null;
          lockDie(d);
        }
        continue;
      }
      const t = d.body.translation();
      const r = d.body.rotation();
      d.die.position.set(t.x, t.y, t.z);
      d.die.quaternion.set(r.x, r.y, r.z, r.w);
      if (settled.has(d) || d.chipDone) continue;
      const lin = d.body.linvel();
      const ang = d.body.angvel();
      const speed = Math.hypot(lin.x, lin.y, lin.z) + Math.hypot(ang.x, ang.y, ang.z);
      if (speed < MIN_ROLL_FINISHED_SPEED) d.slowFrames += 1;
      else d.slowFrames = 0;
      // a die counts as settled ONLY once a face sits clearly up — a die
      // balanced on a tip/edge is snapped onto its nearest face (reads as
      // toppling over) instead of being read
      const faceUp = readFaceDot(d) >= 0.92;
      if (d.slowFrames >= SLOW_FRAMES_REQUIRED && faceUp) {
        lockDie(d);
      } else if (d.slowFrames >= SLOW_FRAMES_REQUIRED || wallNow >= HARD_STOP_MS) {
        snapDie(d, now); // ease a tip/edge balance onto its nearest face
      }
    }
    // per logical roll: all its meshes settled → value chip
    for (const d of dice) {
      if (d.chipDone || !settled.has(d)) continue;
      const group = rollGroups[d.def.rollIndex];
      if (!group.every((x) => settled.has(x))) continue;
      const value = rollValueForGroup(group, readFace);
      for (const die of group) {
        die.rollValue = value;
        die.chipDone = true;
      }
      const crit = value >= critAt(d.def.sides);
      const fail = value === 1;
      appendRollChip(value, d.def.sides, d.def.rollIndex, rollGroups.length);
      if (crit) {
        d.glow = '#fbbf24';
        // covers cleanly-settled crits too — snapDie only fires for dice that
        // were tip/edge-balanced, so a die landing flat on its max face never
        // passed through it
        if (!critZoom && zoomCritParam) {
          critZoom = { pos: group[0].die.position.clone(), from: camera.position.clone(), start: now };
        }
      } else if (fail) d.glow = '#dc2626';
    }
    if (!reported && dice.every((d) => d.chipDone)) {
      reported = true;
      const rolls = rollGroups.map((group) => group[0].rollValue ?? 1);
      const diceTypes = rollGroups.map((group) => group[0].def.sides);
      const crit = rollCrit(rolls, diceTypes);
      const fail = rollFail(rolls);
      if (crit) totalEl.classList.add('crit');
      else if (fail) totalEl.classList.add('fail');
      const total = rollTotal(rolls);
      totalEl.textContent = String(total);
      if (isSelf) reportRollResult({ playerId, rollId, label: plainLabel(), formula, rolls, diceTypes, staged: stagedParam, total });
      eventQueue.free();
    }
    for (const d of dice) {
      if (d.glow && d.chipDone) {
        const pulse = 0.55 + 0.45 * Math.sin(performance.now() / 1000 * 7);
        d.material.emissive.set(d.glow);
        d.material.emissiveIntensity = pulse * 1.5;
      }
    }
    // camera punch-in onto the crit die, eased over the snap, then held
    if (critZoom) {
      const p = Math.min(1, (now - critZoom.start) / SNAP_DURATION_MS);
      const ease = 1 - Math.pow(1 - p, 3);
      const target = critZoom.pos.clone().add(new THREE.Vector3(0, 3.2, 0.01));
      camera.position.lerpVectors(critZoom.from, target, ease);
      camera.lookAt(critZoom.pos);
    }
    // Moving between monitors or changing browser zoom can change DPR without
    // changing the iframe's CSS dimensions, so ResizeObserver alone is insufficient.
    const pixelRatio=Math.min(window.devicePixelRatio||1,3);
    if(renderer.getPixelRatio()!==pixelRatio)renderer.setPixelRatio(pixelRatio);
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }
  animate();
}

export const IMAGE_TYPES = [
  ['MAP', 'Cartes'], ['PROP', 'Accessoires'], ['MOUNT', 'Montures'],
  ['DRAWING', 'Dessins'], ['CHARACTER', 'Personnages'], ['NOTE', 'Notes']
];

export const IMPORT_TYPES = IMAGE_TYPES.filter(([key]) => key !== 'DRAWING');

export function freshTable() {
  return {
    version: 1,
    grid: { visible: true, size: 64, scale: 1, unit: 'm', color: '#798274', opacity: .28, snap: false, snapMode: 'off', snapSensitivity: .28, snapAnchor: 'center', originX: 0, originY: 0, rotation: 0 },
    camera: { x: 0, y: 0, zoom: 1 },
    items: [],
    updatedAt: Date.now()
  };
}

export function normalizeTable(value) {
  const base = freshTable();
  if (!value || value.version !== 1) return base;
  return {
    ...base, ...value,
    grid: { ...base.grid, ...(value.grid || {}), snapMode: value.grid?.snapMode || (value.grid?.snap ? 'strong' : 'off') },
    camera: { ...base.camera, ...(value.camera || {}) },
    items: Array.isArray(value.items) ? value.items.map(item => item.type === 'ATTACHMENT' ? { ...item, type: 'NOTE' } : item) : []
  };
}

export function snap(value, size, enabled) {
  return enabled ? Math.round(value / size) * size : value;
}

export function screenToWorldPoint(clientX, clientY, rect, camera) {
  return {
    x: (clientX - rect.left - rect.width / 2) / camera.zoom - camera.x,
    y: (clientY - rect.top - rect.height / 2) / camera.zoom - camera.y
  };
}

export function worldToScreenPoint(x, y, width, height, camera) {
  return {
    x: width / 2 + (x + camera.x) * camera.zoom,
    y: height / 2 + (y + camera.y) * camera.zoom
  };
}

export function worldToGrid(point, grid) {
  const size = Math.max(1, Number(grid.size) || 64);
  const originX = Number(grid.originX) || 0, originY = Number(grid.originY) || 0;
  const angle = -(Number(grid.rotation) || 0) * Math.PI / 180;
  const dx = point.x - originX, dy = point.y - originY;
  return {
    x: (dx * Math.cos(angle) - dy * Math.sin(angle)) / size,
    y: (dx * Math.sin(angle) + dy * Math.cos(angle)) / size
  };
}

export function gridToWorld(point, grid) {
  const size = Math.max(1, Number(grid.size) || 64);
  const originX = Number(grid.originX) || 0, originY = Number(grid.originY) || 0;
  const angle = (Number(grid.rotation) || 0) * Math.PI / 180;
  const x = point.x * size, y = point.y * size;
  return {
    x: originX + x * Math.cos(angle) - y * Math.sin(angle),
    y: originY + x * Math.sin(angle) + y * Math.cos(angle)
  };
}

export function snapPoint(point, grid, options = {}) {
  const mode = options.disabled ? 'off' : (grid.snapMode || (grid.snap ? 'strong' : 'off'));
  if (mode === 'off') return { ...point, snapped: false };
  const size = Math.max(1, Number(grid.size) || 64), local = worldToGrid(point, grid);
  const offset = grid.snapAnchor === 'intersection' ? 0 : .5;
  const target = gridToWorld({x:Math.round(local.x-offset)+offset,y:Math.round(local.y-offset)+offset},grid);
  const distance = Math.hypot(target.x - point.x, target.y - point.y);
  const threshold = size * Math.max(.05, Math.min(.5, Number(grid.snapSensitivity) || .28));
  if (mode === 'soft' && options.previous?.snapped) {
    const previousDistance = Math.hypot(options.previous.x - point.x, options.previous.y - point.y);
    if (previousDistance <= threshold * 1.35) return { ...options.previous, snapped: true };
  }
  if (mode === 'soft' && distance > threshold) return { ...point, snapped: false };
  return { ...target, snapped: true };
}

export function translateGroup(items, origins, dx, dy) {
  return items.map(item => origins[item.id] ? {...item,x:origins[item.id].x+dx,y:origins[item.id].y+dy} : item);
}

export function itemsInRect(items, rect) {
  return items.filter(item => !item.hidden && !item.locked && item.x+item.w/2>=rect.left && item.x-item.w/2<=rect.right && item.y+item.h/2>=rect.top && item.y-item.h/2<=rect.bottom);
}

export function clampFloatingPosition(x, y, width, height, viewportWidth, viewportHeight, margin=8) {
  return {x:Math.max(margin,Math.min(viewportWidth-width-margin,x)),y:Math.max(margin,Math.min(viewportHeight-height-margin,y))};
}

export function moveItem(items, id, x, y, grid) {
  const point = snapPoint({ x, y }, grid);
  return items.map(item => item.id === id ? {
    ...item,
    x: point.x, y: point.y
  } : item);
}

export function reorderItem(items, id, direction) {
  const next = [...items], index = next.findIndex(item => item.id === id);
  if (index < 0) return next;
  const target = direction === 'front' ? next.length - 1 : direction === 'back' ? 0 : Math.max(0, Math.min(next.length - 1, index + direction));
  const [item] = next.splice(index, 1); next.splice(target, 0, item); return next;
}

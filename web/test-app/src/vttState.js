export const IMAGE_TYPES = [
  ['MAP', 'Cartes'], ['PROP', 'Accessoires'], ['MOUNT', 'Montures'],
  ['DRAWING', 'Dessins'], ['CHARACTER', 'Personnages'], ['NOTE', 'Notes']
];

export const IMPORT_TYPES = IMAGE_TYPES.filter(([key]) => key !== 'DRAWING');

export function freshTable() {
  return {
    version: 1,
    grid: { visible: true, size: 64, scale: 1, unit: 'm', color: '#798274', opacity: .28, snap: false },
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
    grid: { ...base.grid, ...(value.grid || {}) },
    camera: { ...base.camera, ...(value.camera || {}) },
    items: Array.isArray(value.items) ? value.items.map(item => item.type === 'ATTACHMENT' ? { ...item, type: 'NOTE' } : item) : []
  };
}

export function snap(value, size, enabled) {
  return enabled ? Math.round(value / size) * size : value;
}

export function moveItem(items, id, x, y, grid) {
  return items.map(item => item.id === id ? {
    ...item,
    x: snap(x, grid.size, grid.snap), y: snap(y, grid.size, grid.snap)
  } : item);
}

export function reorderItem(items, id, direction) {
  const next = [...items], index = next.findIndex(item => item.id === id);
  if (index < 0) return next;
  const target = direction === 'front' ? next.length - 1 : direction === 'back' ? 0 : Math.max(0, Math.min(next.length - 1, index + direction));
  const [item] = next.splice(index, 1); next.splice(target, 0, item); return next;
}

<script>
  /**
   * Multi-select dropdown for a weapon's property tags.
   *
   * The trigger shows the selected labels (or a placeholder); the panel is a
   * checkbox list where hovering a row explains the rule. A native
   * `<select multiple>` was rejected: one stray click resets the whole
   * selection, which silently drops tags from a weapon.
   *
   * The panel is `position: fixed` — the weapon forms live inside an
   * `overflow-y-auto` block, which would clip an absolutely positioned panel.
   */
  import { PROPERTY_TAGS } from './characterSheet.js';
  import { tooltip } from './tooltip.js';

  /**
   * @type {{
   *   tags?: string[],
   *   onChange?: (tags: string[]) => void,
   *   placeholder?: string,
   *   disabled?: boolean
   * }}
   */
  let { tags = [], onChange = () => {}, placeholder = '— Aucune —', disabled = false } = $props();

  let open = $state(false);
  /** @type {HTMLElement|null} */
  let triggerEl = $state(null);
  let panel = $state({ left: 0, top: 0, width: 0, maxHeight: 240 });

  const selected = $derived(PROPERTY_TAGS.filter((t) => tags.includes(t.id)));
  const summary = $derived(selected.length ? selected.map((t) => t.label).join(', ') : placeholder);

  function placePanel() {
    if (!triggerEl) return;
    const rect = triggerEl.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom - 8;
    const spaceAbove = rect.top - 8;
    // Open upwards when the form's field is near the bottom of the window.
    const openUp = spaceBelow < 180 && spaceAbove > spaceBelow;
    const maxHeight = Math.min(280, Math.max(120, openUp ? spaceAbove : spaceBelow));
    panel = {
      left: rect.left,
      top: openUp ? rect.top - maxHeight - 4 : rect.bottom + 4,
      width: rect.width,
      maxHeight,
    };
  }

  function togglePanel() {
    if (disabled) return;
    if (open) {
      open = false;
      return;
    }
    placePanel();
    open = true;
  }

  function toggleTag(id) {
    onChange(tags.includes(id) ? tags.filter((t) => t !== id) : [...tags, id]);
  }
</script>

<div class="relative">
  <button
    type="button"
    bind:this={triggerEl}
    onclick={togglePanel}
    {disabled}
    aria-haspopup="listbox"
    aria-expanded={open}
    title={selected.length ? selected.map((t) => `${t.label} : ${t.desc}`).join('\n\n') : 'Choisir les propriétés de l’arme'}
    class="w-full flex items-center gap-1 px-2 py-1 bg-[#242424] border border-[#374151] rounded text-[11px] text-left transition-colors disabled:opacity-40 {open
      ? 'border-indigo-500'
      : 'hover:border-[#6b7280]'}"
  >
    <span class="flex-1 min-w-0 truncate {selected.length ? 'text-gray-100' : 'text-[#6b7280]'}">{summary}</span>
    <span class="shrink-0 text-[9px] text-[#9ca3af]">{open ? '▴' : '▾'}</span>
  </button>
</div>

{#if open}
  <!-- Backdrop: closes on any click outside the panel (also swallows that
       click, so it cannot hit the form underneath). -->
  <div class="fixed inset-0 z-[80]" onclick={() => (open = false)} role="presentation"></div>
  <div
    class="fixed z-[81] bg-[#1f2937] border border-[#374151] rounded-md shadow-xl overflow-y-auto py-1"
    style="left: {panel.left}px; top: {panel.top}px; width: {panel.width}px; max-height: {panel.maxHeight}px;"
    role="listbox"
    aria-multiselectable="true"
  >
    {#each PROPERTY_TAGS as tag}
      <label
        class="flex items-center gap-2 px-2 py-1 text-[11px] cursor-pointer hover:bg-[#374151] transition-colors"
        use:tooltip={tag.desc}
      >
        <input
          type="checkbox"
          checked={tags.includes(tag.id)}
          onchange={() => toggleTag(tag.id)}
          class="accent-indigo-500 shrink-0"
        />
        <span class="text-gray-100 truncate">{tag.label}</span>
      </label>
    {/each}
  </div>
{/if}

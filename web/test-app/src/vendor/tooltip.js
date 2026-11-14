/**
 * Svelte action for hover tooltips with 0.5s delay.
 * Usage: <button use:tooltip={"Tooltip text"}>Label</button>
 */
export function tooltip(node, text) {
  let tooltipEl = null;
  let timeout = null;

  function show() {
    if (!text) return;
    timeout = setTimeout(() => {
      tooltipEl = document.createElement('div');
      tooltipEl.textContent = text;
      tooltipEl.style.cssText = `
        position: fixed;
        background: #1e1e2e;
        color: #e5e7eb;
        font-size: 11px;
        line-height: 1.4;
        padding: 6px 10px;
        border-radius: 6px;
        border: 1px solid #374151;
        max-width: 220px;
        z-index: 9999;
        pointer-events: none;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        white-space: pre-line;
        word-wrap: break-word;
      `;
      document.body.appendChild(tooltipEl);

      const rect = node.getBoundingClientRect();
      const tipRect = tooltipEl.getBoundingClientRect();
      
      let top = rect.top - tipRect.height - 8;
      let left = rect.left + rect.width / 2 - tipRect.width / 2;

      // Flip below if would overflow top
      if (top < 4) {
        top = rect.bottom + 8;
      }

      // Clamp horizontal
      if (left < 4) left = 4;
      if (left + tipRect.width > window.innerWidth - 4) {
        left = window.innerWidth - tipRect.width - 4;
      }

      tooltipEl.style.top = `${top}px`;
      tooltipEl.style.left = `${left}px`;
    }, 500);
  }

  function hide() {
    if (timeout) {
      clearTimeout(timeout);
      timeout = null;
    }
    if (tooltipEl) {
      tooltipEl.remove();
      tooltipEl = null;
    }
  }

  node.addEventListener('mouseenter', show);
  node.addEventListener('mouseleave', hide);
  node.addEventListener('click', hide);

  return {
    update(newText) {
      text = newText;
      if (tooltipEl) {
        tooltipEl.textContent = newText;
      }
    },
    destroy() {
      hide();
      node.removeEventListener('mouseenter', show);
      node.removeEventListener('mouseleave', hide);
      node.removeEventListener('click', hide);
    }
  };
}

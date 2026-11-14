// The catalogue swaps its detail DOM on tab changes; keep the Atelier action present.
(() => {
  function addAtelierLink() {
    const match = location.pathname.match(/\/(?:personnages)\/([^/]+)\//);
    const id = match?.[1] || new URLSearchParams(location.search).get('character');
    if (!id) return;
    const actions = document.querySelector('.hero .actions, main > .actions');
    if (!actions || actions.querySelector('[data-atelier-character]')) return;
    const link = document.createElement('a');
    link.className = 'button'; link.dataset.atelierCharacter = '';
    link.href = '/atelier/?character=' + encodeURIComponent(decodeURIComponent(id));
    link.textContent = 'Ouvrir dans l’Atelier'; actions.append(link);
  }
  addAtelierLink();
  new MutationObserver(addAtelierLink).observe(document.querySelector('main') || document.body, {childList:true,subtree:true});
})();

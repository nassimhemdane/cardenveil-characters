// The catalogue swaps its detail DOM on tab changes; keep the Test action present.
(() => {
  function addTestLink() {
    const match = location.pathname.match(/\/(?:personnages)\/([^/]+)\//);
    const id = match?.[1] || new URLSearchParams(location.search).get('character');
    if (!id) return;
    const actions = document.querySelector('.hero .actions, main > .actions');
    if (!actions || actions.querySelector('[data-test-character]')) return;
    const link = document.createElement('a');
    link.className = 'button'; link.dataset.testCharacter = '';
    link.href = '/test/?character=' + encodeURIComponent(decodeURIComponent(id));
    link.textContent = 'Essayer dans Test'; actions.append(link);
  }
  addTestLink();
  new MutationObserver(addTestLink).observe(document.querySelector('main') || document.body, {childList:true,subtree:true});
})();

/* All content stays readable without JavaScript. Search never interprets source HTML. */
'use strict';
const menu = document.querySelector('.docs-nav details');
if (menu && matchMedia('(max-width:760px)').matches) menu.open = false;
const normalize = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
for (const [id, className, key] of [
  ['reading-size', 'reading-large', 'rules-large'],
  ['reading-theme', 'reading-light', 'rules-light']
]) {
  const button = document.getElementById(id);
  if (!button) continue;
  let enabled = false;
  try { enabled = localStorage.getItem(key) === 'true'; } catch (_) { /* optional preference */ }
  const update = () => {
    document.body.classList.toggle(className, enabled);
    button.setAttribute('aria-pressed', String(enabled));
  };
  update(); button.hidden = false;
  button.addEventListener('click', () => {
    enabled = !enabled; update();
    try { localStorage.setItem(key, String(enabled)); } catch (_) { /* optional preference */ }
  });
}
const search = document.querySelector('#rule-search');
if (search) {
  const status = document.querySelector('#search-status');
  const results = document.querySelector('#search-results');
  const clear = document.querySelector('#clear-search');
  const hint = 'Tous les manuels, fiches de référence et arbitrages du MJ.';
  fetch('/regles/search.json').then(r => {
    if (!r.ok) throw Error('Index indisponible');
    return r.json();
  }).then(entries => {
    const indexed = entries.map(e => ({...e, hay: normalize(e.title + ' ' + e.section + ' ' + e.text), heading: normalize(e.title + ' ' + e.section)}));
    search.disabled = false;
    const stop = new Set(['de','des','du','la','le','les','un','une','et','en','comment']);
    let timer, shown = 12;
    function highlight(node, value, words) {
      const normalized = normalize(value);
      const ranges = [];
      for (const word of words) {
        let at = normalized.indexOf(word);
        while (at !== -1) { ranges.push([at, at + word.length]); at = normalized.indexOf(word, at + word.length); }
      }
      ranges.sort((a,b) => a[0] - b[0]);
      let end = 0;
      for (const [start, finish] of ranges) {
        if (start < end) continue;
        node.append(document.createTextNode(value.slice(end, start)));
        const mark = document.createElement('mark'); mark.textContent = value.slice(start, finish); node.append(mark); end = finish;
      }
      node.append(document.createTextNode(value.slice(end)));
    }
    function render() {
      const query = search.value.trim();
      const terms = (normalize(query).match(/[a-z0-9]+/g) || []).filter(w => !stop.has(w));
      results.replaceChildren(); clear.hidden = !query;
      if (!terms.length) { status.textContent = hint; return; }
      const matches = indexed.filter(e => terms.every(w => e.hay.includes(w))).map(e => ({
        ...e, score: terms.reduce((n,w) => n + (e.heading.includes(w) ? 4 : 1), 0) + (e.url.startsWith('/regles/arbitrages/') ? 5 : 0)
      })).sort((a,b) => b.score - a.score);
      status.textContent = matches.length ? `${matches.length} résultat${matches.length > 1 ? 's' : ''} · ${Math.min(shown, matches.length)} affiché${Math.min(shown, matches.length) > 1 ? 's' : ''}` : 'Aucun résultat. Essayez un terme plus court ou consultez les chapitres.';
      for (const entry of matches.slice(0, shown)) {
        const link = document.createElement('a'); link.className = 'search-result'; link.href = entry.url;
        const title = document.createElement('strong'); highlight(title, entry.section + ' · ' + entry.title, terms);
        const excerpt = document.createElement('p');
        const at = Math.max(0, normalize(entry.text).indexOf(terms[0]) - 65);
        const text = (at ? '…' : '') + entry.text.slice(at, at + 230).replace(/\s+/g, ' ') + (at + 230 < entry.text.length ? '…' : '');
        highlight(excerpt, text, terms);
        const citation = document.createElement('small');
        citation.textContent = entry.source ? `${entry.source} · page ${entry.page}` : entry.url.startsWith('/regles/arbitrages/') ? 'Arbitrage du MJ · décision applicable' : 'Fiche de référence';
        link.append(title, excerpt, citation); results.append(link);
      }
      if (matches.length > shown) {
        const more = document.createElement('button'); more.id = 'search-more'; more.type = 'button'; more.textContent = 'Afficher davantage de résultats';
        more.addEventListener('click', () => { const previous = shown; shown += 12; render(); results.querySelectorAll('.search-result')[previous]?.focus(); });
        results.append(more);
      }
    }
    search.addEventListener('input', () => { clearTimeout(timer); shown = 12; timer = setTimeout(render, 120); });
    clear.addEventListener('click', () => { clearTimeout(timer); search.value = ''; render(); search.focus(); });
    search.addEventListener('keydown', event => { if (event.key === 'Escape') clear.click(); });
    render();
  }).catch(() => { status.textContent = 'Recherche indisponible. Les chapitres restent accessibles dans le menu.'; });
}
function revealSource() {
  let id; try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
  const target = document.getElementById(id);
  if (target?.matches('details.original-page')) target.open = true;
}
window.addEventListener('hashchange', revealSource); revealSource();
const mobileToc = document.querySelector('.mobile-toc');
mobileToc?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => { mobileToc.open = false; }));
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      document.querySelectorAll('.docs-toc a,.mobile-toc a').forEach(a => {
        const active = a.getAttribute('href') === '#' + entry.target.id;
        a.classList.toggle('active', active);
        if (active) a.setAttribute('aria-current', 'location'); else a.removeAttribute('aria-current');
      });
    }
  }, {rootMargin:'-10% 0px -70% 0px'});
  document.querySelectorAll('#reading h2[id],#reading h3[id],#reading section[id]').forEach(h => observer.observe(h));
}

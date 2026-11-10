/* URL identifies the edition; an explicit choice wins over first-visit detection. */
(() => {
  'use strict';
  const language = location.pathname.startsWith('/en/') ? 'en' : 'fr';
  window.CardenveilLanguage = language;
  const key = 'cardenveil-language';
  const frenchPath = location.pathname.replace(/^\/en(?=\/)/, '');
  const urlFor = lang => (lang === 'en' ? '/en' : '') + frenchPath + location.search + location.hash;
  let saved = null;
  try { saved = localStorage.getItem(key); } catch (_) { /* Storage is optional. */ }
  // Only the unqualified landing page negotiates automatically. Deep links are authoritative.
  if (location.pathname === '/' && !location.search && !location.hash) {
    const browser = (navigator.languages?.[0] || navigator.language || 'en').toLowerCase().startsWith('fr') ? 'fr' : 'en';
    if (saved === 'en') location.replace(urlFor('en'));
    else if (!saved) {
      fetch('/api/locale', {signal: AbortSignal.timeout(1500)})
        .then(r => r.ok && r.headers.get('content-type')?.includes('application/json') ? r.json() : null)
        .catch(() => null).then(result => {
          // A click made while detection was pending must not be overridden.
          try { if (localStorage.getItem(key)) return; } catch (_) {}
          if ((result?.language || browser) === 'en') location.replace(urlFor('en'));
        });
    }
  }
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-language]').forEach(link => {
      link.href = urlFor(link.dataset.language);
      link.addEventListener('click', () => {
        try { localStorage.setItem(key, link.dataset.language); } catch (_) {}
      });
    });
  });
})();

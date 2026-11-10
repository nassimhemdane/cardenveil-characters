/* All model and document text is rendered as text, never executable HTML. */
(() => {
  'use strict';
  const root = document.querySelector('.gm-native') || document;
  const $ = id => root.querySelector('#' + id);
  if (new URLSearchParams(location.search).get('embed') === '1') document.body.classList.add('gm-embedded');
  let sessionId = '', busy = false, pending = null;
  let savedSession = '';
  try { savedSession = sessionStorage.getItem('gm-session-en') || ''; } catch (_) { /* optional */ }
  try { pending = JSON.parse(sessionStorage.getItem('gm-pending-en') || 'null'); } catch (_) { /* invalid storage */ }
  function savePending() {
    try {
      if (pending) sessionStorage.setItem('gm-pending-en', JSON.stringify(pending));
      else sessionStorage.removeItem('gm-pending-en');
    } catch (_) { /* Storage may be unavailable; in-memory retry remains possible. */ }
  }
  function status(text) { $('status').textContent = text; }
  async function api(path, body) {
    const language=document.documentElement.lang==='en'?'en':'fr';
    const response = await fetch('/api/gm' + path, body === undefined ? {headers:{'Accept-Language':language}} : {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-Cardenveil-Client': 'gm','Accept-Language':language},
      body: JSON.stringify(body)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = Error(typeof data.detail === 'string' ? data.detail : 'Request rejected by the server.');
      error.status = response.status; throw error;
    }
    return data;
  }
  function option(value, text, disabled = false) {
    const node = document.createElement('option'); node.value = value; node.textContent = text; node.disabled = disabled; return node;
  }
  function lock(value) {
    busy = value;
    if (root !== document) root.setAttribute('aria-busy', String(value));
    for (const id of ['sessions', 'provider', 'model', 'create', 'message']) $(id).disabled = value || !!pending;
    $('send').disabled = value || !!pending;
    $('retry').disabled = value;
  }
  function sourceLinks(result) {
    const passages = [...(result?.data?.passages || []), ...(result?.data?.rulings || []),
      ...(result?.data?.sources || []),
      ...(result?.data?.pages || []).map(p => ({...p, document: result.data.document, section: ''}))];
    return passages.filter(p => typeof p.url === 'string' && p.url.startsWith('/regles/'));
  }
  function appendAnswer(node, text, allowed) {
    for (const line of text.split('\n')) {
      const heading = /^#{1,4} /.test(line);
      const row = document.createElement(heading ? 'strong' : 'div');
      const clean = line.replace(/^#{1,4} /, '').replace(/^[*-] /, '• ');
      const pattern = /\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^)]+)\)/g;
      let last = 0;
      for (const match of clean.matchAll(pattern)) {
        row.append(document.createTextNode(clean.slice(last, match.index)));
        if (match[1]) {
          const bold = document.createElement('b'); bold.textContent = match[1]; row.append(bold);
        } else if (allowed.has(match[3])) {
          const link = document.createElement('a'); link.href = match[3]; link.textContent = match[2];
          link.target = '_blank'; link.rel = 'noopener'; row.append(link);
        } else row.append(document.createTextNode(match[2]));
        last = match.index + match[0].length;
      }
      row.append(document.createTextNode(clean.slice(last) || (clean ? '' : '\u00a0')));
      node.append(row);
    }
  }
  function renderMessages(messages, events) {
    $('messages').replaceChildren();
    for (const message of messages) {
      const node = document.createElement('article'); node.className = 'gm-message ' + message.role;
      const label = document.createElement('strong'); label.textContent = message.role === 'user' ? 'You' : 'Cardenveil Guide';
      node.append(label);
      if (message.role === 'assistant') {
        const receipts = events.filter(e => e.payload.request_id === message.request_id)
          .map(e => e.payload.result).filter(r => r?.ok);
        const evidence = receipts.find(r => r.name === 'submit_answer');
        if (evidence) {
          const badge = document.createElement('small'); badge.className = 'gm-verdict';
          badge.textContent = {documented: 'References checked', partial: 'Partial answer',
            unknown: 'Insufficient information'}[evidence.data.answer_status];
          node.append(badge);
        }
        const links = new Map();
        for (const event of events.filter(e => e.payload.request_id === message.request_id)) {
          for (const source of sourceLinks(event.payload.result)) links.set(source.url, source);
        }
        appendAnswer(node, message.content, new Set(links.keys()));
        if (links.size) {
          const sources = document.createElement('details');
          const summary = document.createElement('summary'); summary.textContent = 'Sources consulted';
          sources.append(summary);
          for (const source of links.values()) {
            const link = document.createElement('a'); link.className = 'gm-source'; link.href = source.url;
            link.textContent = `${source.document}${source.page ? ' · p. ' + source.page : ''}`;
            link.target = '_blank'; link.rel = 'noopener'; sources.append(link);
          }
          node.append(sources);
        }
      } else node.append(document.createTextNode(message.content));
      $('messages').append(node);
    }
    $('messages').scrollTop = $('messages').scrollHeight;
  }
  function renderEvents(events) {
    $('events').replaceChildren();
    for (const event of events) {
      const detail = document.createElement('details'), summary = document.createElement('summary');
      const result = event.payload.result;
      summary.textContent = result ? `${result.name} — ${result.ok ? 'OK' : 'Error'}` : 'Session created';
      const pre = document.createElement('pre'); pre.textContent = JSON.stringify(event.payload, null, 2);
      detail.append(summary, pre); $('events').append(detail);
      for (const source of sourceLinks(result)) {
        if (!source.url.startsWith('/regles/') || source.url.startsWith('//')) continue;
        const link = document.createElement('a'); link.className = 'gm-source'; link.href = source.url;
        link.textContent = `${source.document} · ${source.section}${source.page ? ' · p. ' + source.page : ''}`;
        link.target = '_blank'; link.rel = 'noopener'; $('events').append(link);
      }
    }
  }
  async function refresh() {
    if (!sessionId) return;
    const [messages, events] = await Promise.all([
      api(`/sessions/${sessionId}/messages`), api(`/sessions/${sessionId}/events`)
    ]);
    renderMessages(messages, events); renderEvents(events);
  }
  async function loadSessions(selected = sessionId) {
    const sessions = await api('/sessions');
    $('sessions').replaceChildren(option('', 'New conversation'), ...sessions.map(s => option(s.id, s.name)));
    sessionId = sessions.some(s => s.id === selected) ? selected : '';
    $('sessions').value = sessionId;
    try { sessionStorage.setItem('gm-session-en', sessionId); } catch (_) { /* optional */ }
    if (!sessionId) { renderMessages([], []); renderEvents([]); }
    await refresh();
  }
  $('sessions').addEventListener('change', async () => {
    sessionId = $('sessions').value; lock(true);
    try { await loadSessions(); status('Ask your question about Cardenveil.'); } catch (e) { status(e.message); } finally { lock(false); }
  });
  $('create-session').addEventListener('submit', async event => {
    event.preventDefault(); if (busy) return; lock(true);
    try {
      const session = await api('/sessions', {name: $('session-name').value});
      await loadSessions(session.id); status('New conversation created.');
    } catch (e) { status(e.message); } finally { lock(false); }
  });
  async function send() {
    if (!pending || busy) return;
    lock(true); status('Searching the Cardenveil rules…');
    try {
      const result = await api(`/sessions/${pending.session}/messages`, pending.body);
      pending = null; savePending(); $('retry').hidden = true; $('message').value = '';
      await refresh();
      status(result.status === 'completed' ? 'Answer received · See the references below the answer.' : result.text);
    } catch (e) {
      if (e.status >= 400 && e.status < 500 && e.status !== 409) {
        pending = null; savePending();
      }
      status(e.message + (pending ? ' Use “Resume” to retrieve the same request without rerolling the dice.' : ''));
      $('retry').hidden = !pending;
    } finally { lock(false); }
  }
  $('chat-form').addEventListener('submit', async event => {
    event.preventDefault(); if (busy || pending) return;
    if (!sessionId) {
      lock(true);
      try {
        const session = await api('/sessions', {name: $('message').value.slice(0, 100)});
        await loadSessions(session.id);
      } catch (e) { status(e.message); lock(false); return; }
      lock(false);
    }
    pending = {session: sessionId, body: {language: document.documentElement.lang === 'en' ? 'en' : 'fr', request_id: crypto.randomUUID(), message: $('message').value,
      provider: $('provider').value, model: $('model').value}};
    savePending();
    send();
  });
  $('retry').addEventListener('click', send);
  for (const button of document.querySelectorAll('[data-question]')) {
    button.addEventListener('click', () => {
      if (busy || pending) return;
      $('message').value = button.dataset.question; $('message').focus();
    });
  }
  async function init() {
    try {
      const config = await api('/config');
      $('provider').replaceChildren(...config.providers.map(p => option(p.id, p.name)));
      function models() { $('model').replaceChildren(...config.providers.find(p => p.id === $('provider').value).models.map(m => option(m, m))); }
      $('provider').addEventListener('change', models); models();
      $('configuration').textContent = config.providers[0]?.id === 'ollama' ? 'Local Ollama model configured.' : config.configured ? 'Key configured on the server.' : 'Set GEMINI_API_KEY in the server .env file to chat.';
      await loadSessions(pending?.session || savedSession);
      if (pending && !sessionId) { pending = null; savePending(); }
      $('retry').hidden = !pending;
      lock(false); status(pending ? 'A request is waiting to resume.' : 'Ask your question about Cardenveil.');
    } catch (_) {
      status('The chatbot is unavailable on this site. I cannot answer right now. You can still browse the rules library.');
    }
  }
  init();
})();

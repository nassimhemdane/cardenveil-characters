/* Search and recommendations use only fields present in the published sheets. */
(() => {
  const norm = s => String(s ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/œ/g, 'oe');
  const plain = s => { const d = document.createElement('div'); d.innerHTML = String(s ?? ''); return d.textContent.trim(); };
  const escape = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const roles = {
    soin: ['heal', 'healing', 'restore', 'regain'],
    protection: ['protect', 'shield', 'reduce damage'],
    distance: ['ranged', 'bow', 'crossbow'],
    invocation: ['summon', 'summoning', 'summoner'],
    controle: ['restrain', 'immobiliz', 'slow', 'control', 'push'],
    discretion: ['stealth', 'invisible', 'invisibility', 'hidden']
  };
  const roleLabels = {soin:'Heal', protection:'Protect', distance:'Ranged', invocation:'Summon', controle:'Control', discretion:'Hide'};
  const includes = (value, word) => norm(value).includes(norm(word));
  function portrait(c) {
    const name=plain(c.identity.nom),href=`/personnages/${encodeURIComponent(c.id)}/`;
    const content=typeof c.portrait==='string' && c.portrait.startsWith('/assets/')
      ? `<img src="${escape(c.portrait)}" alt="Portrait of ${escape(name)}" loading="lazy" decoding="async" width="480" height="360">`
      : '<span class="guide-portrait-empty">Portrait not recorded</span>';
    return `<a class="guide-portrait" href="${href}" aria-label="Open the sheet for ${escape(name)}">${content}</a>`;
  }
  function entries(c) {
    const m = c.catalog || {};
    return [
      ['Name', c.identity.nom, 10], ['Class', [].concat(m.class || []).join(' '), 6],
      ['Ancestry', c.identity.race, 5], ['Creator', m.creator, 3],
      ['Play style', m.gameplaySummary, 4], ['Story', m.loreSummary, 2],
      ['Totem · ' + plain(c.totem?.nom), c.totem?.description, 2],
      ...(c.capacities || []).map(a => ['Ability · ' + plain(a.name), `${plain(a.name)} — ${plain(a.description)}`, 2]),
      ...(c.weapons || []).map(w => ['Weapon', w.nom, 2]),
      ...Object.entries(c.narrative || {}).map(([k,v]) => ['Narrative · '+k, Array.isArray(v)?v.join(' '):v, 1])
    ].filter(([,v]) => v).map(([label,value,weight]) => ({label, value:plain(value), weight}));
  }
  function evidence(row, role) {
    return row.fields.filter(f => /^(Play style|Ability|Totem)/.test(f.label)).find(f => roles[role]?.some(w => w==='bow'?/\bbow\b/.test(norm(f.value)):includes(f.value,w)));
  }
  window.CardenveilCatalogue = {norm, entries, evidence, mount(root, characters, card) {
    const rows = characters.map(c => ({c, fields:entries(c)}));
    const classMap = new Map();
    for (const c of characters) [].concat(c.catalog?.class || []).forEach((label,i) => classMap.set(c.catalog?.classKeys?.[i] || label, label));
    const classes = [...classMap].sort((a,b)=>a[1].localeCompare(b[1],'en'));
    const params = new URLSearchParams(location.search);
    root.innerHTML = `<section class="character-guide" aria-labelledby="guide-title">
      <div><span class="eyebrow">Your next adventure</span><h1 id="guide-title">Which character suits you?</h1><p>Describe what you want to play. The guide helps you explore the sheets and cites its sources.</p></div>
      <div class="guide-options" aria-label="Play preferences">${Object.entries(roleLabels).map(([k,v])=>`<button type="button" class="chip" data-role="${k}" aria-pressed="false">${v}</button>`).join('')}<button type="button" class="chip" id="guide-easy" aria-pressed="false">Easy to learn</button></div>
      <form id="guide-form"><label for="guide-message">Talk to the guide</label><div class="guide-compose"><input id="guide-message" maxlength="1000" placeholder="I am a beginner and would like to heal my allies…" required><button class="button primary">Find suggestions</button></div></form>
      <p id="guide-mode" class="guide-note">Catalogue guide · filters and sheet excerpts</p><div id="guide-answer" aria-live="polite"><p>Choose a preference or describe your style to find up to three suggestions.</p></div>
    </section><section aria-labelledby="catalog-title"><div class="catalog-heading"><h2 id="catalog-title">Explore the characters</h2><p>Name, ancestry, class, ability, totem or story.</p></div>
      <div class="toolbar catalog-filters"><label>Search<input id="search" type="search" placeholder="E.g. fire, sword, healing…"></label><label>Class<select id="class-filter"><option value="">All classes</option>${classes.map(([key,label])=>`<option value="${escape(key)}">${escape(label)}</option>`).join('')}</select></label><label>Complexity<select id="difficulty-filter"><option value="">All</option><option value="2">Up to 2 / 5</option><option value="3">Up to 3 / 5</option><option value="4">Up to 4 / 5</option><option value="unknown">Not recorded</option></select></label><label>Sort<select id="sort"><option value="relevance">Relevance</option><option value="name">Name A → Z</option><option value="easy">Complexity: low to high</option><option value="difficulty">Complexity: high to low</option></select></label><button id="reset-search" type="button">Reset</button></div><p class="count" id="count" role="status"></p><div class="grid" id="grid"></div></section>`;
    const $ = id => root.querySelector('#'+id);
    for (const [id,key] of [['search','q'],['class-filter','class'],['difficulty-filter','difficulty'],['sort','sort']]) if(params.has(key)) $(id).value=params.get(key);
    function draw() {
      const words=norm($('search').value).split(/\s+/).filter(Boolean), cl=$('class-filter').value, difficulty=$('difficulty-filter').value, sort=$('sort').value;
      const matches=rows.map(row=>({...row, score:words.reduce((n,w)=>n+row.fields.reduce((v,f)=>v+(includes(f.value,w)?f.weight:0),0),0)})).filter(row=> words.every(w=>row.fields.some(f=>includes(f.value,w))) && (!cl || [].concat(row.c.catalog?.classKeys||row.c.catalog?.class||[]).includes(cl)) && (!difficulty || (difficulty==='unknown'?row.c.catalog?.difficulty==null:row.c.catalog?.difficulty!=null && row.c.catalog.difficulty<=+difficulty)));
      matches.sort((a,b)=> (sort==='relevance'? b.score-a.score : sort==='easy'?(a.c.catalog?.difficulty??99)-(b.c.catalog?.difficulty??99):sort==='difficulty'?(b.c.catalog?.difficulty??-1)-(a.c.catalog?.difficulty??-1):0) || plain(a.c.identity.nom).localeCompare(plain(b.c.identity.nom),'en'));
      $('count').textContent=`${matches.length} character${matches.length>1?'s':''} of ${characters.length}`;
      $('grid').innerHTML=matches.map(row=>`<a class="character-link" href="/personnages/${encodeURIComponent(row.c.id)}/">${card(row.c)}${words.length?`<p class="match-reason">Found in: ${escape([...new Set(row.fields.filter(f=>words.some(w=>includes(f.value,w))).map(f=>f.label))].slice(0,3).join(', '))}</p>`:''}</a>`).join('') || '<div class="empty-state">No character meets these criteria. Remove a filter or try a broader search term.</div>';
      const q=new URLSearchParams(); for(const [id,key] of [['search','q'],['class-filter','class'],['difficulty-filter','difficulty'],['sort','sort']]) if($(id).value && $(id).value!=='relevance')q.set(key,$(id).value);
      history.replaceState({},'',location.pathname+(q.size?'?'+q:''));
    }
    for(const id of ['search','class-filter','difficulty-filter','sort']) $(id).addEventListener(id==='search'?'input':'change',draw);
    $('reset-search').onclick=()=>{for(const id of ['search','class-filter','difficulty-filter'])$(id).value='';$('sort').value='relevance';draw();$('search').focus();};
    let selected=[], excluded=[], easy=false, localAI=false, publicAI=false, humanToken='', widget=null;
    const aiReady = (async()=>{
      try {
        const response=await fetch('/api/recommendation-config',{signal:AbortSignal.timeout(8000)});
        const config=response.ok && response.headers.get('content-type')?.includes('application/json') ? await response.json() : null;
        if(config?.enabled && config.siteKey){
          publicAI=true;
          $('guide-mode').textContent='Gemini · up to 6 suggestions with explanations. Your request is sent to Google; avoid personal information.';
          $('guide-answer').textContent='Describe your style, theme or play preferences.';
          const container=document.createElement('div');container.id='guide-verification';$('guide-form').append(container);
          const script=document.createElement('script');script.src='https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';script.async=true;
          script.onload=()=>{widget=window.turnstile.render(container,{sitekey:config.siteKey,action:'recommend',
            callback:token=>{humanToken=token;},'expired-callback':()=>{humanToken='';},'error-callback':()=>{humanToken='';}});};
          script.onerror=()=>{$('guide-answer').textContent='The anti-abuse check is blocked. Allow Cloudflare Turnstile or use the filters.';};
          document.head.append(script);
          return;
        }
      } catch {}
      try {
        const r=await fetch('/api/gm/config',{signal:AbortSignal.timeout(8000)}),c=r.ok?await r.json():null;
        localAI=c?.providers?.[0]?.id==='ollama';
        if(localAI){$('guide-mode').textContent='Qwen via local Ollama · up to 6 suggestions with explanations';$('guide-answer').textContent='Describe what you want: the model will compare the sheets and explain each suggestion.';}
      } catch {}
    })();
    function recommend(note='') {
      excluded=excluded.filter(role=>!selected.includes(role));
      root.querySelectorAll('[data-role]').forEach(b=>{const on=selected.includes(b.dataset.role);b.classList.toggle('active',on);b.setAttribute('aria-pressed',on);});
      $('guide-easy').classList.toggle('active',easy);$('guide-easy').setAttribute('aria-pressed',easy);
      if(!selected.length&&!easy){$('guide-answer').innerHTML=`<p>${escape(note || 'Which role appeals to you: healing, protecting, controlling, summoning, hiding or fighting at range?')}</p>`;return;}
      const candidates=rows.map(row=>({...row, proofs:selected.map(role=>({role,source:evidence(row,role)}))})).filter(row=>(!easy || row.c.catalog?.difficulty!=null&&row.c.catalog.difficulty<=2) && row.proofs.every(p=>p.source) && excluded.every(role=>!evidence(row,role)));
      candidates.sort((a,b)=>(a.c.catalog?.difficulty??99)-(b.c.catalog?.difficulty??99));
      $('guide-answer').innerHTML=`<p>${escape(note)} ${excluded.length?'Exclusions : '+escape(excluded.map(r=>roleLabels[r]).join(', '))+'. ':''}${candidates.length?`${candidates.length}  sheets contain evidence for these criteria. Here are ${Math.min(3,candidates.length)} suggestions to compare; this does not guarantee their effectiveness in play.`:'I cannot suggest a character meeting these criteria from the available sheets. Try removing a preference.'}</p><div class="guide-results">${candidates.slice(0,3).map(row=>`<article>${portrait(row.c)}<h3><a href="/personnages/${encodeURIComponent(row.c.id)}/">${escape(plain(row.c.identity.nom))} ↗</a></h3><p>Complexity : ${row.c.catalog?.difficulty??'not recorded'}${row.c.catalog?.difficulty!=null?' / 5':''}</p>${row.proofs.map(p=>`<p><strong>${roleLabels[p.role]}</strong> · ${escape(p.source.label)}</p><blockquote>${escape(p.source.value)}</blockquote>`).join('') || `<blockquote>${escape(plain(row.c.catalog?.gameplaySummary||'Play style not recorded.'))}</blockquote>`}<a class="button" href="/personnages/${encodeURIComponent(row.c.id)}/">Read the source sheet</a></article>`).join('')}</div>`;
    }
    root.querySelectorAll('[data-role]').forEach(b=>b.onclick=()=>{selected=selected.includes(b.dataset.role)?selected.filter(x=>x!==b.dataset.role):[...selected,b.dataset.role];recommend();});
    $('guide-easy').onclick=()=>{easy=!easy;recommend();};
    $('guide-form').onsubmit=async e=>{
      e.preventDefault(); const message=$('guide-message').value.trim(); if(!message)return;
      const button=e.submitter || $('guide-form').querySelector('button');button.disabled=true;$('guide-answer').textContent='Searching the sheets…';
      try {
        await aiReady;
        if(localAI || publicAI){
          if(publicAI && !humanToken)throw Error('Wait for the anti-abuse check above, then try again.');
          const response = await fetch(publicAI?'/api/recommendations':'/api/gm/character-recommendations', {
            method:'POST', headers:{'Content-Type':'application/json','Accept-Language':document.documentElement.lang,'X-Cardenveil-Client':publicAI?'catalogue':'gm'},
            body:JSON.stringify(publicAI?{message,token:humanToken,language:document.documentElement.lang}:{message,language:document.documentElement.lang}),signal:AbortSignal.timeout(70000)
          });
          if(!response.ok){const error=await response.json().catch(()=>null);throw Error(error?.detail || 'The model cannot respond right now. Try again or use the filters.');}
          const result = await response.json();
          if(result.retrieval)$('guide-mode').textContent=result.retrieval.mode==='structured-identity'?'Exact search in sheet identities · no Gemini call':`Recherche sur tous les champs, statistiques prioritaires · ${result.retrieval.mode.includes('embeddings')?'recherche par embeddings':'recherche par mots-clés (embeddings indisponibles)'} · phrase transmise à Google`;
          const matches = (result.matches || []).slice(0,6).map(match => ({
            ...match, row: rows.find(row => row.c.id === match.character_id)
          })).filter(match => match.row);
          $('guide-answer').innerHTML = `<p>${escape(result.explanation)}</p><div class="guide-results">${matches.map(match=>`<article>${portrait(match.row.c)}<h3><a href="/personnages/${encodeURIComponent(match.character_id)}/">${escape(plain(match.row.c.identity.nom))}</a></h3><p>Complexity : ${escape(match.row.c.catalog?.difficulty ?? 'not recorded')} / 5</p>${match.stats?`<p>STR ${escape(match.stats.force)} · AGI ${escape(match.stats.agilite)} · SPI ${escape(match.stats.esprit)} · SOC ${escape(match.stats.social)}</p><p>Attribute profile: ${escape(match.profile)} (indicative)</p>`:''}<p>${escape(match.comment)}</p><blockquote>${escape(match.evidence)}</blockquote><a class="button" href="/personnages/${encodeURIComponent(match.character_id)}/">Read the source sheet</a></article>`).join('')}</div>${matches.length?'':'<p>No sheet matches this request closely enough.</p>'}`;
          return;
        }
        {
          const value=norm(message);
          if(/\b(without|not|except|avoid|neither|no)\b/.test(value)){ $('guide-answer').textContent='To respect your exclusions, select the criteria above directly. The catalogue guide cannot interpret this sentence confidently enough.';return; }
          selected=Object.keys(roles).filter(k=>roles[k].some(w=>value.includes(w))||value.includes(k));easy=/beginner|easy|simple/.test(value);
          recommend('Keyword-based search. Adjust the criteria above to refine your request.');
        }
      } catch(err){$('guide-answer').textContent=err.name==='TimeoutError'?'The model is taking too long to respond. Try again later.':err.message;} finally {button.disabled=false;if(publicAI && widget!==null){humanToken='';window.turnstile.reset(widget);}}
    };
    draw();
  }};
})();

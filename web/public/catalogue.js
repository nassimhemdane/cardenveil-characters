/* Search and recommendations use only fields present in the published sheets. */
(() => {
  const norm = s => String(s ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/œ/g, 'oe');
  const plain = s => { const d = document.createElement('div'); d.innerHTML = String(s ?? ''); return d.textContent.trim(); };
  const escape = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const roles = {
    soin: ['soin', 'soigne', 'soigner', 'soignez', 'guerison', 'regagne'],
    protection: ['protege', 'proteger', 'protegez', 'bouclier', 'reduit les degats'],
    distance: ['distance', 'arc', 'arbalete'],
    invocation: ['invoque', 'invoquer', 'invoquez', 'invocation', 'invocateur'],
    controle: ['entrave', 'immobilis', 'ralenti', 'controle', 'repousse'],
    discretion: ['furtif', 'invisible', 'invisibilite', 'discretion']
  };
  const roleLabels = {soin:'Soigner', protection:'Protéger', distance:'À distance', invocation:'Invoquer', controle:'Contrôler', discretion:'Se dissimuler'};
  const includes = (value, word) => norm(value).includes(norm(word));
  function entries(c) {
    const m = c.catalog || {};
    return [
      ['Nom', c.identity.nom, 10], ['Classe', [].concat(m.class || []).join(' '), 6],
      ['Peuple', c.identity.race, 5], ['Créateur', m.creator, 3],
      ['Style de jeu', m.gameplaySummary, 4], ['Histoire', m.loreSummary, 2],
      ['Totem · ' + plain(c.totem?.nom), c.totem?.description, 2],
      ...(c.capacities || []).map(a => ['Capacité · ' + plain(a.name), `${plain(a.name)} — ${plain(a.description)}`, 2]),
      ...(c.weapons || []).map(w => ['Arme', w.nom, 2]),
      ...Object.entries(c.narrative || {}).map(([k,v]) => ['Narratif · '+k, Array.isArray(v)?v.join(' '):v, 1])
    ].filter(([,v]) => v).map(([label,value,weight]) => ({label, value:plain(value), weight}));
  }
  function evidence(row, role) {
    return row.fields.filter(f => /^(Style de jeu|Capacité|Totem)/.test(f.label)).find(f => roles[role]?.some(w => w==='arc'?/\barc\b/.test(norm(f.value)):includes(f.value,w)));
  }
  window.CardenveilCatalogue = {norm, entries, evidence, mount(root, characters, card) {
    const rows = characters.map(c => ({c, fields:entries(c)}));
    const classes = [...new Set(characters.flatMap(c => [].concat(c.catalog?.class || [])))].sort((a,b)=>a.localeCompare(b,'fr'));
    const params = new URLSearchParams(location.search);
    root.innerHTML = `<section class="character-guide" aria-labelledby="guide-title">
      <div><span class="eyebrow">Votre prochaine aventure</span><h1 id="guide-title">Quel personnage vous ressemble ?</h1><p>Décrivez votre envie. Le guide vous aide à explorer les fiches, avec ses sources.</p></div>
      <div class="guide-options" aria-label="Envies de jeu">${Object.entries(roleLabels).map(([k,v])=>`<button type="button" class="chip" data-role="${k}" aria-pressed="false">${v}</button>`).join('')}<button type="button" class="chip" id="guide-easy" aria-pressed="false">Facile à prendre en main</button></div>
      <form id="guide-form"><label for="guide-message">Parlez au guide</label><div class="guide-compose"><input id="guide-message" maxlength="1000" placeholder="Je débute, je voudrais soigner mes alliés…" required><button class="button primary">Me conseiller</button></div></form>
      <p id="guide-mode" class="guide-note">Guide du catalogue · critères et extraits des fiches</p><div id="guide-answer" aria-live="polite"><p>Choisissez une envie ou décrivez votre style pour découvrir jusqu’à trois pistes.</p></div>
    </section><section aria-labelledby="catalog-title"><div class="catalog-heading"><h2 id="catalog-title">Explorez les personnages</h2><p>Nom, peuple, classe, capacité, totem ou histoire.</p></div>
      <div class="toolbar catalog-filters"><label>Rechercher<input id="search" type="search" placeholder="Ex. feu, épée, guérison…"></label><label>Classe<select id="class-filter"><option value="">Toutes les classes</option>${classes.map(v=>`<option>${escape(v)}</option>`).join('')}</select></label><label>Complexité<select id="difficulty-filter"><option value="">Toutes</option><option value="2">Jusqu’à 2 / 5</option><option value="3">Jusqu’à 3 / 5</option><option value="4">Jusqu’à 4 / 5</option><option value="unknown">Non renseignée</option></select></label><label>Trier<select id="sort"><option value="relevance">Pertinence</option><option value="name">Nom A → Z</option><option value="easy">Complexité croissante</option><option value="difficulty">Complexité décroissante</option></select></label><button id="reset-search" type="button">Réinitialiser</button></div><p class="count" id="count" role="status"></p><div class="grid" id="grid"></div></section>`;
    const $ = id => root.querySelector('#'+id);
    for (const [id,key] of [['search','q'],['class-filter','class'],['difficulty-filter','difficulty'],['sort','sort']]) if(params.has(key)) $(id).value=params.get(key);
    function draw() {
      const words=norm($('search').value).split(/\s+/).filter(Boolean), cl=$('class-filter').value, difficulty=$('difficulty-filter').value, sort=$('sort').value;
      const matches=rows.map(row=>({...row, score:words.reduce((n,w)=>n+row.fields.reduce((v,f)=>v+(includes(f.value,w)?f.weight:0),0),0)})).filter(row=> words.every(w=>row.fields.some(f=>includes(f.value,w))) && (!cl || [].concat(row.c.catalog?.class||[]).includes(cl)) && (!difficulty || (difficulty==='unknown'?row.c.catalog?.difficulty==null:row.c.catalog?.difficulty!=null && row.c.catalog.difficulty<=+difficulty)));
      matches.sort((a,b)=> (sort==='relevance'? b.score-a.score : sort==='easy'?(a.c.catalog?.difficulty??99)-(b.c.catalog?.difficulty??99):sort==='difficulty'?(b.c.catalog?.difficulty??-1)-(a.c.catalog?.difficulty??-1):0) || plain(a.c.identity.nom).localeCompare(plain(b.c.identity.nom),'fr'));
      $('count').textContent=`${matches.length} personnage${matches.length>1?'s':''} sur ${characters.length}`;
      $('grid').innerHTML=matches.map(row=>`<a class="character-link" href="/personnages/${encodeURIComponent(row.c.id)}/">${card(row.c)}${words.length?`<p class="match-reason">Trouvé dans : ${escape([...new Set(row.fields.filter(f=>words.some(w=>includes(f.value,w))).map(f=>f.label))].slice(0,3).join(', '))}</p>`:''}</a>`).join('') || '<div class="empty-state">Aucun personnage ne réunit ces critères. Retirez un filtre ou essayez un mot plus général.</div>';
      const q=new URLSearchParams(); for(const [id,key] of [['search','q'],['class-filter','class'],['difficulty-filter','difficulty'],['sort','sort']]) if($(id).value && $(id).value!=='relevance')q.set(key,$(id).value);
      history.replaceState({},'',location.pathname+(q.size?'?'+q:''));
    }
    for(const id of ['search','class-filter','difficulty-filter','sort']) $(id).addEventListener(id==='search'?'input':'change',draw);
    $('reset-search').onclick=()=>{for(const id of ['search','class-filter','difficulty-filter'])$(id).value='';$('sort').value='relevance';draw();$('search').focus();};
    let selected=[], excluded=[], easy=false, localAI=false;
    fetch('/api/gm/config').then(r=>r.ok?r.json():null).then(c=>{localAI=c?.providers?.[0]?.id==='ollama';if(localAI)$('guide-mode').textContent='Ollama local · vos envies sont interprétées sur cet ordinateur';}).catch(()=>{});
    function recommend(note='') {
      excluded=excluded.filter(role=>!selected.includes(role));
      root.querySelectorAll('[data-role]').forEach(b=>{const on=selected.includes(b.dataset.role);b.classList.toggle('active',on);b.setAttribute('aria-pressed',on);});
      $('guide-easy').classList.toggle('active',easy);$('guide-easy').setAttribute('aria-pressed',easy);
      if(!selected.length&&!easy){$('guide-answer').innerHTML=`<p>${escape(note || 'Quel rôle vous attire : soigner, protéger, contrôler, invoquer, vous dissimuler ou jouer à distance ?')}</p>`;return;}
      const candidates=rows.map(row=>({...row, proofs:selected.map(role=>({role,source:evidence(row,role)}))})).filter(row=>(!easy || row.c.catalog?.difficulty!=null&&row.c.catalog.difficulty<=2) && row.proofs.every(p=>p.source) && excluded.every(role=>!evidence(row,role)));
      candidates.sort((a,b)=>(a.c.catalog?.difficulty??99)-(b.c.catalog?.difficulty??99));
      $('guide-answer').innerHTML=`<p>${escape(note)} ${excluded.length?'Exclusions : '+escape(excluded.map(r=>roleLabels[r]).join(', '))+'. ':''}${candidates.length?`${candidates.length} fiches contiennent des indices pour ces critères. Voici ${Math.min(3,candidates.length)} pistes à comparer ; cela ne garantit pas leur efficacité en partie.`:'Je ne sais pas vous proposer de personnage réunissant ces critères à partir des fiches disponibles. Essayez de retirer une envie.'}</p><div class="guide-results">${candidates.slice(0,3).map(row=>`<article><h3><a href="/personnages/${encodeURIComponent(row.c.id)}/">${escape(plain(row.c.identity.nom))} ↗</a></h3><p>Complexité : ${row.c.catalog?.difficulty??'non renseignée'}${row.c.catalog?.difficulty!=null?' / 5':''}</p>${row.proofs.map(p=>`<p><strong>${roleLabels[p.role]}</strong> · ${escape(p.source.label)}</p><blockquote>${escape(p.source.value)}</blockquote>`).join('') || `<blockquote>${escape(plain(row.c.catalog?.gameplaySummary||'Style de jeu non renseigné.'))}</blockquote>`}<a class="button" href="/personnages/${encodeURIComponent(row.c.id)}/">Lire la fiche source</a></article>`).join('')}</div>`;
    }
    root.querySelectorAll('[data-role]').forEach(b=>b.onclick=()=>{selected=selected.includes(b.dataset.role)?selected.filter(x=>x!==b.dataset.role):[...selected,b.dataset.role];recommend();});
    $('guide-easy').onclick=()=>{easy=!easy;recommend();};
    $('guide-form').onsubmit=async e=>{
      e.preventDefault(); const message=$('guide-message').value.trim(); if(!message)return;
      const button=e.submitter;button.disabled=true;$('guide-answer').textContent='Je cherche dans les fiches…';
      try {
        if(localAI){
          const r=await fetch('/api/gm/character-preferences',{method:'POST',headers:{'Content-Type':'application/json','X-Cardenveil-Client':'gm'},body:JSON.stringify({message,roles:selected,excluded_roles:excluded,easy})});
          if(!r.ok)throw Error('Le modèle local est indisponible. Vous pouvez utiliser les boutons de critères.');
          const p=await r.json();selected=p.roles;excluded=p.excluded_roles||[];easy=p.easy;recommend(p.clarification+(excluded.length?' Les fiches mentionnant les roles exclus sont retirees ; une fiche incomplete ne permet pas de garantir leur absence.':''));
        } else {
          const value=norm(message);
          if(/\b(sans|pas|sauf|eviter|ni)\b/.test(value)){ $('guide-answer').textContent='Pour respecter vos exclusions, choisissez directement les critères ci-dessus. Le guide du catalogue ne sait pas interpréter cette phrase avec assez de certitude.';return; }
          selected=Object.keys(roles).filter(k=>roles[k].some(w=>value.includes(w))||value.includes(k));easy=/debut|facile|simple/.test(value);
          recommend('Recherche guidée par mots-clés. Ajustez les critères ci-dessus pour préciser votre demande.');
        }
      } catch(err){$('guide-answer').textContent=err.message;} finally {button.disabled=false;}
    };
    draw();
  }};
})();

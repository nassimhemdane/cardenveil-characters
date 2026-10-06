/* Optional progressive enhancement: every rule and navigation link exists without JavaScript. */
'use strict';
const menu=document.querySelector('.docs-nav details');
if(menu&&matchMedia('(max-width:760px)').matches)menu.open=false;
const search=document.querySelector('#rule-search');
/** Normalize search accents and case without changing displayed source text. */
const normalize=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
if(search){
  const status=document.querySelector('#search-status'),results=document.querySelector('#search-results');
  fetch('/regles/search.json').then(r=>{if(!r.ok)throw Error('Index indisponible');return r.json()}).then(entries=>{
    const indexed=entries.map(e=>({...e,hay:normalize(e.title+' '+e.text)}));search.disabled=false;status.textContent='Recherchez dans les documents sources et les fiches de référence.';
    let timer;
    search.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>{
      const words=normalize(search.value.trim()).split(/\s+/).filter(Boolean);results.replaceChildren();
      if(!words.length){status.textContent='Recherchez dans les documents sources et les fiches de référence.';return}
      const matches=indexed.filter(e=>words.every(w=>e.hay.includes(w)));
      status.textContent=matches.length?`${matches.length} résultats${matches.length>20?' — les 20 premiers sont affichés':''}`:'Aucun résultat. Essayez un autre terme.';
      for(const entry of matches.slice(0,20)){
        const link=document.createElement('a');link.className='search-result';link.href=entry.url;
        const title=document.createElement('strong');title.textContent=entry.title+' · '+entry.section;
        const excerpt=document.createElement('p');const at=Math.max(0,normalize(entry.text).indexOf(words[0])-70);excerpt.textContent=(at?'…':'')+entry.text.slice(at,at+220).replace(/\s+/g,' ')+'…';
        link.append(title,excerpt);
        if(entry.source){const citation=document.createElement('small');citation.textContent=entry.source+' · page '+entry.page;link.append(citation)}
        results.append(link);
      }
    },120)});
  }).catch(()=>{status.textContent='Recherche indisponible. Les chapitres restent accessibles ci-dessous.'});
}
/** Open the referenced original page when following a source citation or shared fragment. */
function revealSource(){
  let id;try{id=decodeURIComponent(location.hash.slice(1))}catch{return}
  const target=document.getElementById(id);
  if(target?.matches('details.original-page'))target.open=true;
}
window.addEventListener('hashchange',revealSource);revealSource();
/** Mark the current topic in the reading contents without changing ordinary anchor links. */
if('IntersectionObserver' in window){
  const observer=new IntersectionObserver(entries=>{
    for(const entry of entries){if(!entry.isIntersecting)continue;
      document.querySelectorAll('.docs-toc a').forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+entry.target.id));
    }
  },{rootMargin:'-10% 0px -70% 0px'});
  document.querySelectorAll('.rule-heading').forEach(h=>observer.observe(h));
}

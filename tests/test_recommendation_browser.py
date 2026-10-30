"""Exercise natural-language recommendations in Chromium with a deterministic API."""

import pytest
from test_gemini_pages import run_harness


@pytest.mark.parametrize('provider', ['local', 'public'])
def test_local_recommendation_cards(tmp_path, provider):
    """Render six comments, preserve escaping, and recover from an unavailable model."""
    harness = b'''<pre id="result">RUNNING</pre><div id="catalogue"></div><script>
(async()=>{try{
const source=await (await fetch('/web/public/catalogue.js')).text();
const characters=Array.from({length:7},(_,i)=>({id:'hero-'+i,portrait:i===1?'':i===2?'javascript:alert(1)':'/assets/test-portrait.png',identity:{nom:'Hero '+i},catalog:{difficulty:2,gameplaySummary:'Soigne les allies'},capacities:[]}));
let fail=false;
window.fetch=async(url,options)=>{
 if(url==='/api/recommendation-config')return {ok:true,headers:new Headers({'Content-Type':'application/json'}),json:async()=>({enabled:PUBLIC_MODE,siteKey:'PUBLIC'})};
 if(url==='/api/gm/config')return {ok:true,json:async()=>({providers:[{id:'ollama'}]})};
 if(url!==(PUBLIC_MODE?'/api/recommendations':'/api/gm/character-recommendations'))throw Error('Unexpected URL');
 if(PUBLIC_MODE && !JSON.parse(options.body).token)throw Error('Missing Turnstile token');
 if(JSON.parse(options.body).message!=='soin a distance')throw Error('Missing phrase');
 return {ok:!fail,json:async()=>({explanation:'Suggestions',matches:characters.map(c=>({character_id:c.id,comment:'Correspond au soin <img src=x onerror=alert(1)>',evidence:'Soigne les allies'}))})};
};
if(PUBLIC_MODE){
 window.turnstile={render:(container,options)=>{window.humanOptions=options;options.callback('TOKEN');return 'widget';},reset:()=>window.humanOptions.callback('TOKEN')};
 const append=document.head.append.bind(document.head);
 document.head.append=element=>{if(element.tagName==='SCRIPT' && element.src.includes('turnstile')){setTimeout(()=>element.onload(),0);return;}append(element);};
}
(0,eval)(source);
CardenveilCatalogue.mount(document.querySelector('#catalogue'),characters,()=>'<div>Carte</div>');
document.querySelector('#guide-message').value='soin a distance';
await new Promise(r=>setTimeout(r,100));
document.querySelector('#guide-form').requestSubmit();
await new Promise(r=>setTimeout(r,150));
if(document.querySelectorAll('.guide-results article').length!==6)throw Error('Expected six suggestions');
if(document.querySelector('.guide-results img[src="x"],.guide-results img[onerror]'))throw Error('Unsafe explanation');
if(document.querySelectorAll('.guide-results .guide-portrait img').length!==4)throw Error('Missing recommendation portraits');
if(document.querySelectorAll('.guide-results .guide-portrait-empty').length!==2)throw Error('Missing portrait fallback');
const portrait=document.querySelector('.guide-portrait img');
if(!portrait.alt.includes('Hero 0') || !portrait.closest('a').href.endsWith('/personnages/hero-0/'))throw Error('Portrait accessibility or link');
if(!document.querySelector('.guide-results').textContent.includes('Correspond au soin'))throw Error('Missing comment');
fail=true;document.querySelector('#guide-form').requestSubmit();await new Promise(r=>setTimeout(r,150));
if(document.querySelector('#guide-form button').disabled)throw Error('Button remains disabled');
if(document.querySelectorAll('.guide-results article').length)throw Error('Stale results after failure');
document.querySelector('#result').textContent='PASS';
}catch(e){document.querySelector('#result').textContent='FAIL '+e.message;}})();</script>'''
    run_harness(tmp_path, harness.decode('utf-8').replace('PUBLIC_MODE', 'true' if provider == 'public' else 'false'))

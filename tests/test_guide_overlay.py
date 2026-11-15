"""Exercise the floating guide in Chromium, including a narrow viewport and keyboard focus."""
import pytest
from test_gemini_pages import run_harness


@pytest.mark.parametrize('language', ['fr', 'en'])
def test_guide_overlay(tmp_path, language):
    """The catalogue stays visible while both guides start closed and retain their forms."""
    harness = '''<!doctype html><html lang="LANG"><head><meta name="viewport" content="width=device-width">
<link rel="stylesheet" href="/web/public/styles.css"><link rel="stylesheet" href="/web/public/catalogue.css">
</head><body class="catalogue-home"><pre id="result">RUNNING</pre><main id="catalogue"></main>
<section class="rules-chat"><input id="rules-question" value="saved question"></section>
<script>
(async()=>{try{
const assert=(ok,message)=>{if(!ok)throw Error(message)};
const overlay=await (await fetch('/web/public/guide-overlay.js')).text();
const source=await (await fetch('CATALOGUE_SOURCE')).text();
window.fetch=async()=>({ok:true,headers:new Headers({'Content-Type':'application/json'}),json:async()=>({enabled:false,providers:[]})});
(0,eval)(overlay);(0,eval)(source);
const root=document.querySelector('#catalogue');
CardenveilCatalogue.mount(root,[{id:'camille',identity:{nom:'Camille',race:'Demi-Elfe'},catalog:{difficulty:4.5},capacities:[]}],()=>'<article>Camille</article>');
const dialog=root.querySelector('dialog'),launcher=root.querySelector('.guide-launcher');
assert(!dialog.open && launcher.getAttribute('aria-expanded')==='false','closed by default');
assert(!dialog.contains(root.querySelector('#grid')),'catalogue outside overlay');
assert(getComputedStyle(document.querySelector('.rules-chat')).display==='none','rules initially hidden');
launcher.click();assert(dialog.open && launcher.getAttribute('aria-expanded')==='true','open');
assert(dialog.contains(document.querySelector('.rules-chat')),'both guides inside overlay');
assert(dialog.contains(document.activeElement),'focus inside dialog');
root.querySelector('#guide-message').value='saved preference';
assert(dialog.getBoundingClientRect().width<=innerWidth,'responsive dialog');
root.querySelector('.guide-close').click();
await new Promise(r=>setTimeout(r,50));
assert(!dialog.open && document.activeElement===launcher,'close restores focus');
launcher.click();assert(root.querySelector('#guide-message').value==='saved preference','recommendation preserved');
assert(document.querySelector('#rules-question').value==='saved question','rules question preserved');
dialog.close();
root.querySelector('#search').value='Camille';root.querySelector('#search').dispatchEvent(new Event('input'));
assert(root.querySelectorAll('.character-link').length===1,'search still works');
document.querySelector('#result').textContent='PASS';
}catch(error){document.querySelector('#result').textContent='FAIL '+error.message;}})();
</script></body></html>'''
    source = '/web/public/catalogue.js' if language == 'fr' else '/web/i18n/en/catalogue.js'
    run_harness(tmp_path, harness.replace('LANG', language).replace('CATALOGUE_SOURCE', source),
                window_size='390,844')

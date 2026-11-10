"""Compile actual JS and exercise both editions in Chromium without Node tooling."""
import functools
import json
from pathlib import Path
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

ROOT = Path(__file__).resolve().parents[1]
BROWSER = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')


def browser_audit(tmp_path, javascript, directory=ROOT, budget=12000):
    if not BROWSER.exists():
        pytest.skip('Chromium unavailable')
    harness = ('<!doctype html><meta charset="utf-8"><pre id="result">RUNNING</pre><script>'
               '(async()=>{try{' + javascript + ';document.querySelector("#result").textContent="PASS";'
               '}catch(e){document.querySelector("#result").textContent="FAIL "+e.stack;}})();</script>').encode()

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == '/audit':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(harness)
            else:
                super().do_GET()

    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(directory)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        result = subprocess.run([str(BROWSER), '--headless', '--disable-gpu', '--no-first-run',
            f'--user-data-dir={tmp_path / "chrome"}', f'--virtual-time-budget={budget}', '--dump-dom',
            f'http://127.0.0.1:{server.server_port}/audit'], capture_output=True, encoding='utf-8', errors='replace', timeout=45,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        assert '<pre id="result">PASS</pre>' in result.stdout, result.stdout[-6000:] + result.stderr[-1000:]
    finally:
        server.shutdown()
        server.server_close()


def test_javascript_syntax_and_english_retrieval(tmp_path):
    paths = [*list((ROOT / 'web/public').glob('*.js')), *list((ROOT / 'functions/api').glob('*.js')),
             ROOT / 'web/rag-retrieval.js', *list((ROOT / 'web/i18n/en').glob('*.js'))]
    urls = ['/' + path.relative_to(ROOT).as_posix() for path in paths]
    browser_audit(tmp_path, '''
      for(const url of ''' + json.dumps(urls) + '''){
        let source=await (await fetch(url)).text();
        source=source.replace(/^import .*?;$/gm,'').replace(/\\bexport\\s+(?=(?:async\\s+)?(?:function|const|let|class))/g,'');
        try{new Function(source)}catch(e){throw Error(url+': '+e.message)}
      }
      const rag=await import('/web/rag-retrieval.js');
      const intent=rag.parseIntent('Strength at least 16, proficient in Knowledge, without fire, beginner');
      if(!intent.constraints.some(c=>c.stat==='force'&&c.value===16))throw Error('English numerical constraint');
      if(!intent.requiredSkills.includes('culture'))throw Error('English skill proficiency');
      if(!intent.excludedThemes.includes('feu'))throw Error('English exclusion');
      if(intent.maxDifficulty!==2)throw Error('English beginner filter');
    ''')


def test_published_english_pages_and_switch(tmp_path):
    public = ROOT / 'web/public'
    if not (public / 'en/data/characters.json').exists():
        pytest.skip('Complete the bilingual build first')
    browser_audit(tmp_path, '''
      localStorage.setItem('cardenveil-language','en');
      const frame=document.createElement('iframe');frame.style.width='390px';document.body.append(frame);
      const load=url=>new Promise((resolve,reject)=>{frame.onload=()=>resolve(frame.contentWindow);frame.src=url;});
      const until=async fn=>{for(let i=0;i<150;i++){if(fn())return;await new Promise(r=>setTimeout(r,50));}throw Error('Timed out');};
      let w=await load('/en/personnages/afreaux-shaufeois/?tab=skills#app');
      await until(()=>w.document.querySelector('#panel'));
      const d=w.document;
      if(d.documentElement.lang!=='en')throw Error('Wrong document language');
      if(!d.querySelector('#panel').textContent.includes('Sleight of Hand'))throw Error('Skill label missing');
      if(!d.querySelector('[data-language="fr"]').href.endsWith('/personnages/afreaux-shaufeois/?tab=skills#app'))throw Error('Switch lost context');
      for(const tab of ['abilities','inventory','narrative','progression']){
        d.querySelector('[data-tab="'+tab+'"]').click();
        if(!d.querySelector('#panel').textContent.trim())throw Error('Empty '+tab);
      }
      if(d.documentElement.scrollWidth>w.innerWidth+2)throw Error('Mobile character overflow');
      w=await load('/en/');await until(()=>w.document.querySelector('#search'));
      let search=w.document.querySelector('#search');search.value='zzzzmissing';search.dispatchEvent(new w.Event('input'));
      if(w.document.querySelector('.character-link'))throw Error('Stale search results');
      w.document.querySelector('#reset-search').click();
      const data=await (await fetch('/en/data/characters.json')).json();
      if(w.document.querySelectorAll('.character-link').length!==data.length)throw Error('Catalogue coverage');
      w.document.querySelector('[data-role="soin"]').click();
      if(!w.document.querySelector('.guide-results blockquote'))throw Error('English healing recommendations');
      w=await load('/en/regles/combat/');await until(()=>!w.document.querySelector('#rule-search').disabled);
      search=w.document.querySelector('#rule-search');search.value='parry';search.dispatchEvent(new w.Event('input'));
      await until(()=>w.document.querySelector('.search-result'));
      if(!w.document.querySelector('.search-result').href.includes('/en/regles/'))throw Error('French search link');
      if(w.document.documentElement.scrollWidth>w.innerWidth+2)throw Error('Mobile rules overflow');
      w=await load('/en/print.html?character=afreaux-shaufeois');await until(()=>w.document.body.dataset.ready||w.document.body.dataset.error);
      if(w.document.body.dataset.error)throw Error(w.document.body.dataset.error);
      if(!w.document.querySelector('#sheets').textContent.includes('Sleight of Hand'))throw Error('English print labels');
      if([...w.document.querySelectorAll('.page-content')].some(p=>p.scrollHeight>p.clientHeight+1))throw Error('Print overflow');
    ''', public, 30000)


def test_language_negotiation_respects_country_choice_and_deep_links(tmp_path):
    browser_audit(tmp_path, '''
      const source=await (await fetch('/web/public/language.js')).text();
      const run=async(path,saved,country,browser='en-US')=>{
        let redirected=null,calls=0;
        const location={pathname:path,search:'',hash:'',replace:value=>redirected=value};
        const storage={getItem:()=>saved,setItem:(_,value)=>saved=value};
        const execute=new Function('location','window','document','localStorage','navigator','fetch','AbortSignal',source);
        execute(location,{}, {addEventListener:()=>{}},storage,{languages:[browser]},
          async()=>{calls++;return {ok:true,headers:{get:()=> 'application/json'},json:async()=>({language:country})}},AbortSignal);
        await new Promise(resolve=>setTimeout(resolve,10));
        return {redirected,calls};
      };
      if((await run('/',null,'en')).redirected!=='/en/')throw Error('Country EN');
      if((await run('/',null,'fr')).redirected!==null)throw Error('Country FR');
      if((await run('/','fr','en')).redirected!==null)throw Error('Explicit French preference');
      if((await run('/','en','fr')).redirected!=='/en/')throw Error('Explicit English preference');
      if((await run('/',null,null,'fr-FR')).redirected!==null)throw Error('Browser fallback');
      for(const path of ['/en/','/regles/combat/','/en/personnages/mimyr/']){
        const result=await run(path,'en','en');
        if(result.redirected||result.calls)throw Error('Deep link language changed');
      }
      const endpoint=await import('/functions/api/locale.js');
      for(const [country,expected] of [['FR','fr'],['BE','fr'],['US','en'],['JP','en']]){
        const result=await endpoint.onRequestGet({request:{cf:{country}}});
        if((await result.json()).language!==expected)throw Error('Country mapping '+country);
      }
    ''')

"""Run Pages modules in Chromium with fake Google, Turnstile and asset bindings."""

import functools
import shutil
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = '''<pre id="result">RUNNING</pre><script type="module">
import {candidatesFrom,validateRecommendations} from '/web/recommendations-core.js';
import {onRequestPost} from '/functions/api/recommendations.js';
import {onRequestGet} from '/functions/api/recommendation-config.js';
try {
 const assert=(value,label)=>{if(!value)throw Error(label);};
 const characters=[{id:'hero',identity:{nom:'Hero'},catalog:{gameplaySummary:'Soigne les allies a distance.'}}];
 const index={version:'test-index',model:'gemini-embedding-001',dimensions:2,embeddedDocuments:0,
   characters:[{id:'hero',name:'Hero',race:'Nain',stats:{force:8,agilite:14,esprit:18,social:12},difficulty:2,classes:[]}],
   documents:[{id:'hero:capacity-1',characterId:'hero',title:'Soin',text:'Soigne les allies a distance.'}]};
 const candidates=candidatesFrom(characters);
 const result={explanation:'Un personnage de soin.',matches:[{character_id:'hero',comment:'Il soigne a distance comme demande.',evidence:'Soigne les allies'}]};
 const apiResult={explanation:result.explanation,matches:[{character_id:'hero',comment:result.matches[0].comment,source_id:'hero:capacity-1'}]};
 assert(validateRecommendations(result,candidates).matches.length===1,'valid result');
 for(const invalid of [
  {...result,matches:[{...result.matches[0],character_id:'fake'}]},
  {...result,matches:[...result.matches,...result.matches]},
  {...result,matches:[{...result.matches[0],evidence:'Invented power'}]},
  {...result,matches:Array(7).fill(result.matches[0])}
 ]){let rejected=false;try{validateRecommendations(invalid,candidates);}catch{rejected=true;}assert(rejected,'reject invalid response');}
 const env={GEMINI_API_KEY:'FAKE_SECRET',TURNSTILE_SECRET_KEY:'FAKE_TURNSTILE',TURNSTILE_SITE_KEY:'PUBLIC',GEMINI_FREE_TIER_CONFIRMED:'1',
  ASSETS:{fetch:async()=>Response.json(index)}};
 const config=await onRequestGet({env}).json();assert(config.enabled && !JSON.stringify(config).includes('FAKE'),'public config');
 assert(!(await onRequestGet({env:{}}).json()).enabled,'disabled by default');
 let mode='ok',googleCalls=0,turnstileCalls=0,embeddingCalls=0,cached=null;
 caches.default={match:async()=>cached,put:async(key,value)=>{cached=value;}};
 window.fetch=async(url,options)=>{
  if(url.includes('siteverify')){turnstileCalls++;return Response.json({
    success:!['bot','secret','expired'].includes(mode),
    hostname:mode==='hostname'?'other.invalid':location.hostname,
    action:mode==='action'?'wrong':'recommend',
    'error-codes':mode==='secret'?['invalid-input-secret']:mode==='expired'?['timeout-or-duplicate']:['invalid-input-response']
  },{status:mode==='secret'?400:200});}
  if(url.includes(':embedContent')){embeddingCalls++;
    const payload=JSON.parse(options.body);assert(payload.taskType==='RETRIEVAL_QUERY','retrieval query task');
    if(mode==='embedding-failure')return new Response('{}',{status:429});
    return Response.json({embedding:{values:[1,0]}});
  }
  googleCalls++;const body=JSON.parse(options.body);
  assert(options.headers['x-goog-api-key']==='FAKE_SECRET','secret only in server request');
  assert(!body.tools && body.generationConfig.maxOutputTokens===2300,'bounded request');
  if(mode==='quota')return new Response('{}',{status:429});
  if(mode==='bad')return Response.json({candidates:[{finishReason:'STOP',content:{parts:[{text:JSON.stringify({...apiResult,matches:[{...apiResult.matches[0],character_id:'fake'}]})}]}}]});
  return Response.json({candidates:[{finishReason:'STOP',content:{parts:[{text:JSON.stringify(apiResult)}]}}]});
 };
 const request=(body={message:'Je veux soigner',token:'TOKEN'},origin=location.origin)=>({url:location.origin+'/api/recommendations',
  headers:new Headers({'Origin':origin,'Content-Type':'application/json','X-Cardenveil-Client':'catalogue'}),body:new Response(JSON.stringify(body)).body});
 const call=(req=request(),bindings=env)=>onRequestPost({request:req,env:bindings,waitUntil:p=>p});
 assert((await call(request(undefined,'https://other.invalid'))).status===403,'reject foreign origin');
 assert((await call(request(),{})).status===503,'missing secrets');
 assert((await call(request({message:'x'.repeat(5000),token:'TOKEN'}))).status===400,'bounded body');
 mode='bot';assert((await call()).status===403 && googleCalls===0,'bot spends no quota');
 mode='ok';const good=await call();assert(good.status===200 && googleCalls===1,'one google call');
 assert((await good.json()).matches.length===1,'response shape');
 const hit=await call();assert(hit.status===200 && googleCalls===1 && turnstileCalls===3,'verified cache hit');
 for(const [value,status,code] of [['secret',503,'turnstile_secret_invalid'],['expired',403,'turnstile_token_expired'],['hostname',403,'turnstile_hostname_mismatch'],['action',403,'turnstile_action_mismatch']]){
   mode=value;const response=await call();assert(response.status===status && (await response.json()).code===code && googleCalls===1,'safe diagnostic '+value);
 }
 cached=null;mode='quota';assert((await call()).status===429 && googleCalls===2,'quota no retries');
 mode='bad';const bad=await call();assert(bad.status===503 && googleCalls===3,'reject invented character');
 assert(!(await bad.text()).includes('FAKE'),'no secret in failure');
 cached=null;mode='ok';index.embeddedDocuments=1;index.documents[0].vector={data:'fwA=',norm:127};index.version='embedded';
 const semantic=await call();const payload=await semantic.json();
 assert(semantic.status===200 && payload.retrieval.mode==='stats+embeddings+bm25' && embeddingCalls===1 && googleCalls===4,'one embedding plus one explanation');
 assert(payload.matches[0].stats.esprit===18 && payload.matches[0].sources[0].id==='hero:capacity-1','numerical evidence and provenance');
 cached=null;mode='embedding-failure';const fallback=await call();
 assert(fallback.status===200 && (await fallback.json()).retrieval.mode==='stats+bm25' && embeddingCalls===2 && googleCalls===5,'honest lexical fallback without retries');
 cached=null;const identity=await call(request({message:'nains',token:'TOKEN'}));const direct=await identity.json();
 assert(identity.status===200 && direct.matches.length===1 && direct.matches[0].race==='Nain' && direct.retrieval.mode==='structured-identity','race filter preserves matching sheet');
 assert(embeddingCalls===2 && googleCalls===5,'identity-only search spends no Google quota');
 document.querySelector('#result').textContent='PASS';
} catch(error){document.querySelector('#result').textContent='FAIL '+error.message;}
</script>'''


def run_harness(tmp_path, harness):
    """Run a repository-hosted browser harness without creating any public test assets."""
    browser = next((str(p) for p in [Path('C:/Program Files/Google/Chrome/Application/chrome.exe')]
                    if p.is_file()), shutil.which('chromium'))
    if not browser:
        pytest.skip('Chromium required')

    class Handler(SimpleHTTPRequestHandler):
        """Serve ES modules from the repository for the isolated browser test."""
        def do_GET(self):
            """Expose an in-memory test page and local module source files."""
            if self.path != '/audit':
                return super().do_GET()
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(harness.encode('utf-8'))

    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        result=subprocess.run([browser,'--headless','--disable-gpu','--no-first-run',
            f'--user-data-dir={tmp_path / "browser"}','--virtual-time-budget=10000','--dump-dom',
            f'http://127.0.0.1:{server.server_port}/audit'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
        assert '<pre id="result">PASS</pre>' in result.stdout, result.stdout[:2500]
        return result.stdout
    finally:
        server.shutdown()
        server.server_close()


def test_pages_recommendations(tmp_path):
    """Check safe defaults, validation, anti-abuse, quotas and cache without real API calls."""
    run_harness(tmp_path, HARNESS)

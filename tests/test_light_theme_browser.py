"""Verify the optional white theme, semantic stat colors and responsive core journeys."""

import functools
import shutil
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = '''<meta charset="utf-8"><pre id="result">RUNNING</pre><script>
const colors={force:'rgb(180, 35, 50)',agilite:'rgb(24, 118, 71)',esprit:'rgb(36, 91, 193)',social:'rgb(117, 65, 167)'};
const assert=(condition,message)=>{if(!condition)throw Error(message);};
const luminance=rgb=>{const c=rgb.match(/[\\d.]+/g).slice(0,3).map(x=>{const n=+x/255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4;});return .2126*c[0]+.7152*c[1]+.0722*c[2];};
const contrast=(a,b)=>{const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
(async()=>{try{
  for(const route of ['/', '/personnages/garreth/', '/statistiques/', '/regles/']){
    const frame=document.createElement('iframe');frame.style.width='WIDTHpx';frame.style.height='900px';
    const loaded=new Promise(resolve=>frame.onload=resolve);frame.src=route;document.body.append(frame);await loaded;
    const w=frame.contentWindow,d=w.document;
    if(route==='/')for(let i=0;i<100&&!d.querySelector('.card-stats');i++)await new Promise(r=>setTimeout(r,50));
    assert(w.getComputedStyle(d.body).backgroundColor==='rgb(255, 255, 255)',route+' white background');
    assert(w.getComputedStyle(d.documentElement).colorScheme==='light',route+' native controls');
    assert(d.documentElement.scrollWidth<=w.innerWidth+1,route+' horizontal overflow');
    if(route==='/'){
      assert(d.querySelectorAll('.character-link').length===68,'Full catalogue');
      for(const [key,color] of Object.entries(colors)){
        const tile=d.querySelector('.card-stats [data-stat="'+key+'"]'),value=tile.querySelector('strong');
        assert(w.getComputedStyle(value).color===color,'Catalogue stat color '+key);
        assert(contrast(color,w.getComputedStyle(tile).backgroundColor)>=4.5,'Readable stat contrast '+key);
      }
      const search=d.querySelector('#search');search.value='Garreth';search.dispatchEvent(new w.Event('input'));
      assert(d.querySelectorAll('.character-link').length===1,'Search still works');
      d.querySelector('#reset-search').click();assert(d.querySelectorAll('.character-link').length===68,'Reset still works');
      d.querySelector('[data-role="soin"]').click();assert(d.querySelector('.guide-results article'),'Guide still works');
      assert(w.getComputedStyle(d.querySelector('.guide-results article')).backgroundColor==='rgb(255, 255, 255)','White recommendations');
    }
    if(route.includes('/personnages/')){
      for(const [key,color] of Object.entries(colors))assert(w.getComputedStyle(d.querySelector('.detail-stats [data-stat="'+key+'"] strong')).color===color,'Sheet stat color '+key);
      d.querySelector('[data-tab="skills"]').click();
      [...d.querySelectorAll('.skill-group h3')].forEach((heading,i)=>assert(w.getComputedStyle(heading).color===Object.values(colors)[i],'Skill group color'));
    }
    if(route==='/statistiques/')for(const [key,color] of Object.entries(colors)){
      assert(w.getComputedStyle(d.querySelector('.stat-histograms [data-stat="'+key+'"] .bar-track span')).backgroundColor===color,'Dashboard stat color '+key);
    }
    frame.remove();
  }
  document.querySelector('#result').textContent='PASS';
}catch(e){document.querySelector('#result').textContent='FAIL '+e.message;}})();</script>'''


@pytest.mark.parametrize("width", [390, 1280])
def test_light_theme_core_routes(tmp_path, width):
    """Check real generated pages without contacting Gemini or spending external quota."""
    browser = next((str(p) for p in [Path('C:/Program Files/Google/Chrome/Application/chrome.exe')] if p.is_file()), shutil.which('chromium'))
    if not browser:
        pytest.skip('Chromium required')

    class Handler(SimpleHTTPRequestHandler):
        """Serve public pages with a synthetic audit and disabled external AI providers."""

        def do_GET(self):
            """Keep all requests local, including recommendation configuration checks."""
            if self.path == '/theme-audit':
                body = AUDIT.replace('WIDTH', str(width)).encode('utf-8')
                content_type = 'text/html; charset=utf-8'
            elif self.path.startswith('/api/'):
                body = b'{"enabled":false,"providers":[]}'
                content_type = 'application/json'
            else:
                return super().do_GET()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT / 'web/public')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        result = subprocess.run([browser, '--headless', '--disable-gpu', '--no-first-run',
                                 f'--user-data-dir={tmp_path / "browser"}', '--virtual-time-budget=15000', '--dump-dom',
                                 f'http://127.0.0.1:{server.server_port}/theme-audit'],
                                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        assert '<pre id="result">PASS</pre>' in result.stdout, result.stdout[:3000]
    finally:
        server.shutdown()
        server.server_close()

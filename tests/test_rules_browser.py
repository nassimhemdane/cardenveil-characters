"""Check optional rules search and mobile layout in a real Chromium browser."""

import functools
import shutil
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = b"""<pre id="result">RUNNING</pre><iframe style="width:390px" src="/regles/"></iframe>
<script>document.querySelector('iframe').onload=async function(){try{
this.onload=null;
const w=this.contentWindow,d=w.document,s=d.querySelector('#rule-search');
for(let i=0;i<100&&s.disabled;i++)await new Promise(r=>setTimeout(r,50));
if(s.disabled)throw Error('Search did not initialize');
if(d.documentElement.scrollWidth>w.innerWidth+1)throw Error('Mobile horizontal overflow');
if(d.querySelector('.docs-nav details').open)throw Error('Mobile menu should be collapsed');
if(d.querySelector('.docs-toc,.mobile-toc'))throw Error('Duplicate contents still present');
const outer=d.querySelector('.docs-nav details');outer.open=true;
if(d.querySelectorAll('.chapter-navigation').length!==8)throw Error('Some chapters have no subsections');
for(const summary of d.querySelectorAll('.chapter-navigation>summary')){
  if(w.getComputedStyle(summary).display!=='flex')throw Error('Chapter arrow alignment layout');
  if(w.getComputedStyle(summary.querySelector('.chapter-heading')).display!=='flex')throw Error('Missing shared arrow/title row');
  const caret=summary.querySelector('.chapter-caret').getBoundingClientRect(),label=summary.querySelector('a').getBoundingClientRect();
  if(Math.abs(caret.top+caret.height/2-label.top-label.height/2)>1)throw Error('Chapter arrow and title on different lines');
  if(label.left-caret.right>8)throw Error('Arrow not directly beside title');
}
outer.open=false;
s.value='parade';s.dispatchEvent(new w.Event('input'));
await new Promise(r=>setTimeout(r,350));
if(!d.querySelector('.search-result'))throw Error('Missing search results');
if(!d.querySelector('.search-result mark'))throw Error('Missing search highlighting');
d.querySelector('#clear-search').click();
if(s.value||d.querySelector('.search-result'))throw Error('Clear search failed');
if(d.querySelector('#reading-theme,#reading-size,.reading-tools,.source-cite'))throw Error('Removed controls still visible');
s.value='zzzinexistantzz';s.dispatchEvent(new w.Event('input'));
await new Promise(r=>setTimeout(r,350));
if(d.querySelector('.search-result'))throw Error('Stale results');
const frame=this;
await new Promise(resolve=>{frame.onload=resolve;w.location.href='/regles/combat/';});
frame.onload=null;
const chapter=frame.contentDocument,win=frame.contentWindow;
for(let i=0;i<100&&chapter.querySelector('#rule-search').disabled;i++)
await new Promise(r=>setTimeout(r,50));
if(chapter.querySelector('#reading-theme,#reading-size,.reading-tools,.source-cite,.original-page'))throw Error('Removed chapter controls still visible');
if(chapter.documentElement.scrollWidth>win.innerWidth+1)throw Error('Chapter overflow');
if(chapter.querySelector('.docs-toc,.mobile-toc'))throw Error('Duplicate chapter contents');
const combatNav=chapter.querySelector('.chapter-navigation[data-chapter="combat"]');
if(!combatNav||!combatNav.open)throw Error('Missing expanded combat categories');
const actionLink=[...combatNav.querySelectorAll('a')].find(a=>a.textContent==='Actions en combat');
if(!actionLink||!chapter.querySelector(new URL(actionLink.href).hash))throw Error('Broken actions category');
if(combatNav.querySelectorAll('.chapter-sections>li').length<10)throw Error('Missing combat categories');
if(combatNav.querySelectorAll('.chapter-subsections a').length<5)throw Error('Missing combat subsections');
await new Promise(resolve=>{frame.onload=resolve;win.location.href='/regles/races/';});
frame.onload=null;
const races=frame.contentDocument,view=frame.contentWindow;
if(races.querySelectorAll('.race-card').length!==26)throw Error('Missing races');
if(races.querySelectorAll('.race-art img').length!==25)throw Error('Missing race art');
if(races.documentElement.scrollWidth>view.innerWidth+1)throw Error('Race gallery overflow');
const raceSearch=races.querySelector('#race-search');raceSearch.value='nain';raceSearch.dispatchEvent(new view.Event('input'));
if(races.querySelectorAll('.race-card:not([hidden])').length!==1)throw Error('Race filter failed');
document.querySelector('#result').textContent='PASS';
}catch(e){document.querySelector('#result').textContent=e.message}}</script>"""


def test_rules_browser(tmp_path):
    """Search works without external services and the narrow layout stays within the screen."""
    browser = next(
        (
            str(p)
            for p in [
                Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
            ]
            if p.is_file()
        ),
        shutil.which("chromium"),
    )
    if not browser or not (ROOT / "web/public/regles/index.html").is_file():
        pytest.skip("Build the site and install Chromium for the browser check")

    class Handler(SimpleHTTPRequestHandler):
        """Serve an isolated browser harness alongside the generated library."""

        def do_GET(self):
            """Serve the in-memory harness without adding test files to production."""
            if self.path != "/audit":
                return super().do_GET()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(AUDIT)

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Handler, directory=str(ROOT / "web/public"))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        result = subprocess.run(
            [
                browser,
                "--headless",
                "--disable-gpu",
                "--no-first-run",
                f"--user-data-dir={tmp_path / 'browser'}",
                "--virtual-time-budget=15000",
                "--dump-dom",
                f"http://127.0.0.1:{server.server_port}/audit",
            ],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        assert '<pre id="result">PASS</pre>' in result.stdout, result.stdout[-3000:]
    finally:
        server.shutdown()
        server.server_close()

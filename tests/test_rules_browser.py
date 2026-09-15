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
const w=this.contentWindow,d=w.document,s=d.querySelector('#rule-search');
for(let i=0;i<100&&s.disabled;i++)await new Promise(r=>setTimeout(r,50));
if(s.disabled)throw Error('Search did not initialize');
if(d.documentElement.scrollWidth>w.innerWidth+1)throw Error('Mobile horizontal overflow');
if(d.querySelector('.docs-nav details').open)throw Error('Mobile menu should be collapsed');
s.value='parade';s.dispatchEvent(new w.Event('input'));
await new Promise(r=>setTimeout(r,350));
if(!d.querySelector('.search-result'))throw Error('Missing search results');
s.value='zzzinexistantzz';s.dispatchEvent(new w.Event('input'));
await new Promise(r=>setTimeout(r,350));
if(d.querySelector('.search-result'))throw Error('Stale results');
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

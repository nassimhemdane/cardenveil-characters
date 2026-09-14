"""Integration checks for physical HTML pagination in an installed Chromium browser."""

import functools
import html
import json
import re
import shutil
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_all_printable_sheets_in_browser(tmp_path):
    """Check every built sheet plus a long rich-text continuation without a cloud service."""
    browser = next(
        (
            str(path)
            for path in (
                Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
            )
            if path.is_file()
        ),
        shutil.which("chromium") or shutil.which("google-chrome"),
    )
    if not browser or not (ROOT / "web/public/data/characters.json").is_file():
        pytest.skip("Build the catalogue and install Chromium to audit printable sheets")

    class Handler(SimpleHTTPRequestHandler):
        """Serve the built site and an in-memory audit page from the same local origin."""

        def do_GET(self):
            """Route the audit assets without adding them to the production directory."""
            if self.path == "/audit":
                body = (
                    b'<meta charset="utf-8"><pre id="result">RUNNING</pre>'
                    b'<iframe src="/print.html?audit=1" style="width:900px;height:1200px">'
                    b'</iframe><script src="/audit.js"></script>'
                )
            elif self.path == "/audit.js":
                body = (ROOT / "tests/print-browser-audit.js").read_bytes()
            else:
                return super().do_GET()
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/javascript" if self.path.endswith(".js") else "text/html; charset=utf-8",
            )
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            """Keep request noise out of the test report."""

    handler = functools.partial(Handler, directory=str(ROOT / "web/public"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = subprocess.run(
            [
                browser,
                "--headless",
                "--disable-gpu",
                "--no-first-run",
                f"--user-data-dir={tmp_path / 'browser'}",
                "--virtual-time-budget=120000",
                "--dump-dom",
                f"http://127.0.0.1:{server.server_port}/audit",
            ],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
    finally:
        server.shutdown()
        server.server_close()
    match = re.search(r'<pre id="result">(.*?)</pre>', result.stdout, re.S)
    assert match and match[1] != "RUNNING", result.stderr[-2000:]
    rows = json.loads(html.unescape(match[1]))
    assert len(rows) == len(list((ROOT / "Final").glob("*.zip"))) + 1
    for row in rows:
        assert "error" not in row, row
        assert not row["missing"], row
        assert not row["missingImages"], row
        assert row["horizontal"] == 0, row
        assert row["inventoryPage"] in (-1, 2), row
        if row["id"] != "continuation-test":
            assert 2 <= row["pages"] <= 4, row

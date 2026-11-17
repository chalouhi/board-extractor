#!/usr/bin/env python3
"""The example board: a tiny service with made-up cards, the extractor inside it, and a page drawn by the
Board Generator 1.1. Everything stays on this machine.

    python3 example/serve.py [--port 8400] [--db <file>]     start it, then open http://127.0.0.1:8400/
    python3 example/reset.py [--db <file>]                   put it back to the sample

The service keeps its cards in a small database file (example/shop.db), made at the first start.
"""

import argparse
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from board_extractor import ExtractorError, board_file, card_file  # noqa: E402
from store import DEFAULT_DB, Store  # noqa: E402

TODAY = "2026-03-10"  # the made-up cards' own day
POLICY = ("default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; connect-src 'self'; "
          "img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
FILES = {
    "/": ("page.html", "text/html; charset=utf-8"),
    "/page.js": ("page.js", "text/javascript; charset=utf-8"),
    "/page.css": ("page.css", "text/css; charset=utf-8"),
    "/board-generator/board.js": ("../vendor/board-generator/src/board.js", "text/javascript; charset=utf-8"),
    "/fonts/Carlito-Regular.ttf": ("../vendor/board-generator/fonts/Carlito-Regular.ttf", "font/ttf"),
    "/fonts/Carlito-Bold.ttf": ("../vendor/board-generator/fonts/Carlito-Bold.ttf", "font/ttf"),
}
CARD = re.compile(r"/api/cards/([^/]{1,40})")
ACTION = re.compile(r"/api/cards/([^/]{1,40})/([a-z-]{1,20})")

with open(os.path.join(HERE, "settings.json"), encoding="utf-8") as f:
    SETTINGS = json.load(f)


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        server_version = "board-extractor-example"
        sys_version = ""

        def log_message(self, fmt, *args):
            pass

        def _send(self, status, body, ctype="application/json; charset=utf-8"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Security-Policy", POLICY)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _error(self, status, message):
            self._send(status, json.dumps({"error": message}))

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            from urllib.parse import unquote
            if path in FILES:
                name, ctype = FILES[path]
                with open(os.path.normpath(os.path.join(HERE, name)), "rb") as f:
                    return self._send(200, f.read(), ctype)
            try:
                if path == "/api/board":
                    return self._send(200, board_file(SETTINGS, store.records(), today=TODAY))
                m = CARD.fullmatch(path)
                if m:
                    r = store.record(unquote(m.group(1)))
                    if r is None:
                        return self._error(404, "There is no such card.")
                    return self._send(200, card_file(SETTINGS, r))
            except ExtractorError as e:
                return self._error(500, "\n".join(e.problems))
            self._error(404, "Not found.")

        def do_POST(self):
            from urllib.parse import unquote
            m = ACTION.fullmatch(self.path)
            if not m:
                return self._error(404, "Not found.")
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{self.headers.get('Host')}":
                return self._error(403, "Only the example's own page can press its buttons.")
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(min(n, 65536)) or b"{}")
            except ValueError:
                return self._error(400, "The request is not JSON.")
            text = body.get("text") if isinstance(body, dict) else None
            status, answer = store.act(unquote(m.group(1)), m.group(2), text)
            if status != 200:
                return self._error(status, answer)
            self._send(200, json.dumps({"answer": answer}))

    return Handler


def serve(port=8400, db=DEFAULT_DB, host="127.0.0.1"):
    """Starts the example and returns the server (call serve_forever on it)."""
    return ThreadingHTTPServer((host, port), make_handler(Store(db)))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Start the example board on this machine.")
    ap.add_argument("--port", type=int, default=8400, help="the port (default 8400)")
    ap.add_argument("--db", default=DEFAULT_DB, help="the database file (default example/shop.db)")
    a = ap.parse_args(argv)
    httpd = serve(a.port, a.db)
    print(f"The example board is at http://127.0.0.1:{httpd.server_address[1]}/  (Ctrl+C stops it)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

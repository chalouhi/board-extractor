"""The example board's service: requirements 25 to 28 and scenario 3, through its own API.
The page itself is tested in a browser by tests/browser/example.test.js."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from helpers import ROOT, path, text

sys.path.insert(0, path("example"))
import serve  # noqa: E402


class Example(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "shop.db")
        self.start()

    def tearDown(self):
        self.stop()
        self.tmp.cleanup()

    def start(self):
        self.httpd = serve.serve(0, self.db)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def get(self, p):
        with urllib.request.urlopen(self.url + p) as r:
            return r.status, r.headers, r.read().decode("utf-8", "replace")

    def post(self, p, body, headers=None):
        req = urllib.request.Request(self.url + p, data=json.dumps(body).encode(), method="POST",
                                     headers=dict({"Content-Type": "application/json"}, **(headers or {})))
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def board(self):
        b = json.loads(self.get("/api/board")[2])
        cols = {c["name"]: c for c in b["columns"]}
        drawn = {n: [c["id"] for c in b["cards"] if c["column"] == n and not c.get("in_strip")] for n in cols}
        return b, cols, drawn

    def card(self, cid):
        return json.loads(self.get(f"/api/cards/{cid}")[2])

    def test_scenario_3(self):
        b, cols, drawn = self.board()
        self.assertEqual(b["title"], "Shop relaunch")
        self.assertEqual([c["id"] for c in b["cards"] if c.get("in_strip")], ["41", "38"])
        self.assertEqual((len(drawn["Doing"]), cols["Doing"]["limit"]), (3, 2))  # "3 / 2", in red
        self.assertEqual((cols["Done"]["total"], cols["Done"]["show"], len(drawn["Done"])), (48, 3, 3))  # "45 more"
        c = self.card("43")
        self.assertEqual(c["column"], "Checking")
        self.assertEqual([x["done"] for x in c["sections"][0]["items"]], [True, True, False])  # "2 of 3 done"
        self.assertEqual([(s["title"], len(s["items"])) for s in c["sections"]],
                         [("Requirements", 3), ("Notes", 2), ("History", 6)])
        self.assertEqual([x["name"] for x in c["buttons"]], ["Accept", "Send back", "Add note"])

        self.assertEqual(self.post("/api/cards/43/send-back", {"text": "Closing time wraps on a phone"}), (200, {"answer": ""}))
        b, cols, drawn = self.board()
        self.assertEqual(drawn["Ready"], ["47", "48", "49", "43"])  # "4 / 4"
        self.assertEqual(drawn["Checking"], [])  # "0": card 38 is in the strip
        notes = self.card("43")["sections"][1]["items"]
        self.assertEqual(len(notes), 3)
        self.assertEqual(notes[0]["text"], "Closing time wraps on a phone")

        self.stop()
        self.start()
        self.assertEqual(self.card("43")["column"], "Ready")
        r = subprocess.run([sys.executable, path("example", "reset.py"), "--db", self.db], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.card("43")["column"], "Checking")
        self.assertEqual(len(self.card("43")["sections"][1]["items"]), 2)

    def test_accept_and_add_note(self):
        self.assertEqual(self.post("/api/cards/38/accept", {}), (200, {"answer": ""}))
        b, cols, drawn = self.board()
        self.assertEqual(drawn["Done"], ["38", "40", "39"])
        self.assertEqual(cols["Done"]["total"], 49)
        self.assertNotIn("38", [c["id"] for c in b["cards"] if c.get("in_strip")])
        self.assertEqual(self.post("/api/cards/44/note", {"text": "  Payment page looks right  "}),
                         (200, {"answer": "keep open"}))
        self.assertEqual(self.card("44")["sections"][0]["items"][0]["text"], "Payment page looks right")

    def test_refused(self):
        self.assertEqual(self.post("/api/cards/99/note", {"text": "x"})[0], 404)
        self.assertEqual(self.post("/api/cards/44/accept", {})[0], 409)  # not in Checking
        self.assertEqual(self.post("/api/cards/43/send-back", {"text": "   "})[0], 400)
        self.assertEqual(self.post("/api/cards/43/accept", {}, {"Origin": "https://example.com"})[0], 403)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.get("/api/cards/99")
        self.assertEqual(e.exception.code, 404)
        self.assertEqual(self.card("43")["column"], "Checking")

    def test_the_page(self):
        status, headers, html = self.get("/")
        self.assertIn("connect-src 'self'", headers["Content-Security-Policy"])
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertIn("An example with made-up cards", html)
        for p in ("/page.js", "/page.css", "/board-generator/board.js", "/fonts/Carlito-Regular.ttf"):
            self.assertEqual(self.get(p)[0], 200)
        self.assertEqual(self.get("/board-generator/board.js")[2],
                         text("vendor", "board-generator", "src", "board.js"))

    def test_listens_on_this_machine_only(self):
        self.assertEqual(self.httpd.server_address[0], "127.0.0.1")
        self.assertTrue(os.path.exists(self.db))
        self.assertFalse(os.path.exists(os.path.join(ROOT, "example", "shop.db.tmp")))


if __name__ == "__main__":
    unittest.main()

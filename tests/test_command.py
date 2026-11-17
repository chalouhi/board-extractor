"""The command: requirements 22 to 24, scenarios 1 and 4."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

from helpers import ROOT, lines, load, path


def run(*args, cwd=ROOT):
    return subprocess.run([sys.executable, "-m", "board_extractor", *args], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8")


SETTINGS = path("samples", "shop", "settings.json")
RECORDS = path("samples", "shop", "records.json")
RECORD = path("samples", "shop", "card-43.record.json")


class Command(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_scenario_1(self):
        board, card = os.path.join(self.dir, "board.json"), os.path.join(self.dir, "card.json")
        r = run(SETTINGS, RECORDS, "--today", "2026-03-10", "--out", board)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
        with open(board, encoding="utf-8") as f:
            self.assertEqual(json.load(f), load("expected", "shop.board.json"))
        r = run(SETTINGS, RECORD, "--out", card)
        self.assertEqual(r.returncode, 0)
        with open(card, encoding="utf-8") as f:
            self.assertEqual(json.load(f), load("expected", "shop.card-43.json"))
        self.assertEqual(sorted(os.listdir(self.dir)), ["board.json", "card.json"])

    def test_prints_when_no_place_is_named(self):
        r = run(SETTINGS, RECORDS, "--today", "2026-03-10")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout), load("expected", "shop.board.json"))
        r = run(SETTINGS, RECORD, "--out", "-")
        self.assertEqual(json.loads(r.stdout), load("expected", "shop.card-43.json"))

    def test_filters(self):
        r = run(SETTINGS, RECORDS, "--group", "Website")
        self.assertEqual([c["id"] for c in json.loads(r.stdout)["cards"]], ["38", "52", "48", "44", "45", "43", "40"])
        r = run(SETTINGS, RECORDS, "--waiting")
        self.assertEqual([c["id"] for c in json.loads(r.stdout)["cards"]], ["41", "38"])
        r = run(SETTINGS, RECORDS, "--kind", "Fix", "--group", "Website")
        self.assertEqual([c["id"] for c in json.loads(r.stdout)["cards"]], ["38", "45", "43"])

    def test_scenario_4(self):
        out = os.path.join(self.dir, "board.json")
        r = run(path("samples", "broken", "settings.json"), path("samples", "broken", "records.json"), "--out", out)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.stderr.splitlines(), lines("expected", "broken.problems.txt"))
        self.assertEqual(os.listdir(self.dir), [])

    def test_a_file_already_there_is_left_alone_on_a_problem(self):
        out = os.path.join(self.dir, "board.json")
        with open(out, "w") as f:
            f.write("before")
        r = run(SETTINGS, RECORDS, "--today", "10 March", "--out", out)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stderr.splitlines(), ['Today: "10 March" is not a date; a date is written YYYY-MM-DD.'])
        with open(out) as f:
            self.assertEqual(f.read(), "before")
        self.assertEqual(os.listdir(self.dir), ["board.json"])

    def test_used_wrongly(self):
        for args in ([], [SETTINGS], [SETTINGS, RECORDS, RECORD], [SETTINGS, RECORDS, "--colour", "red"],
                     [SETTINGS, RECORDS, "--today"], [SETTINGS, os.path.join(self.dir, "missing.json")],
                     [SETTINGS, RECORD, "--waiting"], [SETTINGS, RECORDS, "--out", self.dir]):
            r = run(*args)
            self.assertEqual(r.returncode, 2, args)
            self.assertEqual(r.stdout, "")
            self.assertTrue(r.stderr.startswith("board-extractor: "), r.stderr)
        self.assertEqual(os.listdir(self.dir), [])

    def test_help_and_version(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Usage: board-extractor", r.stdout)
        r = run("--version")
        self.assertEqual(r.stdout.strip(), "1.0.0")

    def test_from_a_copy_with_no_install_step(self):
        r = subprocess.run([sys.executable, path("bin", "board-extractor"), SETTINGS, RECORDS, "--today", "2026-03-10"],
                           cwd=self.dir, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), load("expected", "shop.board.json"))


if __name__ == "__main__":
    unittest.main()

"""The part, inside a Python program: requirements 1 to 21, scenarios 1, 2 and 4."""

import copy
import json
import random
import sys
import time
import unittest

from helpers import load, lines, settings, text

from board_extractor import ExtractorError, MAX_RECORDS, board_file, card_file

SHOP = load("samples", "shop", "settings.json")
RECORDS = load("samples", "shop", "records.json")
CARD43 = load("samples", "shop", "card-43.record.json")


def ids(board_text):
    return [c["id"] for c in json.loads(board_text)["cards"]]


def problems(fn, *a, **k):
    try:
        fn(*a, **k)
    except ExtractorError as e:
        return e.problems
    raise AssertionError("no problem was reported")


class Scenario1(unittest.TestCase):
    """Records in, the expected board file and card file out (requirements 1, 2, 4)."""

    def setUp(self):
        self.board = json.loads(board_file(SHOP, RECORDS, today="2026-03-10"))

    def test_board_file_equals_the_expected_one(self):
        self.assertEqual(self.board, load("expected", "shop.board.json"))

    def test_fourteen_cards_in_order(self):
        self.assertEqual([c["id"] for c in self.board["cards"]], "41 38 52 53 47 48 49 44 45 46 43 40 39 37".split())

    def test_what_the_scenario_sees(self):
        cards = {c["id"]: c for c in self.board["cards"]}
        self.assertEqual([c["id"] for c in self.board["cards"] if c.get("in_strip")], ["41", "38"])
        doing = [r["id"] for r in RECORDS["records"] if r["stage"] == "doing"]
        self.assertTrue(doing and all(cards[i]["column"] == "Doing" for i in doing))
        done = [c["id"] for c in self.board["cards"] if c["column"] == "Done"]
        self.assertEqual(done, ["40", "39", "37"])
        self.assertEqual(self.board["columns"][4]["total"], 48)
        self.assertNotIn("35", cards)
        self.assertNotIn("33", cards)
        for c in self.board["cards"]:
            for k in ("text", "facts", "sections"):
                self.assertNotIn(k, c)

    def test_card_file_equals_the_expected_one(self):
        card = json.loads(card_file(SHOP, CARD43))
        self.assertEqual(card, load("expected", "shop.card-43.json"))
        self.assertEqual(card["column"], "Checking")
        self.assertEqual([f["label"] for f in card["facts"]], ["Held by", "Version"])
        self.assertEqual(len(card["sections"]), 3)
        self.assertEqual(len(card["buttons"]), 4)

    def test_files_and_text_give_the_same(self):
        a = board_file(text("samples", "shop", "settings.json"), text("samples", "shop", "records.json"), today="2026-03-10")
        b = board_file(SHOP, RECORDS, today="2026-03-10")
        c = board_file(SHOP, RECORDS["records"], totals=RECORDS["totals"], today="2026-03-10")
        self.assertEqual(a, b)
        self.assertEqual(b, c)
        self.assertEqual(card_file(text("samples", "shop", "settings.json"), text("samples", "shop", "card-43.record.json")),
                         card_file(SHOP, CARD43))


class Scenario2(unittest.TestCase):
    """A program asks for smaller boards (requirement 13), and gets the same text twice (requirement 19)."""

    def test_group(self):
        b = json.loads(board_file(SHOP, RECORDS, today="2026-03-10", group="Website"))
        self.assertEqual([c["id"] for c in b["cards"]], ["38", "52", "48", "44", "45", "43", "40"])
        self.assertEqual([c["name"] for c in b["columns"]], ["Ideas", "Ready", "Doing", "Checking", "Done"])
        self.assertNotIn("total", b["columns"][4])

    def test_waiting(self):
        b = json.loads(board_file(SHOP, RECORDS, today="2026-03-10", waiting=True))
        self.assertEqual([c["id"] for c in b["cards"]], ["41", "38"])
        self.assertEqual(len(b["columns"]), 5)
        self.assertTrue(all("total" not in c for c in b["columns"]))

    def test_kind(self):
        b = json.loads(board_file(SHOP, RECORDS, kind="Decision"))
        self.assertEqual([c["id"] for c in b["cards"]], ["41", "37", "33"])  # "Done" keeps its latest 3 of those left
        self.assertEqual(len(b["columns"]), 5)

    def test_filters_together(self):
        b = json.loads(board_file(SHOP, RECORDS, group="Website", kind="Fix"))
        self.assertEqual([c["id"] for c in b["cards"]], ["38", "45", "43"])
        b = json.loads(board_file(SHOP, RECORDS, group="Nowhere"))
        self.assertEqual(b["cards"], [])

    def test_same_text_every_time(self):
        first = board_file(SHOP, RECORDS, today="2026-03-10")
        self.assertEqual(first, board_file(SHOP, RECORDS, today="2026-03-10"))
        self.assertEqual(first, board_file(SHOP, RECORDS, today="2026-03-10"))
        self.assertEqual(json.loads(first), load("expected", "shop.board.json"))


class Scenario4(unittest.TestCase):
    """Wrong input: one error holding every problem, in the expected words and order (requirements 14, 20)."""

    def test_six_problems(self):
        got = problems(board_file, text("samples", "broken", "settings.json"), text("samples", "broken", "records.json"))
        self.assertEqual(got, lines("expected", "broken.problems.txt"))
        self.assertEqual(len(got), 6)

    def test_one_error_and_the_program_goes_on(self):
        try:
            board_file(load("samples", "broken", "settings.json"), load("samples", "broken", "records.json"))
        except ExtractorError as e:
            self.assertIsInstance(e, ValueError)
            self.assertEqual(str(e), "\n".join(lines("expected", "broken.problems.txt")))
        else:
            self.fail("no error")
        self.assertTrue(board_file(SHOP, RECORDS))  # still working


class HowTheBoardIsMade(unittest.TestCase):
    """Requirements 5 to 12."""

    def recs(self, *rs):
        return [dict(r) for r in rs]

    def test_order_then_arrival(self):
        rs = self.recs({"id": "a", "title": "A", "stage": "todo"}, {"id": "b", "title": "B", "stage": "todo", "order": 5},
                       {"id": "c", "title": "C", "stage": "todo"}, {"id": "d", "title": "D", "stage": "todo", "order": -1.5})
        self.assertEqual(ids(board_file(settings(), rs)), ["d", "b", "a", "c"])

    def test_two_stages_one_column(self):
        s = settings(columns=[{"name": "Open", "stages": ["todo", "doing"]}, {"name": "Done", "stages": ["done"]}])
        b = json.loads(board_file(s, [{"id": "1", "title": "x", "stage": "doing"}, {"id": "2", "title": "y", "stage": "todo"}]))
        self.assertEqual([c["name"] for c in b["columns"]], ["Open", "Done"])
        self.assertEqual([c["column"] for c in b["cards"]], ["Open", "Open"])

    def test_keep_latest(self):
        s = settings()
        s["columns"][2]["keep_latest"] = 2
        rs = [{"id": "1", "title": "a", "stage": "done", "changed": "2026-03-01"},
              {"id": "2", "title": "b", "stage": "done"},
              {"id": "3", "title": "c", "stage": "done", "changed": "2026-03-01T10:00:00+02:00"},
              {"id": "4", "title": "d", "stage": "done", "changed": "2026-03-01 09:00Z"}]
        b = json.loads(board_file(s, rs))
        self.assertEqual([c["id"] for c in b["cards"]], ["4", "3"])  # 09:00 UTC is later than 08:00 UTC
        self.assertEqual(b["columns"][2]["total"], 4)
        s["columns"][2]["keep_latest"] = 4
        self.assertEqual(ids(board_file(s, rs)), ["4", "3", "1", "2"])  # no "changed": last

    def test_total_only_when_greater(self):
        rs = [{"id": "1", "title": "a", "stage": "done"}]
        b = json.loads(board_file(settings(), rs, totals={"done": 1}))
        self.assertNotIn("total", b["columns"][2])
        b = json.loads(board_file(settings(), rs, totals={"done": 7}))
        self.assertEqual(b["columns"][2]["total"], 7)

    def test_total_of_two_stages(self):
        s = settings(columns=[{"name": "Open", "stages": ["todo", "doing"], "keep_latest": 1}])
        rs = [{"id": "1", "title": "a", "stage": "todo"}, {"id": "2", "title": "b", "stage": "doing"},
              {"id": "3", "title": "c", "stage": "doing"}]
        self.assertEqual(json.loads(board_file(s, rs))["columns"][0]["total"], 3)
        self.assertEqual(json.loads(board_file(s, rs, totals={"todo": 10}))["columns"][0]["total"], 12)
        self.assertEqual(json.loads(board_file(s, rs, totals={"todo": 10, "doing": 2}))["columns"][0]["total"], 12)

    def test_no_total_with_a_filter(self):
        rs = [{"id": "1", "title": "a", "stage": "done", "group": "G"}]
        b = json.loads(board_file(settings(), rs, totals={"done": 9}, group="G"))
        self.assertNotIn("total", b["columns"][2])

    def test_waiting_with_and_without_a_strip(self):
        rs = [{"id": "1", "title": "a", "stage": "doing", "waiting": True}, {"id": "2", "title": "b", "stage": "todo"}]
        b = json.loads(board_file(settings(), rs))
        self.assertEqual(b["cards"][0], {"id": "1", "title": "a", "column": "Doing", "in_strip": True})
        s = settings()
        del s["strip"]
        b = json.loads(board_file(s, rs))
        self.assertEqual([c["id"] for c in b["cards"]], ["2", "1"])
        self.assertTrue(all("in_strip" not in c for c in b["cards"]))

    def test_detail_never_in_the_board_file(self):
        b = json.loads(board_file(SHOP, [dict(CARD43)]))
        self.assertEqual(set(b["cards"][0]), {"id", "title", "column", "kind", "group", "due", "buttons"})

    def test_copied_as_they_are(self):
        extra = {"summary": ["Launch in 3 weeks"], "link_pattern": "https://example.com/c/{id}",
                 "style": {"card_lines": 2, "colours": {"accent": "#4B5320"}},
                 "buttons": [{"name": "Go", "link": "https://example.com/{id}/go", "confirm": "Sure?"}]}
        rs = [{"id": "1", "title": "a", "stage": "todo", "buttons": [{"name": "Yes", "action": "yes", "main": True}],
               "link": "https://example.com/one", "note": "n", "group": "g", "kind": "k", "due": "2026-01-02"}]
        b = json.loads(board_file(settings(**extra), rs))
        for k, v in extra.items():
            self.assertEqual(b[k], v)
        self.assertEqual(b["cards"][0]["buttons"], rs[0]["buttons"])
        self.assertEqual(b["cards"][0]["link"], "https://example.com/one")

    def test_column_fields_copied(self):
        s = settings()
        s["columns"][2].update(limit=3, show=2, more_link="https://example.com/done", keep_latest=5)
        b = json.loads(board_file(s, []))
        self.assertEqual(b["columns"][2], {"name": "Done", "limit": 3, "show": 2, "more_link": "https://example.com/done"})
        self.assertEqual(b["cards"], [])
        self.assertNotIn("today", b)

    def test_buttons_keep_only_kinds_on_the_board(self):
        """The Board Generator refuses a button naming a kind no card has; such kinds are left out."""
        b = json.loads(board_file(SHOP, RECORDS, waiting=True))
        start = [x for x in b["buttons"] if x["name"] == "Start"]
        self.assertEqual(start[0]["kinds"], ["Fix"])
        b = json.loads(board_file(SHOP, RECORDS, kind="Decision"))
        self.assertEqual([x["name"] for x in b["buttons"]],
                         ["Send to checking", "Accept", "Send back", "Discuss", "Add note", "Archive"])
        self.assertEqual(SHOP["buttons"][0]["kinds"], ["Feature", "Fix", "Task"])  # the settings are untouched


class TheCheck(unittest.TestCase):
    """Requirements 14 to 17: every problem at once, saying where it is."""

    def assertProblems(self, s, rs, want, **k):
        self.assertEqual(problems(board_file, s, rs, **k), want)

    def test_settings(self):
        bad = {"extractor": 2, "title": 5, "columns": [
            {"name": "A", "stages": ["a"], "limit": 0, "show": 1.5, "keep_latest": "3", "more_link": "ftp://x"},
            {"name": "a", "stages": []}, "x", {"stages": ["b", "b", 7]}, {"name": "C", "stages": ["a"]}],
            "strip": {"show": 0}, "summary": "on", "link_pattern": "https://example.com/",
            "buttons": [{"name": "Go", "columns": ["Nowhere"], "ask": {"label": "Why?"}, "confirm": "Sure?"}],
            "style": {"card_lines": 4, "colours": {"ink": "#FFFFFF", "pink": "#FF00FF"}}}
        self.assertProblems(bad, [], [
            'Settings: the format version ("extractor") is missing or is not 1.',
            'Settings: the board name ("title") must be text.',
            'Settings: in the column "A", "limit" is 0; it must be a whole number, 1 or more.',
            'Settings: in the column "A", "show" is 1.5; it must be a whole number, 1 or more.',
            'Settings: in the column "A", "keep_latest" is "3"; it must be a whole number, 1 or more.',
            'Settings: in the column "A", the link for "more" is not a web address.',
            'Settings: the column name "a" is used twice.',
            'Settings: the column "a" has no stages ("stages").',
            'Settings: column 3 is not a column; write it as {"name": "…", "stages": ["…"]}.',
            'Settings: column 4 has no name.',
            'Settings: column 4 lists the stage "b" twice.',
            'Settings: column 4 lists a stage that is not a word: 7.',
            'Settings: the column "C" lists the stage "a", which the column "A" already has.',
            'Settings: the top strip has no name.',
            'Settings: the top strip: "show" is 0; it must be a whole number, 1 or more.',
            'Settings: the summary line ("summary") must be "auto", "off" or a list of up to 6 short texts (40 characters each).',
            'Settings: the link pattern ("link_pattern") must be a web address with {id} in it.',
            'Settings, button 1 ("Go"): it has neither a link nor an action.',
            'Settings, button 1 ("Go"): it asks for text but has no action.',
            'Settings, button 1 ("Go"): it has both a question to confirm and a text to ask for; only one is allowed.',
            'Settings, button 1 ("Go"): the column "Nowhere" is not defined. Defined: A, C.',
            'Settings, style: lines per card is 4; it must be 2 or 3.',
            'Settings, style: "pink" is not a colour the board has. It has: accent, column, strip, label, button, ink, muted, line, soon, late.',
            'Settings, style: "ink" (#FFFFFF) cannot be read on white: contrast 1.0 to 1; at least 4.5 is needed.',
        ])

    def test_no_columns(self):
        self.assertProblems({"extractor": 1, "title": "t"}, [], ['Settings: there are no columns ("columns").'])
        self.assertProblems(settings(columns=[{"name": str(i), "stages": [str(i)]} for i in range(13)]), [],
                            ["Settings: there are 13 columns; the limit is 12."])

    def test_records(self):
        rs = [{"id": "x" * 13, "title": "t" * 201, "stage": "todo"}, {"title": "", "stage": 3},
              {"id": "a", "title": "t", "stage": "todo", "kind": 1, "group": [], "note": "n" * 61, "due": "2026-02-30",
               "waiting": "yes", "link": "www.example.com", "order": "1", "changed": "yesterday"},
              {"id": "a", "title": "t"}, ["not", "a", "record"], {"id": 7.0, "title": "t", "stage": "todo", "id2": 1},
              {"id": True, "title": "t", "stage": "todo"},
              {"id": "b", "title": "t", "stage": "todo", "text": "x" * 5001, "facts": [{"label": "L"}],
               "sections": [{"title": "S", "type": "checklist", "items": [{"text": "i", "done": "yes"}]}, {"type": "grid"}],
               "buttons": [{"name": "N"}]}]
        self.assertProblems(settings(), rs, [
            'Record 1 (id "xxxxxxxxxxxxx"): the id is 13 characters; the limit is 12.',
            'Record 1 (id "xxxxxxxxxxxxx"): the title is 201 characters; the limit is 200.',
            'Record 2: the id is missing.',
            'Record 2: the title is missing.',
            'Record 2: the stage must be text.',
            'Record 3 (id "a"): "kind" must be text.',
            'Record 3 (id "a"): "group" must be text.',
            'Record 3 (id "a"): the due date is "2026-02-30"; a date is written YYYY-MM-DD.',
            'Record 3 (id "a"): "waiting" must be true or false.',
            'Record 3 (id "a"): the note is 61 characters; the limit is 60.',
            'Record 3 (id "a"): the link is not a web address; it must start with https:// or http://.',
            'Record 3 (id "a"): "order" is "1"; it must be a number.',
            'Record 3 (id "a"): "changed" is "yesterday"; a date is written YYYY-MM-DD, or YYYY-MM-DDTHH:MM with a time.',
            'Record 4 (id "a"): the id "a" is used twice.',
            'Record 4 (id "a"): the stage is missing.',
            'Record 5: it is not a record; write it as {"id": "…", "title": "…", "stage": "…"}.',
            'Record 7: the id must be text or a number.',
            'Record 8 (id "b"): the text is 5,001 characters; the limit is 5,000.',
            'Record 8 (id "b"), fact 1 ("L"): the value is missing.',
            'Record 8 (id "b"), section 1 ("S"), item 1: "done" is "yes"; it must be true or false.',
            'Record 8 (id "b"), section 2: the title is missing.',
            'Record 8 (id "b"), section 2: the type "grid" is not known. Known: text, list, checklist, timeline.',
            'Record 8 (id "b"), button 1 ("N"): it has neither a link nor an action.',
        ])

    def test_totals(self):
        rs = [{"id": "1", "title": "a", "stage": "done"}, {"id": "2", "title": "b", "stage": "done"}]
        self.assertProblems(settings(), rs, [
            'Records: there is a total for the stage "review", which is not in the settings.',
            'Records: the total for the stage "todo" is -1; it must be a whole number.',
            'Records: the total for the stage "done" is 1, but 2 records arrived with that stage.',
        ], totals={"review": 3, "todo": -1, "done": 1})
        self.assertProblems(settings(), rs, ['Records: the totals ("totals") must be written as {"stage": number, …}.'],
                            totals=[3])

    def test_settings_and_records_together(self):
        self.assertProblems({"extractor": 1, "title": "t", "columns": []}, [{"id": "1", "title": "a", "stage": "todo"}], [
            'Settings: there are no columns ("columns").',
            'Record 1 (id "1"): the stage "todo" is not in the settings.',
        ])

    def test_not_json(self):
        got = problems(board_file, "{", "[]")
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0].startswith("Settings: the file is not valid JSON: "))
        self.assertEqual(problems(board_file, settings(), ""), ["Records: the file is empty."])
        self.assertEqual(problems(board_file, settings(), '{"records": [], "x": NaN}')[0][:38],
                         "Records: the file is not valid JSON: N")
        self.assertEqual(problems(board_file, settings(), {"rows": []}), ['Records: the list of records ("records") is missing.'])
        self.assertEqual(problems(board_file, settings(), 5), ['Records: they must be a list of records, or {"records": […]}.'])
        self.assertEqual(problems(board_file, [], []),
                         ['Settings: they must be one object: {"extractor": 1, "title": "…", "columns": […]}.'])

    def test_options(self):
        self.assertEqual(problems(board_file, settings(), [], today="10 March", group="", kind=3, waiting="yes"), [
            'Today: "10 March" is not a date; a date is written YYYY-MM-DD.',
            "Filter: the group must be text.", "Filter: the kind must be text.", "Filter: waiting must be true or false."])
        import datetime
        self.assertEqual(json.loads(board_file(settings(), [], today=datetime.date(2026, 3, 10)))["today"], "2026-03-10")

    def test_totals_given_twice(self):
        self.assertEqual(problems(board_file, settings(), {"records": [], "totals": {}}, totals={}),
                         ["Records: totals are given twice, in the records and on their own; give them once."])

    def test_too_many_records_alone(self):
        rs = [{"id": str(i), "title": "t", "stage": "nowhere"} for i in range(MAX_RECORDS + 1)]
        self.assertEqual(problems(board_file, {}, rs), ["There are 5,001 records; the limit is 5,000."])

    def test_too_large_alone(self):
        link = "https://example.com/" + "a" * 1000
        rs = [{"id": str(i), "title": "t", "stage": "todo", "buttons": [{"name": "Go", "link": link}]} for i in range(5000)]
        got = problems(board_file, settings(), rs)
        self.assertEqual(len(got), 1)
        self.assertRegex(got[0], r"^The board file would be 5\.[0-9] MB; the limit is 5 MB\.$")
        big = dict(CARD43, sections=[{"title": f"S{i}", "type": "list", "items": [{"text": "x" * 300}] * 200}
                                     for i in range(20)])
        got = problems(card_file, SHOP, big)
        self.assertEqual(len(got), 1)
        self.assertRegex(got[0], r"^The card file would be [0-9.]+ MB; the limit is 1 MB\.$")

    def test_text_is_never_changed(self):
        odd = ["  spaces kept  ", "<b>not bold</b> & \"quoted\"", "{id} stays", "line\nbreak", "emoji 🧭 and ✓",
               "עברית", "‮reversed", "tab\there", "back\\slash"]
        rs = [{"id": str(i), "title": t, "stage": "todo", "note": t[:60], "group": t, "kind": t} for i, t in enumerate(odd)]
        b = json.loads(board_file(settings(), rs))
        for c, t in zip(b["cards"], odd):
            self.assertEqual((c["title"], c["group"], c["kind"], c["note"]), (t, t, t, t[:60]))
        r = dict(CARD43, text=odd[1] + "\n\n" + odd[4])
        self.assertEqual(json.loads(card_file(SHOP, r))["text"], r["text"])

    def test_lengths_count_as_the_board_generator_counts(self):
        # 🧭 is two units for the Board Generator: 31 of them make 62, over the note's 60.
        rs = [{"id": "1", "title": "t", "stage": "todo", "note": "🧭" * 31}]
        self.assertEqual(problems(board_file, settings(), rs), ['Record 1 (id "1"): the note is 62 characters; the limit is 60.'])


class TheCardFile(unittest.TestCase):

    def test_problems_name_the_record(self):
        r = dict(CARD43, stage="review", due="soon", facts="many")
        self.assertEqual(problems(card_file, SHOP, r), [
            'Record (id "43"): the stage "review" is not in the settings. In the settings: idea, ready, doing, checking, rework, done.',
            'Record (id "43"): the due date is "soon"; a date is written YYYY-MM-DD.',
            'Record (id "43"): the facts ("facts") must be a list.',
        ])
        self.assertEqual(problems(card_file, SHOP, {"title": "t", "stage": "idea"}), ["Record: the id is missing."])
        self.assertEqual(problems(card_file, SHOP, [CARD43]),
                         ['Record: it must be one record: {"id": "…", "title": "…", "stage": "…"}.'])
        self.assertEqual(problems(card_file, {"extractor": 1}, CARD43)[:2], [
            'Settings: the board name ("title") is missing.', 'Settings: there are no columns ("columns").'])

    def test_smallest(self):
        self.assertEqual(json.loads(card_file(SHOP, {"id": 7, "title": "t", "stage": "done"})),
                         {"card": 1, "id": 7, "title": "t", "column": "Done"})


class InsideAProgram(unittest.TestCase):
    """Requirements 19 to 21."""

    def test_writes_nothing_and_opens_no_connection(self):
        seen = []

        def hook(event, args):
            if event == "open" and len(args) > 1 and isinstance(args[1], str) and any(m in args[1] for m in "wax+"):
                seen.append((event, args[0]))
            elif event.startswith("socket.") or event in ("os.remove", "os.rename", "os.mkdir", "shutil.copyfile"):
                seen.append((event,))
        hooks.append(hook)
        try:
            board_file(SHOP, RECORDS, today="2026-03-10")
            board_file(SHOP, RECORDS, group="Website")
            card_file(SHOP, CARD43)
            problems(board_file, load("samples", "broken", "settings.json"), load("samples", "broken", "records.json"))
        finally:
            hooks.remove(hook)
        self.assertEqual(seen, [])

    def test_input_is_left_as_it_was(self):
        s, r, c = copy.deepcopy(SHOP), copy.deepcopy(RECORDS), copy.deepcopy(CARD43)
        board_file(s, r, waiting=True)
        card_file(s, c)
        self.assertEqual((s, r, c), (SHOP, RECORDS, CARD43))

    def test_never_anything_but_its_own_error(self):
        """Any shape of input gives a board file or an ExtractorError, never another failure."""
        rnd = random.Random(208)
        values = [None, True, False, 0, -1, 1, 2.5, 1e309 if False else 1e300, "", " ", "x", "2026-03-10", "doing",
                  "https://example.com/{id}", [], [1], ["doing"], {}, {"name": "x"}, {"label": "l", "value": "v"},
                  "#FFFFFF", float("nan")]
        fields = ["extractor", "title", "columns", "strip", "summary", "link_pattern", "style", "buttons"]
        rfields = ["id", "title", "stage", "kind", "group", "due", "note", "link", "waiting", "order", "changed",
                   "buttons", "text", "facts", "sections"]
        for _ in range(3000):
            s = copy.deepcopy(SHOP)
            rs = copy.deepcopy(RECORDS["records"][:4])
            for _ in range(rnd.randint(1, 3)):
                target = rnd.choice(["s", "c", "r", "b"])
                v = rnd.choice(values)
                if target == "s":
                    s[rnd.choice(fields)] = v
                elif target == "c" and isinstance(s.get("columns"), list) and s["columns"]:
                    col = rnd.choice(s["columns"])
                    if isinstance(col, dict):
                        col[rnd.choice(["name", "stages", "limit", "show", "keep_latest", "more_link"])] = v
                elif target == "r":
                    rnd.choice(rs)[rnd.choice(rfields)] = v
                elif isinstance(s.get("buttons"), list) and s["buttons"]:
                    b = rnd.choice(s["buttons"])
                    if isinstance(b, dict):
                        b[rnd.choice(["name", "link", "action", "kinds", "columns", "main", "ask", "confirm"])] = v
            try:
                out = board_file(s, rs, totals=rnd.choice([None, {"done": 3}, {"done": v}]),
                                 waiting=rnd.choice([False, True]))
                json.loads(out)
            except ExtractorError as e:
                self.assertTrue(e.problems and all(isinstance(m, str) and m for m in e.problems))
            try:
                card_file(s, rnd.choice(rs))
            except ExtractorError:
                pass

    def test_five_thousand_records_in_under_a_second(self):
        rnd = random.Random(21)
        stages = ["idea", "ready", "doing", "checking", "rework", "done"]
        rs = [{"id": str(i), "title": f"Card number {i} with a title of a usual length", "stage": rnd.choice(stages),
               "kind": rnd.choice(["Feature", "Fix", "Task", "Decision"]), "group": rnd.choice(["Website", "Stockroom"]),
               "due": "2026-03-%02d" % rnd.randint(1, 28), "order": rnd.randint(1, 9999),
               "changed": "2026-03-01T10:%02d:00" % rnd.randint(0, 59), "waiting": rnd.random() < 0.02}
              for i in range(5000)]
        best = None
        for _ in range(3):
            t = time.perf_counter()
            board_file(SHOP, rs, today="2026-03-10")
            took = time.perf_counter() - t
            best = took if best is None else min(best, took)
        self.assertLess(best, 1.0, f"took {best:.2f} s")


hooks = []
sys.addaudithook(lambda event, args: [h(event, args) for h in list(hooks)])

if __name__ == "__main__":
    unittest.main()

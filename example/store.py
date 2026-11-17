"""The example's database: a small SQLite file holding the shop sample's made-up cards.

The service reads its cards from here, decides each card's buttons by its own
rules, and hands the records to the extractor. Nothing here is part of the
extractor.
"""

import contextlib
import datetime
import json
import os
import sqlite3
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAMPLE = os.path.join(ROOT, "samples", "shop")
DEFAULT_DB = os.path.join(HERE, "shop.db")
WHO = "You"

SCHEMA = """
CREATE TABLE cards (
  id TEXT PRIMARY KEY, pos INTEGER NOT NULL, title TEXT NOT NULL, stage TEXT NOT NULL,
  kind TEXT, grp TEXT, due TEXT, note TEXT, waiting INTEGER NOT NULL DEFAULT 0, ord REAL, changed TEXT,
  text TEXT, facts TEXT, extra TEXT
);
CREATE TABLE lines (
  n INTEGER PRIMARY KEY AUTOINCREMENT, card_id TEXT NOT NULL, kind TEXT NOT NULL,
  at TEXT NOT NULL, who TEXT, text TEXT NOT NULL
);
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
"""


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def seed(path):
    """Writes a fresh database from the shop sample, replacing the file in one step."""
    with open(os.path.join(SAMPLE, "records.json"), encoding="utf-8") as f:
        sample = json.load(f)
    with open(os.path.join(SAMPLE, "card-43.record.json"), encoding="utf-8") as f:
        detail = json.load(f)
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".shop-", suffix=".db", dir=folder)
    os.close(fd)
    try:
        db = sqlite3.connect(tmp)
        db.executescript(SCHEMA)
        done = 0
        for pos, r in enumerate(sample["records"]):
            done += r["stage"] == "done"
            db.execute("INSERT INTO cards (id, pos, title, stage, kind, grp, due, note, waiting, ord, changed) "
                       "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (r["id"], pos, r["title"], r["stage"], r.get("kind"), r.get("group"), r.get("due"),
                        r.get("note"), 1 if r.get("waiting") else 0, r.get("order"), r.get("changed")))
        # The finished cards the board has but does not hand over: the sample's total less those it holds.
        db.execute("INSERT INTO meta VALUES ('done_elsewhere', ?)", (str(sample["totals"]["done"] - done),))
        extra = []
        for s in detail.get("sections", []):
            if s["type"] == "timeline" and s["title"] in ("Notes", "History"):
                kind = "note" if s["title"] == "Notes" else "history"
                for it in reversed(s["items"]):  # oldest first, so a higher number is newer
                    db.execute("INSERT INTO lines (card_id, kind, at, who, text) VALUES (?,?,?,?,?)",
                               (detail["id"], kind, it["when"], it.get("who"), it["text"]))
            else:
                extra.append(s)
        db.execute("UPDATE cards SET text = ?, facts = ?, extra = ?, due = ? WHERE id = ?",
                   (detail.get("text"), json.dumps(detail.get("facts", [])), json.dumps(extra), detail.get("due"),
                    detail["id"]))
        db.commit()
        db.close()
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class Store:
    def __init__(self, path=DEFAULT_DB):
        self.path = os.path.abspath(path)
        if not os.path.exists(self.path):  # made at the first start
            seed(self.path)

    @contextlib.contextmanager
    def _db(self):
        """One connection per request: committed when all went well, always closed."""
        if not os.path.exists(self.path):
            seed(self.path)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        finally:
            db.close()

    # -- reading

    def records(self):
        """Every card as a plain record, with the true total of finished cards."""
        with self._db() as db:
            rows = db.execute("SELECT * FROM cards ORDER BY pos").fetchall()
            elsewhere = int(db.execute("SELECT v FROM meta WHERE k = 'done_elsewhere'").fetchone()[0])
        recs = [self._record(r) for r in rows]
        done = sum(1 for r in recs if r["stage"] == "done")
        return {"records": recs, "totals": {"done": done + elsewhere}}

    @staticmethod
    def _record(row):
        r = {"id": row["id"], "title": row["title"], "stage": row["stage"]}
        for field, col in (("kind", "kind"), ("group", "grp"), ("due", "due"), ("note", "note"),
                           ("changed", "changed")):
            if row[col] is not None:
                r[field] = row[col]
        if row["waiting"]:
            r["waiting"] = True
        if row["ord"] is not None:
            r["order"] = int(row["ord"]) if float(row["ord"]).is_integer() else row["ord"]
        return r

    def record(self, card_id):
        """One card with its detail, or None."""
        with self._db() as db:
            row = db.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
            if row is None:
                return None
            lines = db.execute("SELECT * FROM lines WHERE card_id = ? ORDER BY n DESC", (card_id,)).fetchall()
        r = self._record(row)
        if row["text"]:
            r["text"] = row["text"]
        facts = json.loads(row["facts"]) if row["facts"] else []
        if facts:
            r["facts"] = facts
        timeline = lambda kind: [dict({"when": x["at"], "text": x["text"]}, **({"who": x["who"]} if x["who"] else {}))
                                 for x in lines if x["kind"] == kind]
        r["sections"] = (json.loads(row["extra"]) if row["extra"] else []) + [
            {"title": "Notes", "type": "timeline", "items": timeline("note")},
            {"title": "History", "type": "timeline", "collapsed": True, "items": timeline("history")},
        ]
        r["buttons"] = buttons(r["stage"])
        return r

    # -- changing

    def act(self, card_id, action, text):
        """Carries out a button press. Returns (status, answer or message)."""
        text = text.strip() if isinstance(text, str) else ""
        with self._db() as db:
            row = db.execute("SELECT stage FROM cards WHERE id = ?", (card_id,)).fetchone()
            if row is None:
                return 404, "There is no such card."
            if action not in [b["action"] for b in buttons(row["stage"])]:
                return 409, f'The card cannot do "{action}" where it is now.'
            now = _now()
            if action == "accept":
                db.execute("UPDATE cards SET stage = 'done', waiting = 0, changed = ? WHERE id = ?", (now, card_id))
                self._line(db, card_id, "history", now, "Accepted")
                return 200, ""
            if not text:
                return 400, "Some text is needed."
            if action == "send-back":
                db.execute("UPDATE cards SET stage = 'ready', waiting = 0, changed = ? WHERE id = ?", (now, card_id))
                self._line(db, card_id, "note", now, text)
                self._line(db, card_id, "history", now, "Sent back to Ready")
                return 200, ""
            self._line(db, card_id, "note", now, text)  # "note"
            db.execute("UPDATE cards SET changed = ? WHERE id = ?", (now, card_id))
            return 200, "keep open"

    @staticmethod
    def _line(db, card_id, kind, at, text):
        db.execute("INSERT INTO lines (card_id, kind, at, who, text) VALUES (?,?,?,?,?)", (card_id, kind, at, WHO, text))


def buttons(stage):
    """The service's own rule for a card's buttons: what can be done with it where it stands."""
    note = {"name": "Add note", "action": "note", "ask": {"label": "Note", "required": True}}
    if stage in ("checking", "rework"):
        return [
            {"name": "Accept", "main": True, "action": "accept"},
            {"name": "Send back", "action": "send-back", "ask": {"label": "Why is it going back?", "required": True}},
            note,
        ]
    return [note]

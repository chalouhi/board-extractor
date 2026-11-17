"""Board Extractor: settings and card records in; the Board Generator's board file and card file out.

The input is described in docs/input-format.md, the output in the Board
Generator's file-format guide (release 1.1). Nothing here keeps state, writes a
file or opens a connection, and the same input always gives the same text.
"""

import copy
import datetime
import json
import re
from decimal import Decimal

from . import rules
from .rules import filled, is_finite, is_number, is_obj, is_text, js_string_of, jslen, key, show, thousands, whole

FORMAT = 1
MAX_RECORDS = 5000
MAX_BOARD_BYTES = rules.MAX_BYTES        # 5 MB
MAX_CARD_BYTES = rules.CARD_MAX_BYTES    # 1 MB, the card file's own limit


class ExtractorError(ValueError):
    """The input has problems. ``problems`` lists every one, in plain words."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("\n".join(self.problems))


# ---------------------------------------------------------------- reading the input --

def _no_constant(name):
    raise ValueError(f"{name} is not allowed in JSON")


def _load(value, what):
    """JSON text (or bytes) becomes data; data is taken as it is. Returns (data, problems)."""
    if isinstance(value, (bytes, bytearray)):
        try:
            value = bytes(value).decode("utf-8")
        except UnicodeDecodeError:
            return None, [f"{what}: the file is not UTF-8 text."]
    if isinstance(value, str):
        text = value[1:] if value.startswith("﻿") else value
        if not text.strip():
            return None, [f"{what}: the file is empty."]
        try:
            return json.loads(text, parse_constant=_no_constant), []
        except ValueError as e:
            return None, [f"{what}: the file is not valid JSON: {str(e).rstrip('.')}."]
    return value, []


def _lower_first(msg):
    if len(msg) > 1 and msg[0].isupper() and not msg[1].isupper():
        return msg[0].lower() + msg[1:]
    return msg


def _under(prefix, msg):
    """A message of the Board Generator, said of a part of the input."""
    if re.match(r"(Fact|Section|Button|Column|Card) [0-9]", msg):
        return f"{prefix}, {_lower_first(msg)}"
    if msg.startswith("Style: "):
        return f"{prefix}, style: {msg[7:]}"
    return f"{prefix}: {_lower_first(msg)}"


_CHANGED = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})(?:[T ]([0-9]{2}):([0-9]{2})(?::([0-9]{2})(\.[0-9]+)?)?"
                      r"(Z|[+-][0-9]{2}:?[0-9]{2})?)?")


def _changed_key(s):
    """When a record last changed, as a number of seconds, or None when it is not a date."""
    m = _CHANGED.fullmatch(s) if isinstance(s, str) else None
    if not m:
        return None
    d = rules.date_of(m.group(1))
    if not d:
        return None
    hh, mm, ss = int(m.group(2) or 0), int(m.group(3) or 0), int(m.group(4) or 0)
    if hh > 23 or mm > 59 or ss > 59:
        return None
    t = Decimal(d.toordinal()) * 86400 + hh * 3600 + mm * 60 + ss + Decimal(m.group(5) or 0)
    z = m.group(6)
    if z and z != "Z":
        zh, zm = int(z[1:3]), int(z[-2:])
        if zh > 23 or zm > 59:
            return None
        t -= (1 if z[0] == "+" else -1) * (zh * 3600 + zm * 60)
    return t


# ---------------------------------------------------------------- the settings --

class _Settings:
    """The checked settings: the columns and which stage belongs to which."""

    def __init__(self, s):
        self.s = s
        self.columns = []          # (settings column, its name), valid ones only
        self.column_of = {}        # stage -> index into self.columns
        self.stages = []           # every stage, in column order


def _check_settings(s):
    if not is_obj(s):
        return None, ['Settings: they must be one object: {"extractor": 1, "title": "…", "columns": […]}.']
    p = []
    st = _Settings(s)
    if not (is_number(s.get("extractor")) and s.get("extractor") == FORMAT):
        p.append('Settings: the format version ("extractor") is missing or is not 1.')
    if not filled(s.get("title")):
        p.append('Settings: the board name ("title") must be text.' if "title" in s and not is_text(s["title"])
                 else 'Settings: the board name ("title") is missing.')

    cols = s["columns"] if isinstance(s.get("columns"), list) else []
    if not cols:
        p.append('Settings: there are no columns ("columns").')
    elif len(cols) > rules.MAX_COLUMNS:
        p.append(f"Settings: there are {len(cols)} columns; the limit is {rules.MAX_COLUMNS}.")
    names, owner = [], {}
    for i, c in enumerate(cols, 1):
        if not is_obj(c):
            p.append(f'Settings: column {i} is not a column; write it as {{"name": "…", "stages": ["…"]}}.')
            continue
        n = c.get("name")
        if not filled(n):
            p.append(f"Settings: the name of column {i} must be text." if "name" in c and not is_text(n)
                     else f"Settings: column {i} has no name.")
            at = f"column {i}"
        else:
            at = f'the column "{n}"'
            if any(key(x) == key(n) for x in names):
                p.append(f'Settings: the column name "{n}" is used twice.')
            else:
                names.append(n)
        stages = c.get("stages")
        mine = []
        if not isinstance(stages, list) or not stages:
            p.append(f'Settings: {at} has no stages ("stages").')
        else:
            for x in stages:
                if not filled(x):
                    p.append(f"Settings: {at} lists a stage that is not a word: {show(x)}.")
                elif x in mine:
                    p.append(f'Settings: {at} lists the stage "{x}" twice.')
                elif x in owner:
                    p.append(f'Settings: {at} lists the stage "{x}", which {owner[x]} already has.')
                else:
                    mine.append(x)
                    owner[x] = at
        for k in ("limit", "show", "keep_latest"):
            if k in c and not whole(c[k]):
                p.append(f'Settings: in {at}, "{k}" is {show(c[k])}; it must be a whole number, 1 or more.')
        if "more_link" in c and not rules.is_web(c["more_link"]):
            p.append(f'Settings: in {at}, the link for "more" is not a web address.')
        if filled(n) and mine:
            idx = len(st.columns)
            st.columns.append((c, n))
            for x in mine:
                st.column_of[x] = idx
                st.stages.append(x)

    # What is copied into the board file is checked by the Board Generator's own rules.
    known = [key(x) for x in names]
    p.extend(_under("Settings", m) for m in rules.strip_problems(s))
    p.extend(_under("Settings", m) for m in rules.summary_problems(s))
    p.extend(_under("Settings", m) for m in rules.link_pattern_problems(s))
    shaped = dict(s, columns=[{"name": n} for n in names])
    p.extend(_under("Settings", m) for m in rules.file_button_problems(shaped, set(), known, check_kinds=False))
    p.extend(_under("Settings", m) for m in rules.style_problems(s))
    return st, p


# ---------------------------------------------------------------- the records --

def _record_problems(r, w, st, ids):
    """Every problem of one record. ``w`` names it; ``ids`` holds the ids already seen (None: one record)."""
    p = []
    rid = r.get("id")
    id_ok = (is_text(rid) and rid != "") or is_finite(rid)
    if not id_ok:
        p.append(f"{w}: the id must be text or a number." if "id" in r and rid != "" else f"{w}: the id is missing.")
    else:
        sid = js_string_of(rid)
        if jslen(sid) > rules.MAX_ID:
            p.append(f"{w}: the id is {jslen(sid)} characters; the limit is {rules.MAX_ID}.")
        if ids is not None:
            if sid in ids:
                p.append(f'{w}: the id "{sid}" is used twice.')
            ids.add(sid)
    if not filled(r.get("title")):
        p.append(f"{w}: the title is missing.")
    elif jslen(r["title"]) > rules.MAX_TITLE:
        p.append(f"{w}: the title is {jslen(r['title'])} characters; the limit is {rules.MAX_TITLE}.")
    stage = r.get("stage")
    if "stage" not in r or stage == "" or stage is None:
        p.append(f"{w}: the stage is missing.")
    elif not is_text(stage):
        p.append(f"{w}: the stage must be text.")
    elif stage not in st.column_of:
        listed = f" In the settings: {', '.join(st.stages)}." if st.stages else ""
        p.append(f'{w}: the stage "{stage}" is not in the settings.{listed}')
    for k in ("kind", "group", "note", "text"):
        if k in r and not is_text(r[k]):
            p.append(f'{w}: "{k}" must be text.')
    if "due" in r and not rules.date_of(r["due"]):
        p.append(f"{w}: the due date is {show(r['due'])}; a date is written YYYY-MM-DD.")
    if "waiting" in r and not isinstance(r["waiting"], bool):
        p.append(f'{w}: "waiting" must be true or false.')
    if is_text(r.get("note")) and jslen(r["note"]) > rules.MAX_NOTE:
        p.append(f"{w}: the note is {jslen(r['note'])} characters; the limit is {rules.MAX_NOTE}.")
    if "link" in r and not rules.is_web(r["link"]):
        p.append(f"{w}: the link is not a web address; it must start with https:// or http://.")
    if "order" in r and not is_finite(r["order"]):
        p.append(f'{w}: "order" is {show(r["order"])}; it must be a number.')
    if "changed" in r and _changed_key(r["changed"]) is None:
        p.append(f'{w}: "changed" is {show(r["changed"])}; a date is written YYYY-MM-DD, '
                 f"or YYYY-MM-DDTHH:MM with a time.")
    # The detail, by the rules of the card file.
    p.extend(_under(w, m) for m in rules.detail_problems({k: r[k] for k in ("text", "facts", "sections", "buttons")
                                                          if k in r}))
    return p


def _record_name(i, r):
    rid = r.get("id") if is_obj(r) else None
    if (is_text(rid) and rid != "") or is_finite(rid):
        return f'Record {i} (id "{js_string_of(rid)}")'
    return f"Record {i}"


def _check_totals(totals, st, arrived):
    p = []
    if totals is None:
        return p
    if not is_obj(totals):
        return ['Records: the totals ("totals") must be written as {"stage": number, …}.']
    for stage in rules.js_keys(totals):
        n = totals[stage]
        if stage not in st.column_of:
            p.append(f'Records: there is a total for the stage "{stage}", which is not in the settings.')
        elif not (is_finite(n) and float(n).is_integer() and n >= 0):
            p.append(f'Records: the total for the stage "{stage}" is {show(n)}; it must be a whole number.')
        elif n < arrived.get(stage, 0):
            p.append(f'Records: the total for the stage "{stage}" is {rules.js_number(n)}, '
                     f"but {arrived[stage]} records arrived with that stage.")
    return p


def _today(today):
    if today is None:
        return None, []
    if isinstance(today, datetime.datetime):
        return today.date().isoformat(), []
    if isinstance(today, datetime.date):
        return today.isoformat(), []
    if rules.date_of(today):
        return today, []
    return None, [f"Today: {show(today)} is not a date; a date is written YYYY-MM-DD."]


def _text_filter(v, name):
    if v is None or filled(v):
        return []
    return [f"Filter: the {name} must be text."]


def _dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


# ---------------------------------------------------------------- the board file --

def board_file(settings, records, *, totals=None, today=None, group=None, kind=None, waiting=False):
    """The board file, as JSON text.

    settings  the settings: a dict, or the settings file's text.
    records   the records: a list of dicts, a records file as a dict ({"records": […], "totals": {…}}),
              or a records file's text.
    totals    the true number of cards per stage, when only some are handed over ({"done": 48}).
    today     the day due dates are judged by: "YYYY-MM-DD" or a date. Left out: not written.
    group, kind, waiting   filters: only one group, only one kind, only the waiting cards.

    Raises ExtractorError, holding every problem, when the input is wrong. Never anything else.
    """
    s, p_set = _load(settings, "Settings")
    data, p_rec = _load(records, "Records")
    p_opt = []
    recs = None
    if p_rec:
        pass
    elif isinstance(data, list):
        recs = data
    elif is_obj(data):
        if not isinstance(data.get("records"), list):
            p_rec.append('Records: the list of records ("records") is missing.')
        else:
            recs = data["records"]
        if "totals" in data:
            if totals is not None:
                p_rec.append("Records: totals are given twice, in the records and on their own; give them once.")
            else:
                totals = data["totals"]
    else:
        p_rec.append('Records: they must be a list of records, or {"records": […]}.')
    if recs is not None and len(recs) > MAX_RECORDS:
        raise ExtractorError([f"There are {thousands(len(recs))} records; the limit is {thousands(MAX_RECORDS)}."])
    day, p = _today(today)
    p_opt += p
    p_opt += _text_filter(group, "group") + _text_filter(kind, "kind")
    if not isinstance(waiting, bool):
        p_opt.append("Filter: waiting must be true or false.")

    st, p = (None, []) if p_set else _check_settings(s)
    p_set += p
    if st is None:
        st = _Settings({})
    ids, arrived = set(), {}
    for i, r in enumerate(recs or [], 1):
        if not is_obj(r):
            p_rec.append(f'Record {i}: it is not a record; write it as {{"id": "…", "title": "…", "stage": "…"}}.')
            continue
        p_rec.extend(_record_problems(r, _record_name(i, r), st, ids))
        if is_text(r.get("stage")):
            arrived[r["stage"]] = arrived.get(r["stage"], 0) + 1
    if recs is not None:
        p_rec.extend(_check_totals(totals, st, arrived))
    problems = p_set + p_rec + p_opt
    if problems:
        raise ExtractorError(problems)

    out, origin = _build_board(st, recs, totals or {}, day, group, kind, waiting)
    problems = []
    for m in rules.read_problems(out):
        hit = re.match(r"Card ([0-9]+)( \(id \"[^\"]*\"\))?(.*)", m, re.S)
        if hit:
            i = origin[int(hit.group(1)) - 1]
            problems.append(_record_name(i, recs[i - 1]) + hit.group(3))
        else:
            problems.append(_under("Settings", m))
    if problems:
        raise ExtractorError(problems)
    return _sized(_dump(out), "board file", MAX_BOARD_BYTES)


def _sized(text, what, limit):
    n = rules.utf8_length(text)
    if n > limit:
        raise ExtractorError([f"The {what} would be {rules.megabytes(n)} MB; the limit is {limit // (1024 * 1024)} MB."])
    return text


def _ordered(items):
    """Rising "order"; records without one keep the order they arrived in, after those that have one."""
    return sorted(items, key=lambda x: (0, x[1]["order"], x[0]) if "order" in x[1] else (1, 0, x[0]))


def _latest(items):
    """The most recently changed first; records with no "changed" last, in the order they arrived."""
    def k(x):
        t = _changed_key(x[1].get("changed")) if "changed" in x[1] else None
        return (0, -t, x[0]) if t is not None else (1, 0, x[0])
    return sorted(items, key=k)


def _card(r, column, in_strip):
    c = {"id": r["id"], "title": r["title"], "column": column}
    for k in ("kind", "group", "due", "note", "link"):
        if k in r:
            c[k] = copy.deepcopy(r[k])
    if in_strip:
        c["in_strip"] = True
    if "buttons" in r:
        c["buttons"] = copy.deepcopy(r["buttons"])
    return c


def _build_board(st, recs, totals, day, group, kind, waiting):
    s = st.s
    filtered = group is not None or kind is not None or waiting
    has_strip = "strip" in s
    chosen = [(i, r) for i, r in enumerate(recs, 1)
              if (group is None or r.get("group") == group) and (kind is None or r.get("kind") == kind)
              and (not waiting or r.get("waiting") is True)]
    arrived = {}
    for r in recs:
        arrived[r["stage"]] = arrived.get(r["stage"], 0) + 1

    strip, per_column = [], [[] for _ in st.columns]
    for i, r in chosen:
        if has_strip and r.get("waiting") is True:
            strip.append((i, r))
        else:
            per_column[st.column_of[r["stage"]]].append((i, r))

    placed = [(i, r, True) for i, r in _ordered(strip)]
    columns = []
    for idx, (c, name) in enumerate(st.columns):
        mine = per_column[idx]
        if "keep_latest" in c:
            mine = _latest(mine)[:int(c["keep_latest"])]
        else:
            mine = _ordered(mine)
        placed += [(i, r, False) for i, r in mine]
        col = {"name": name}
        for k in ("limit", "show"):
            if k in c:
                col[k] = c[k]
        if not filtered:
            count = sum(totals[x] if x in totals else arrived.get(x, 0) for x in st.stages if st.column_of[x] == idx)
            carried = sum(1 for _, r, _s in placed if st.column_of[r["stage"]] == idx)
            if count > carried:
                col["total"] = int(count)
        if "more_link" in c:
            col["more_link"] = c["more_link"]
        columns.append(col)

    cards = [_card(r, st.columns[st.column_of[r["stage"]]][1], in_strip) for _, r, in_strip in placed]
    origin = [i for i, _, _ in placed]

    out = {"board": 1, "title": s["title"]}
    if day:
        out["today"] = day
    for k in ("link_pattern", "strip", "summary", "style"):
        if k in s:
            out[k] = copy.deepcopy(s[k])
    out["columns"] = columns
    out["cards"] = cards
    if "buttons" in s:
        out["buttons"] = _buttons_for(s["buttons"], cards)
    return out, origin


def _buttons_for(buttons, cards):
    """The settings' buttons, as they are. A kind that no card on this board has is left out of a button's
    "kinds" (the Board Generator refuses a kind no card has), and a button left with none of its kinds is
    not written: it could show on no card of this board."""
    present = {key(c["kind"]) for c in cards if filled(c.get("kind"))}
    out = []
    for b in buttons:
        b = copy.deepcopy(b)
        if isinstance(b.get("kinds"), list) and b["kinds"]:
            kept = [k for k in b["kinds"] if key(k) in present]
            if not kept:
                continue
            b["kinds"] = kept
        out.append(b)
    return out


# ---------------------------------------------------------------- the card file --

def card_file(settings, record):
    """The card file of one record, as JSON text.

    settings  the settings: a dict, or the settings file's text.
    record    one record with its detail (text, facts, sections, buttons): a dict, or its text.

    Raises ExtractorError, holding every problem, when the input is wrong. Never anything else.
    """
    s, p_set = _load(settings, "Settings")
    r, p_rec = _load(record, "Record")
    st, p = (None, []) if p_set else _check_settings(s)
    p_set += p
    if st is None:
        st = _Settings({})
    w = "Record"
    if not p_rec:
        if not is_obj(r):
            p_rec.append('Record: it must be one record: {"id": "…", "title": "…", "stage": "…"}.')
        else:
            rid = r.get("id")
            if (is_text(rid) and rid != "") or is_finite(rid):
                w = f'Record (id "{js_string_of(rid)}")'
            p_rec.extend(_record_problems(r, w, st, None))
    problems = p_set + p_rec
    if problems:
        raise ExtractorError(problems)

    out = {"card": 1, "id": r["id"], "title": r["title"], "column": st.columns[st.column_of[r["stage"]]][1]}
    for k in ("kind", "group", "due", "note", "link", "text", "facts", "sections", "buttons"):
        if k in r:
            out[k] = copy.deepcopy(r[k])
    problems = [_under(w, m) for m in rules.validate_card(out, r["id"])]
    if problems:
        raise ExtractorError(problems)
    return _sized(_dump(out), "card file", MAX_CARD_BYTES)

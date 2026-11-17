"""The rules of the Board Generator 1.1 board file and card file, in Python.

These are the checks the Board Generator's own reader (``src/board.js`` at
release 1.1) makes, with the same messages, in the same order. The extractor
runs them on everything it writes, so a file it returns is always one the
Board Generator accepts. ``tests/parity.test.js`` holds the two side by side.

JavaScript and Python differ in small ways that change a message: the length
of a text (JavaScript counts UTF-16 units), what counts as a space, how a
number is written, and the order of an object's keys. The helpers below follow
JavaScript.
"""

import math
import re
from decimal import Decimal, ROUND_HALF_UP

# Limits of the board file and the card file.
MAX_BYTES = 5 * 1024 * 1024
MAX_CARDS = 5000
MAX_COLUMNS = 12
MAX_TITLE = 200
MAX_NOTE = 60
MAX_TEXT = 2000
MAX_ID = 12
MAX_BUTTON = 24
MAX_SUMMARY = 6
MAX_SUMMARY_TEXT = 40
CARD_MAX_BYTES = 1024 * 1024
MAX_FACTS = 12
MAX_SECTIONS = 20
MAX_ITEMS = 200
MAX_CARD_TEXT = 5000
MAX_LABEL = 24
MAX_VALUE = 60
MAX_ASK = 60
SECTION_TYPES = ["text", "list", "checklist", "timeline"]

COLOURS = {
    "accent": "#FF5B04", "column": "#F0F6F7", "strip": "#FFF3EC", "label": "#075056", "button": "#075056",
    "ink": "#16232A", "muted": "#5F7078", "line": "#D3E0E3", "soon": "#9A5B00", "late": "#C62828",
}
READ_ON = [("ink", ["white", "column", "strip"]), ("muted", ["white", "column", "strip"]), ("label", ["white"]),
           ("soon", ["white"]), ("late", ["white", "column"])]

# JavaScript's white space (String.prototype.trim, and \s in a pattern).
_JS_SPACE = "\t\n\v\f\r              " \
            "    　﻿"
_WEB = re.compile("https?://[^" + re.escape(_JS_SPACE) + "]+")
_HEX = re.compile("#[0-9A-Fa-f]{6}")
_DATE = re.compile("([0-9]{4})-([0-9]{2})-([0-9]{2})")
_WHEN = re.compile("([0-9]{4}-[0-9]{2}-[0-9]{2})(?:[T ]([0-9]{2}):([0-9]{2})(?::[0-9]{2}(?:\\.[0-9]+)?)?"
                   "(?:Z|[+-][0-9]{2}:?[0-9]{2})?)?")
_INDEX = re.compile("0|[1-9][0-9]*")


# ---------------------------------------------------------------- helpers --

def is_obj(v):
    return isinstance(v, dict)


def is_text(v):
    return isinstance(v, str)


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_finite(v):
    return is_number(v) and math.isfinite(v)


def js_trim(s):
    return s.strip(_JS_SPACE)


def filled(v):
    return isinstance(v, str) and js_trim(v) != ""


def whole(v):
    return is_finite(v) and float(v).is_integer() and v >= 1


def jslen(s):
    """The length of a text as JavaScript counts it (UTF-16 units)."""
    return len(s.encode("utf-16-le", "surrogatepass")) // 2


def utf8_length(s):
    return len(s.encode("utf-8", "surrogatepass"))


def js_keys(d):
    """An object's keys in JavaScript's order: array indexes first, rising."""
    keys = list(d.keys())
    idx = sorted((k for k in keys if isinstance(k, str) and _INDEX.fullmatch(k) and int(k) < 2 ** 32 - 1), key=int)
    return idx + [k for k in keys if k not in idx]


def js_number(x):
    """A number written as JavaScript writes it."""
    if isinstance(x, int) and abs(x) < 2 ** 53:
        return str(x)
    x = float(x)
    if not math.isfinite(x):
        return "NaN" if x != x else ("Infinity" if x > 0 else "-Infinity")
    if x == 0:
        return "0"
    sign = "-" if x < 0 else ""
    t = Decimal(repr(abs(x))).normalize().as_tuple()  # the shortest digits that give the number back
    digits = "".join(map(str, t.digits))
    k = len(digits)
    n = t.exponent + k
    if k <= n <= 21:
        s = digits + "0" * (n - k)
    elif 0 < n <= 21:
        s = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        s = "0." + "0" * (-n) + digits
    else:
        e = n - 1
        s = digits[0] + ("." + digits[1:] if k > 1 else "") + "e" + ("+" if e >= 0 else "-") + str(abs(e))
    return sign + s


def _js_string(s):
    out = ['"']
    for ch in s:
        c = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif c < 0x20 or 0xD800 <= c <= 0xDFFF:
            out.append("\\u%04x" % c)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def show(v):
    """JSON.stringify, as the Board Generator uses it in its messages."""
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if is_number(v):
        return js_number(v) if math.isfinite(v) else "null"
    if isinstance(v, str):
        return _js_string(v)
    if isinstance(v, list):
        return "[" + ",".join(show(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(_js_string(str(k)) + ":" + show(v[k]) for k in js_keys(v)) + "}"
    return "null"


def js_string_of(v):
    """String(v) for a text or a number."""
    return v if isinstance(v, str) else js_number(v)


def key(s):
    return js_string_of(s).lower() if is_number(s) or isinstance(s, str) else str(s).lower()


def thousands(n):
    return "{:,}".format(int(n)) if float(n).is_integer() else js_number(n)


def to_fixed(x, digits):
    """Number.prototype.toFixed: halves go up, on the exact value."""
    q = Decimal(1).scaleb(-digits)
    return str(Decimal(x).quantize(q, rounding=ROUND_HALF_UP))


def megabytes(n):
    return to_fixed(n / 1024 / 1024, 1)


def date_of(s):
    """A real calendar date written YYYY-MM-DD, or None."""
    import datetime
    if not isinstance(s, str):
        return None
    m = _DATE.fullmatch(s)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def when_of(s):
    """A timeline date: YYYY-MM-DD, or with a time. True when valid."""
    if not isinstance(s, str):
        return False
    m = _WHEN.fullmatch(s)
    if not m or not date_of(m.group(1)):
        return False
    if m.group(2) is not None and (int(m.group(2)) > 23 or int(m.group(3)) > 59):
        return False
    return True


def is_web(v):
    return isinstance(v, str) and _WEB.fullmatch(v) is not None


def _lum(h):
    def lin(c):
        return c / 12.92 if c <= 0.03928 else math.pow((c + 0.055) / 1.055, 2.4)
    v = [lin(int(h[i:i + 2], 16) / 255) for i in (1, 3, 5)]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def contrast(a, b):
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


# ---------------------------------------------------------------- the board file --

def limits(f):
    """The safety limits, reported alone."""
    if isinstance(f.get("columns"), list) and len(f["columns"]) > MAX_COLUMNS:
        return [f"There are {len(f['columns'])} columns; the limit is {MAX_COLUMNS}."]
    if isinstance(f.get("cards"), list) and len(f["cards"]) > MAX_CARDS:
        return [f"There are {thousands(len(f['cards']))} cards; the limit is {thousands(MAX_CARDS)}."]
    return []


def button_problems(b, w, own):
    p = []
    if not is_obj(b):
        return [f'{w}: it is not a button; write it as {{"name": "…", "link": "…"}}.']
    if not filled(b.get("name")):
        p.append(f"{w}: the name is missing.")
    elif jslen(b["name"]) > MAX_BUTTON:
        p.append(f"{w}: the name is {jslen(b['name'])} characters; the limit is {MAX_BUTTON}.")
    link = b["link"] if "link" in b and b["link"] != "" else None
    action = b["action"] if "action" in b and b["action"] != "" else None
    if link is None and action is None:
        p.append(f"{w}: it has neither a link nor an action.")
    if link is not None and not is_web(link):
        p.append(f"{w}: the link is not a web address; it must start with https:// or http://.")
    if action is not None and not is_text(action):
        p.append(f"{w}: the action must be text.")
    if "confirm" in b and not is_text(b["confirm"]):
        p.append(f"{w}: the question to confirm must be text.")
    if "ask" in b:
        a = b["ask"]
        if not is_obj(a):
            p.append(f'{w}: the text to ask for ("ask") must be written as {{"label": "…"}}.')
        else:
            if not filled(a.get("label")):
                p.append(f'{w}: the question to ask ("label") is missing.')
            elif jslen(a["label"]) > MAX_ASK:
                p.append(f"{w}: the question to ask is {jslen(a['label'])} characters; the limit is {MAX_ASK}.")
            for k in ("required", "long"):
                if k in a and not isinstance(a[k], bool):
                    p.append(f'{w}: "{k}" in "ask" must be true or false.')
        if action is None:
            p.append(f"{w}: it asks for text but has no action.")
        if "confirm" in b:
            p.append(f"{w}: it has both a question to confirm and a text to ask for; only one is allowed.")
    for k in (("main",) if own else ("main", "strip_only")):
        if k in b and not isinstance(b[k], bool):
            p.append(f'{w}: "{k}" must be true or false.')
    if not own:
        for k in ("kinds", "columns"):
            if k in b and not (isinstance(b[k], list) and all(is_text(x) for x in b[k])):
                p.append(f'{w}: "{k}" must be a list of names.')
    return p


def strip_problems(f):
    p = []
    if "strip" in f:
        s = f["strip"]
        if not is_obj(s):
            p.append('The top strip must be written as {"name": "…"}.')
        else:
            if not filled(s.get("name")):
                p.append("The top strip has no name.")
            if "show" in s and not whole(s["show"]):
                p.append(f'The top strip: "show" is {show(s["show"])}; it must be a whole number, 1 or more.')
    return p


def summary_problems(f):
    if "summary" not in f:
        return []
    s = f["summary"]
    ok = s == "auto" or s == "off" or (isinstance(s, list) and len(s) <= MAX_SUMMARY
                                        and all(filled(x) and jslen(x) <= MAX_SUMMARY_TEXT for x in s))
    if ok:
        return []
    return [f'The summary line ("summary") must be "auto", "off" or a list of up to {MAX_SUMMARY} short texts '
            f'({MAX_SUMMARY_TEXT} characters each).']


def link_pattern_problems(f):
    if "link_pattern" in f:
        lp = f["link_pattern"]
        if not (is_web(lp) and "{id}" in lp):
            return ['The link pattern ("link_pattern") must be a web address with {id} in it.']
    return []


def file_button_problems(f, kinds, names, check_kinds=True):
    """The file's own buttons. ``kinds`` and ``names`` are lower-cased."""
    p = []
    if "buttons" in f and not isinstance(f["buttons"], list):
        p.append('The buttons ("buttons") must be a list.')
    shown = ", ".join(names_shown(f))
    for j, b in enumerate(f["buttons"] if isinstance(f.get("buttons"), list) else [], 1):
        w = f"Button {j}" + (f' ("{b["name"]}")' if is_obj(b) and filled(b.get("name")) else "")
        p.extend(button_problems(b, w, False))
        if not is_obj(b):
            continue
        if check_kinds and isinstance(b.get("kinds"), list):
            for k in b["kinds"]:
                if is_text(k) and key(k) not in kinds:
                    p.append(f'{w}: no card has the kind "{k}".')
        if isinstance(b.get("columns"), list):
            for k in b["columns"]:
                if is_text(k) and key(k) not in names:
                    p.append(f'{w}: the column "{k}" is not defined. Defined: {shown}.')
    return p


def names_shown(f):
    """The defined column names, as the Board Generator lists them."""
    out = []
    for c in f["columns"] if isinstance(f.get("columns"), list) else []:
        if is_obj(c) and filled(c.get("name")) and not any(key(x) == key(c["name"]) for x in out):
            out.append(c["name"])
    return out


def style_problems(f):
    p = []
    st = f["style"] if "style" in f else {}
    if not is_obj(st):
        return ['The style ("style") must be written as {"card_lines": 3, "colours": {…}}.']
    if "card_lines" in st and not (is_number(st["card_lines"]) and st["card_lines"] in (2, 3)):
        p.append(f'Style: lines per card is {show(st["card_lines"])}; it must be 2 or 3.')
    col = dict(COLOURS)
    if "colours" in st and not is_obj(st["colours"]):
        p.append('Style: the colours must be written as {"accent": "#FF5B04", …}.')
    given = st["colours"] if is_obj(st.get("colours")) else {}
    for k in js_keys(given):
        v = given[k]
        if k not in COLOURS:
            p.append(f'Style: "{k}" is not a colour the board has. It has: {", ".join(COLOURS)}.')
            continue
        if not is_text(v) or not _HEX.fullmatch(v):
            p.append(f'Style: the colour "{k}" is {show(v)}; a colour is written as six-digit hex, like #075056.')
            continue
        col[k] = v

    def bg(b):
        return "#FFFFFF" if b == "white" else col[b]
    for t, on in READ_ON:
        worst = on[0]
        for b in on[1:]:
            if contrast(col[t], bg(b)) < contrast(col[t], bg(worst)):
                worst = b
        r = contrast(col[t], bg(worst))
        if r < 4.5:
            where = "white" if worst == "white" else f"the {worst} tint ({col[worst]})"
            p.append(f'Style: "{t}" ({col[t]}) cannot be read on {where}: contrast {to_fixed(r, 1)} to 1; '
                     f"at least 4.5 is needed.")
    r = contrast("#FFFFFF", col["button"])
    if r < 4.5:
        p.append(f'Style: white text cannot be read on "button" ({col["button"]}): contrast {to_fixed(r, 1)} to 1; '
                 f"at least 4.5 is needed.")
    return p


def validate(f, check_kinds=True):
    """Every problem of a board file (already parsed), as the Board Generator lists them."""
    p = []
    if not (is_number(f.get("board")) and f.get("board") == 1):
        p.append('The format version ("board") is missing or is not 1.')
    if not filled(f.get("title")):
        p.append('The board name ("title") must be text.' if "title" in f and not is_text(f["title"])
                 else 'The board name ("title") is missing.')
    cols = f["columns"] if isinstance(f.get("columns"), list) else []
    if not cols:
        p.append('There are no columns ("columns").')
    names = []
    for i, c in enumerate(cols, 1):
        at = f"Column {i}"
        if not is_obj(c):
            p.append(f'{at}: it is not a column; write it as {{"name": "…"}}.')
            continue
        n = c.get("name")
        if not filled(n):
            p.append(f"{at}: the name is missing.")
            continue
        if any(key(x) == key(n) for x in names):
            p.append(f'{at}: the name "{n}" is used twice.')
        else:
            names.append(n)
        for k in ("limit", "show", "total"):
            if k in c and not whole(c[k]) and not (k == "total" and is_number(c[k]) and c[k] == 0):
                p.append(f'{at} ("{n}"): "{k}" is {show(c[k])}; it must be a whole number, 1 or more.')
        if "more_link" in c and not is_web(c["more_link"]):
            p.append(f'{at} ("{n}"): the link for "more" is not a web address.')
    known = [key(x) for x in names]
    shown = ", ".join(names)

    p.extend(strip_problems(f))
    p.extend(summary_problems(f))
    if "today" in f and not date_of(f["today"]):
        p.append(f'"today" is {show(f["today"])}; a date is written YYYY-MM-DD.')
    p.extend(link_pattern_problems(f))

    cards = f["cards"] if isinstance(f.get("cards"), list) else None
    if cards is None:
        p.append('The list of cards ("cards") is missing.')
    ids, kinds, per = set(), set(), {}
    for i, c in enumerate(cards or [], 1):
        if not is_obj(c):
            p.append(f'Card {i}: it is not a card; write it as {{"id": "…", "title": "…", "column": "…"}}.')
            continue
        cid = c.get("id")
        id_ok = (is_text(cid) and cid != "") or is_finite(cid)
        sid = js_string_of(cid) if id_ok else None
        w = f"Card {i}" + (f' (id "{sid}")' if sid else "")
        if not sid:
            p.append(f"{w}: the id must be text or a number." if "id" in c and cid != "" else f"{w}: the id is missing.")
        else:
            if jslen(sid) > MAX_ID:
                p.append(f"{w}: the id is {jslen(sid)} characters; the limit is {MAX_ID}.")
            if sid in ids:
                p.append(f'{w}: the id "{sid}" is used twice.')
            ids.add(sid)
        if not filled(c.get("title")):
            p.append(f"{w}: the title is missing.")
        elif jslen(c["title"]) > MAX_TITLE:
            p.append(f"{w}: the title is {jslen(c['title'])} characters; the limit is {MAX_TITLE}.")
        if not filled(c.get("column")):
            p.append(f"{w}: the column is missing.")
        elif key(c["column"]) not in known:
            p.append(f'{w}: the column "{c["column"]}" is not defined. Defined: {shown}.')
        else:
            per[key(c["column"])] = per.get(key(c["column"]), 0) + 1
        for k in ("kind", "group", "note", "text"):
            if k in c and not is_text(c[k]):
                p.append(f'{w}: "{k}" must be text.')
        if "due" in c and not date_of(c["due"]):
            p.append(f"{w}: the due date is {show(c['due'])}; a date is written YYYY-MM-DD.")
        if "in_strip" in c and not isinstance(c["in_strip"], bool):
            p.append(f'{w}: "in_strip" must be true or false.')
        if c.get("in_strip") is True and "strip" not in f:
            p.append(f"{w}: it is marked for the top strip, but the file has no top strip.")
        if is_text(c.get("note")) and jslen(c["note"]) > MAX_NOTE:
            p.append(f"{w}: the note is {jslen(c['note'])} characters; the limit is {MAX_NOTE}.")
        if is_text(c.get("text")) and jslen(c["text"]) > MAX_TEXT:
            p.append(f"{w}: the text is {thousands(jslen(c['text']))} characters; the limit is {thousands(MAX_TEXT)}.")
        if "link" in c and not is_web(c["link"]):
            p.append(f"{w}: the link is not a web address; it must start with https:// or http://.")
        if filled(c.get("kind")):
            kinds.add(key(c["kind"]))
        if "buttons" in c:
            if not isinstance(c["buttons"], list):
                p.append(f'{w}: "buttons" must be a list.')
            else:
                for j, b in enumerate(c["buttons"], 1):
                    p.extend(button_problems(b, f"{w}, button {j}", True))
    for i, c in enumerate(cols, 1):
        if is_obj(c) and filled(c.get("name")) and whole(c.get("total")) and c["total"] < per.get(key(c["name"]), 0):
            p.append(f'Column {i} ("{c["name"]}"): the total is {js_number(c["total"])}, '
                     f"but the file holds {per[key(c['name'])]} cards in it.")
    p.extend(file_button_problems(f, kinds, known, check_kinds))
    p.extend(style_problems(f))
    return p


def read_problems(f):
    """What the Board Generator's reader says about a parsed board file: the limits alone, or every problem."""
    return limits(f) or validate(f)


# ---------------------------------------------------------------- the card file --

def _longer(v, mx, what):
    if is_text(v) and jslen(v) > mx:
        return f"{what} is {thousands(jslen(v))} characters; the limit is {thousands(mx)}."
    return None


def _link_problem(o, w):
    if "link" in o and not is_web(o["link"]):
        return [f"{w}: the link is not a web address; it must start with https:// or http://."]
    return []


def detail_problems(f):
    """The checks of a card file's text, facts, sections and buttons."""
    p = []

    def push(m):
        if m:
            p.append(m)
    push(_longer(f.get("text"), MAX_CARD_TEXT, "The text"))
    if "facts" in f:
        facts = f["facts"]
        if not isinstance(facts, list):
            p.append('The facts ("facts") must be a list.')
        elif len(facts) > MAX_FACTS:
            p.append(f"There are {len(facts)} facts; the limit is {MAX_FACTS}.")
        else:
            for i, x in enumerate(facts, 1):
                w = f"Fact {i}" + (f' ("{x["label"]}")' if is_obj(x) and filled(x.get("label")) else "")
                if not is_obj(x):
                    p.append(f'{w}: it is not a fact; write it as {{"label": "…", "value": "…"}}.')
                    continue
                if not filled(x.get("label")):
                    p.append(f"{w}: the label is missing.")
                else:
                    push(_longer(x["label"], MAX_LABEL, f"{w}: the label"))
                v = x.get("value")
                if not (filled(v) or is_finite(v)):
                    p.append(f"{w}: the value must be text or a number." if "value" in x and not is_text(v)
                             else f"{w}: the value is missing.")
                else:
                    push(_longer(v, MAX_VALUE, f"{w}: the value"))
                p.extend(_link_problem(x, w))
    if "sections" in f:
        secs = f["sections"]
        if not isinstance(secs, list):
            p.append('The sections ("sections") must be a list.')
        elif len(secs) > MAX_SECTIONS:
            p.append(f"There are {len(secs)} sections; the limit is {MAX_SECTIONS}.")
        else:
            for i, s in enumerate(secs, 1):
                w = f"Section {i}" + (f' ("{s["title"]}")' if is_obj(s) and filled(s.get("title")) else "")
                if not is_obj(s):
                    p.append(f'{w}: it is not a section; write it as {{"title": "…", "type": "…"}}.')
                    continue
                if not filled(s.get("title")):
                    p.append(f"{w}: the title is missing.")
                st = s.get("type")
                if "type" not in s:
                    p.append(f"{w}: the type is missing. Known: {', '.join(SECTION_TYPES)}.")
                elif st not in SECTION_TYPES or not is_text(st):
                    shown = f'"{st}"' if is_text(st) else show(st)
                    p.append(f"{w}: the type {shown} is not known. Known: {', '.join(SECTION_TYPES)}.")
                for k in ("collapsed", "numbered"):
                    if k in s and not isinstance(s[k], bool):
                        p.append(f'{w}: "{k}" must be true or false.')
                if st == "text":
                    if "text" in s and not is_text(s["text"]):
                        p.append(f"{w}: the text must be text.")
                    push(_longer(s.get("text"), MAX_CARD_TEXT, f"{w}: the text"))
                    continue
                if not (is_text(st) and st in SECTION_TYPES) or "items" not in s:
                    continue
                items = s["items"]
                if not isinstance(items, list):
                    p.append(f'{w}: "items" must be a list.')
                    continue
                if len(items) > MAX_ITEMS:
                    p.append(f"{w}: there are {len(items)} items; the limit is {MAX_ITEMS}.")
                    continue
                for j, it in enumerate(items, 1):
                    iw = f"{w}, item {j}"
                    if not is_obj(it):
                        p.append(f'{iw}: it is not an item; write it as {{"text": "…"}}.')
                        continue
                    if st == "timeline":
                        if "when" not in it:
                            p.append(f'{iw}: the date ("when") is missing.')
                        elif not when_of(it["when"]):
                            p.append(f'{iw}: the date ("when") is {show(it["when"])}; a date is written YYYY-MM-DD, '
                                     f"or YYYY-MM-DD HH:MM with a time.")
                        if "who" in it and not is_text(it["who"]):
                            p.append(f'{iw}: "who" must be text.')
                    if not filled(it.get("text")):
                        p.append(f"{iw}: the text must be text." if "text" in it and not is_text(it["text"])
                                 else f"{iw}: the text is missing.")
                    else:
                        push(_longer(it["text"], MAX_CARD_TEXT, f"{iw}: the text"))
                    if st == "checklist" and not isinstance(it.get("done"), bool):
                        p.append(f'{iw}: "done" is {show(it["done"])}; it must be true or false.' if "done" in it
                                 else f'{iw}: "done" is missing; it must be true or false.')
                    p.extend(_link_problem(it, iw))
    if "buttons" in f:
        if not isinstance(f["buttons"], list):
            p.append('The buttons ("buttons") must be a list.')
        else:
            for j, b in enumerate(f["buttons"], 1):
                w = f"Button {j}" + (f' ("{b["name"]}")' if is_obj(b) and filled(b.get("name")) else "")
                p.extend(button_problems(b, w, True))
    return p


def validate_card(f, opened=None):
    """Every problem of a card file (already parsed), as the Board Generator lists them."""
    p = []

    def push(m):
        if m:
            p.append(m)
    if not (is_number(f.get("card")) and f.get("card") == 1):
        p.append('The format version ("card") is missing or is not 1.')
    if not filled(f.get("title")):
        p.append('The card\'s title ("title") must be text.' if "title" in f and not is_text(f["title"])
                 else 'The card\'s title ("title") is missing.')
    else:
        push(_longer(f["title"], MAX_TITLE, "The card's title"))
    cid = f.get("id")
    if not ((is_text(cid) and cid != "") or is_finite(cid)):
        p.append('The card\'s id ("id") must be text or a number.' if "id" in f and cid != ""
                 else 'The card\'s id ("id") is missing.')
    elif opened is not None and js_string_of(cid) != js_string_of(opened):
        p.append(f'The id is "{js_string_of(cid)}", but the card that was opened is "{js_string_of(opened)}".')
    for k in ("kind", "column", "group", "note", "text"):
        if k in f and not is_text(f[k]):
            p.append(f'"{k}" must be text.')
    push(_longer(f.get("note"), MAX_NOTE, "The note"))
    if "due" in f and not date_of(f["due"]):
        p.append(f"The due date is {show(f['due'])}; a date is written YYYY-MM-DD.")
    if "link" in f and not is_web(f["link"]):
        p.append("The link is not a web address; it must start with https:// or http://.")
    p.extend(detail_problems(f))
    return p

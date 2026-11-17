# Using the Board Extractor

For someone using it for the first time. The [front page](../README.md) says what it does; the [input guide](input-format.md) says how to write the settings and the records.

The Board Extractor sits between a program that keeps cards and the [Board Generator](https://github.com/chalouhi/board-generator) (release 1.1) that draws them. The program hands it its settings and its card records; it gives back the **board file** (every card, reduced) and the **card file** (one card, in full), checked and ready to draw.

## 1 · Inside a Python program

Python 3.10 or later; nothing else. One install step, at a numbered release:

```bash
pip install "git+https://github.com/chalouhi/board-extractor@v1.0.0"
```

(From a copy of the repository, `import board_extractor` works with the repository's folder on the path, with no install at all.)

```python
from board_extractor import board_file, card_file, ExtractorError

text = board_file(settings, records, totals={"done": 48}, today="2026-03-10")
text = card_file(settings, record)
```

**`board_file(settings, records, *, totals=None, today=None, group=None, kind=None, waiting=False)`** returns the board file as JSON text.

| Argument | Meaning |
|---|---|
| `settings` | The settings: a dict, or the settings file's text. |
| `records` | The records: a list of dicts; or a records file as a dict, `{"records": […], "totals": {…}}`; or a records file's text. |
| `totals` | The true number of cards per stage, when only some were handed over: `{"done": 48}`. Give totals here or in the records file, not both. |
| `today` | The day due dates are judged by, `"YYYY-MM-DD"` or a `datetime.date`. Left out, the board file has no `today` and the Board Generator uses the day it draws. |
| `group`, `kind` | Only the cards of this group, or of this kind (exact text). |
| `waiting` | `True`: only the cards waiting for a person. |

**`card_file(settings, record)`** returns the card file of one record, as JSON text. `record` is a dict, or its text, holding the record with its detail (`text`, `facts`, `sections`, `buttons`).

**On a problem**, both raise `ExtractorError`, a `ValueError` whose `problems` attribute lists every problem in plain words (and whose text is those lines). Nothing else is ever raised for a wrong input; catch it and carry on.

```python
try:
    text = board_file(settings, records)
except ExtractorError as e:
    log(e.problems)        # ['Record 2 (id "48"): the stage "review" is not in the settings. …', …]
```

**What it never does.** It keeps nothing between calls, writes no file, opens no connection, and never reads the clock: the same input gives the same text, character for character. It never changes the settings or records it is given.

### Fitting it into a service

The service reads its own cards, decides each card's buttons by its own rules, and serves the two files to its page:

```python
SETTINGS = json.load(open("board-settings.json"))

def board_json(group=None):                                # GET /board.json
    rows = db.open_cards() + db.latest_done(3)
    return board_file(SETTINGS, [as_record(r) for r in rows], totals={"done": db.count_done()}, group=group)

def card_json(card_id):                                    # GET /cards/<id>.json
    r = db.card(card_id)
    return card_file(SETTINGS, dict(as_record(r), text=r.text, sections=sections_of(r), buttons=buttons_for(r)))
```

`as_record` turns one of the service's rows into a record (section 3 of the [input guide](input-format.md)). The page hands both files to the Board Generator with `getCard` and `refresh`; [`example/`](../example/) does exactly this.

## 2 · The command

```bash
board-extractor <settings> <records> [--out <board.json>] [--today YYYY-MM-DD] [--group <name>] [--kind <name>] [--waiting]
board-extractor <settings> <record> [--out <card.json>]
```

After the install step the command is `board-extractor`. From a copy of the repository with no install step, it is `bin/board-extractor` (or `python3 -m board_extractor` from the repository's folder). It needs no network.

```bash
board-extractor samples/shop/settings.json samples/shop/records.json --today 2026-03-10 --out board.json
board-extractor samples/shop/settings.json samples/shop/card-43.record.json --out card-43.json
```

A records file (one with a `"records"` list) gives the board file; a file holding one record gives the card file.

| Option | Meaning |
|---|---|
| `--out <path>` | Write the file there. Left out (or `-`): print it. The file is written whole or not at all. |
| `--today <date>` | The day due dates are judged by, `YYYY-MM-DD`. Board file only. |
| `--group <name>` | Only the cards of one group. Board file only. |
| `--kind <name>` | Only the cards of one kind. Board file only. |
| `--waiting` | Only the cards waiting for a person. Board file only. |
| `--version`, `--help` | Print the version, or the help. |

| Exit code | Meaning |
|---|---|
| `0` | Done. |
| `1` | The input has problems. Nothing is written; the problems are printed one per line (on standard error). |
| `2` | Used wrongly (a missing file, an unknown option, a filter with a single record). Nothing is written. |

## 3 · The example board

A tiny service with made-up cards, the extractor inside it, and a page drawn by the Board Generator 1.1, to try the whole chain on one machine. It needs Python 3.10 or later and no network; nothing is installed.

```bash
python3 example/serve.py
```

Then open <http://127.0.0.1:8400/>. `--port <n>` picks another port; `--db <file>` another database file. Ctrl+C stops it.

- It holds the 16 cards of the shop sample in a small database file of its own, `example/shop.db`, made at the first start.
- The page shows the board ("Shop relaunch", seen from 10 Mar 2026), opens a card in full, and has a Refresh button.
- Its buttons work. **Accept** (cards in Checking) moves a card to Done. **Send back** (cards in Checking) asks why, then moves the card to Ready with the reason added to its notes. **Add note** adds a note and keeps the card open.
- Stopping and starting it again keeps the changes. To put it back to the sample, even while it runs:

```bash
python3 example/reset.py
```

The service listens on this machine only (127.0.0.1); its page is allowed to talk to that service and nothing else.

## 4 · What you get

- **The board file**: JSON, version 1 of the Board Generator's [board file](https://github.com/chalouhi/board-generator/blob/v1.1/docs/file-format.md). `board`, `title`, `today` when given, then the settings' `link_pattern`, `strip`, `summary` and `style` as they are, the `columns`, the `cards`, and the settings' `buttons`. Each card carries `id`, `title`, `column`, and when the record has them `kind`, `group`, `due`, `note`, `link`, `in_strip` and its own `buttons`. At most 5 MB.
- **The card file**: JSON, the Board Generator's [card file](https://github.com/chalouhi/board-generator/blob/v1.1/docs/file-format.md#the-card-file). `card`, `id`, `title`, `column`, the record's `kind`, `group`, `due`, `note`, `link`, and its `text`, `facts`, `sections` and `buttons` as they are. At most 1 MB.

Both are UTF-8 JSON, indented by two spaces, with a newline at the end. Every file is one the Board Generator 1.1 reads without a problem.

## 5 · How it behaves

- **Columns.** Every column of the settings is listed, in their order, even when empty or when a filter leaves it empty.
- **Order.** Strip cards first, then each column's cards. Within a column, rising `order`, then the order the records arrived in. A column with `keep_latest` keeps its most recently `changed` records, newest first; records with no `changed` come last.
- **Waiting cards** go in the top strip when the settings have one, and stay in their column when they do not.
- **Totals.** A column's `total` is written only when its count (the totals given for its stages, or else the records that arrived) is greater than the cards the file carries for it. Never with a filter on.
- **Text is text.** Every text from a record is copied exactly: never trimmed, shortened, escaped or read as HTML.
- **Buttons with `kinds`.** The Board Generator refuses a button naming a kind no card on the board has. So a settings button keeps only the kinds some card on this board has, and a button left with none is not written. Everything else in a button is copied as it is.
- **Wrong input.** Nothing is returned or written; every problem is listed at once, settings first, then records, each saying where it is: `Settings: …`, `Settings, button 2 ("Discuss"): …`, `Record 6 (id "50"): …`, `Records: …` (the totals). Section 5 of the [input guide](input-format.md) lists them all.
- **Its own check.** Before returning, it checks the file it made by every rule of the Board Generator's board file and card file guides.
- **Limits.** More than 5,000 records, a board file over 5 MB or a card file over 1 MB is refused with one message saying which limit was passed. A board of 5,000 records is made in well under a second.

## 6 · Checking a copy

The tests need no network. Python's tests need nothing but Python 3.10 or later:

```bash
python3 -m unittest discover -s tests
```

The Node tests (Node 18 or later, and `python3`) run the Board Generator's own reader on every file the extractor writes, and compare the extractor's checks with the reader's, message for message, on thousands of files:

```bash
node --test tests/*.test.js
```

The browser test plays the example board in Chromium, in the official Playwright container with no network:

```bash
tests/browser/run-offline.sh <folder holding node_modules/playwright>
```

`node tools/make-picture.js` remakes `docs/example.svg`, the front page's picture; a test checks it is up to date.

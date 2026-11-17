# The input: settings and card records

Version 1.

This page is for anyone whose program keeps work as cards and wants them shown by the [Board Generator](https://github.com/chalouhi/board-generator). Give the Board Extractor two things, a **settings file** written once per board and the **card records** read fresh each time, and it writes the board file and the card file the Board Generator draws. How to call it is in the [user guide](guide.md).

## 1 · The words

| Word | Meaning |
|---|---|
| **Record** | One card as the program knows it, in the plain shape of section 3. |
| **Stage** | Where a card stands, in the program's own word, for example `doing`. |
| **Settings** | How this board is to be shown: its title, which stages go into which column, limits, the top strip, colours. |
| **Board file** | What the Board Generator draws as the board. Every card, in reduced form. |
| **Card file** | What the Board Generator shows when one card is opened. One card, in full. |

## 2 · The settings file

One JSON file per board.

| Field | Required | Meaning |
|---|---|---|
| `extractor` | yes | The format version. Always `1`. |
| `title` | yes | The board's name. |
| `columns` | yes | The columns, in order (below). At least one, at most 12. |
| `strip` | no | The top strip: `name`, and optionally `show`. Left out: no strip, and a waiting card stays in its column. |
| `summary`, `link_pattern`, `style`, `buttons` | no | Copied into the board file as they are. See the Board Generator's [board file guide](https://github.com/chalouhi/board-generator/blob/v1.1/docs/file-format.md). |

### A column

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | The column's name on the board. Different for every column. |
| `stages` | yes | The stages whose cards go into this column. A stage belongs to one column only. A stage in no column is a mistake when a record has it. |
| `limit`, `show`, `more_link` | no | Copied into the board file. |
| `keep_latest` | no | A whole number. When more records than this arrive for the column, only the most recently changed are kept, newest first. For a column of finished work. |

## 3 · A record

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | The card's number or code, 1 to 12 characters, different for every record. |
| `title` | yes | The card's title, up to 200 characters. |
| `stage` | yes | The card's stage. Decides its column. |
| `kind`, `group`, `due`, `note`, `link` | no | As in the board file. `due` is a date, `YYYY-MM-DD`. |
| `waiting` | no | `true`: the card waits for a person and goes in the top strip. |
| `order` | no | A number. Cards in a column are put in rising order. Left out: the order the records arrived in. |
| `changed` | no | When the card last changed, as a date (`YYYY-MM-DD`) or a date and time (`YYYY-MM-DDTHH:MM`, seconds and a zone such as `Z` or `+03:00` allowed). Used by `keep_latest`. |
| `buttons` | no | The buttons this card may show, as the program's own rules decide. |
| `text`, `facts`, `sections` | no | The card's full detail. Used only for the card file; never put in the board file. See the [card file guide](https://github.com/chalouhi/board-generator/blob/v1.1/docs/file-format.md#the-card-file). |

Records are handed over with optional **totals**: the true number of cards in a stage, when the program hands over only some of them. Example: 5 finished cards handed over, `"totals": { "done": 48 }`.

A **records file** holds both:

```json
{ "records": [ { "id": "1", "title": "Book the van", "stage": "doing" } ],
  "totals": { "done": 48 } }
```

A **record file** holds one record with its detail, and gives the card file.

## 4 · What the extractor writes

**The board file**

- The cards in the strip first, then each column's cards in column order.
- A card's `column` is the name of the column that holds its stage.
- Within a column, cards are in rising `order`; records without `order` keep the order they arrived in, after those that have one. A column with `keep_latest` is ordered newest first instead; records with no `changed` come last.
- A column's `total` is written only when its count is greater than the cards the file carries for it. The count adds up, for each of its stages, the total given for it, or else the number of records that arrived with it.
- A card never carries its `text`, `facts` or `sections`.
- `today` is written when a date is given.
- A button in the settings that names `kinds` keeps only the kinds some card on this board has, since the Board Generator refuses a button naming a kind no card has; a button left with none of its kinds is not written, as it could show on no card.

**The card file**

- One record with its detail gives one card file: its fields, its `column`, and its `text`, `facts`, `sections` and `buttons` as they are.

**Filters**, applied to the records before the board file is written: only one `group`; only one `kind`; only the waiting cards. Every column is still listed. Totals are not applied when a filter is on.

**The check.** Before anything is returned, the extractor checks its own output by the Board Generator's rules. Wrong settings or records produce nothing, and every problem is listed at once, in plain words, saying where it is. Example: `Record 2 (id "48"): the stage "review" is not in the settings. In the settings: idea, ready, doing, checking, rework, done.`

## 5 · Problems the extractor reports

In the settings: missing or wrong `extractor` version · missing `title` · no columns, or more than 12 · a column with no `name`, a name used twice, or no stages · a stage listed in two columns · `limit`, `show` or `keep_latest` that is not a whole number of 1 or more · everything the board file guide lists for `strip`, `summary`, `link_pattern`, `style` and `buttons`.

In the records: a record with no `id`, no `title` or no `stage` · an `id` longer than 12 characters, or used twice · a stage that is not in the settings · a `due` or `changed` that is not a date · `order` that is not a number · `waiting` that is not true or false · a total for a stage that is not in the settings, or smaller than the records that arrived for it · more than 5,000 records (reported alone) · everything the card file guide lists for `text`, `facts`, `sections` and `buttons`.

In what it writes: a board file larger than 5 MB, or a card file larger than 1 MB (reported alone).

## 6 · Smallest example

Settings:

```json
{ "extractor": 1, "title": "House move",
  "columns": [ { "name": "To do", "stages": ["todo"] }, { "name": "Doing", "stages": ["doing"] }, { "name": "Done", "stages": ["done"] } ] }
```

Records:

```json
{ "records": [ { "id": "1", "title": "Book the van", "stage": "doing" },
               { "id": "2", "title": "Pack the kitchen", "stage": "todo" } ] }
```

Board file:

```json
{ "board": 1, "title": "House move",
  "columns": [ { "name": "To do" }, { "name": "Doing" }, { "name": "Done" } ],
  "cards": [ { "id": "2", "title": "Pack the kitchen", "column": "To do" },
             { "id": "1", "title": "Book the van", "column": "Doing" } ] }
```

## 7 · The samples

| File | What it proves |
|---|---|
| `samples/shop/settings.json`, `records.json` | A strip, two stages in one column, limits, `keep_latest` with a total of 48, file buttons and a card's own buttons; 16 records handed over shuffled. Gives `expected/shop.board.json` with today as 10 Mar 2026. |
| `samples/shop/card-43.record.json` | One record with its detail. Gives `expected/shop.card-43.json`. |
| `samples/broken/` | Six mistakes between the settings and the records, listed in `expected/broken.problems.txt`. |

All cards in them are made up.

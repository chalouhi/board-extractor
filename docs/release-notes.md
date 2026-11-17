# Release notes

## 1.0 · 2026-11

The first release.

- **The part**, for Python 3.10 or later with nothing else: `board_file(settings, records, …)` and `card_file(settings, record)` return the Board Generator 1.1's board file and card file as JSON text. Filters by group, by kind, and for the waiting cards. A wrong input raises one `ExtractorError` holding every problem.
- **The command**, `board-extractor`, does the same from files, for any other program or person.
- **The check.** Wrong settings or records give nothing and a list of every problem, in plain words. Every file written is checked by the Board Generator's own rules first; the tests hold those rules to the Board Generator's reader, message for message.
- **The example board**, `python3 example/serve.py`: a tiny service with made-up cards, the extractor inside it, and a page drawn by the Board Generator 1.1, on one machine with no network.

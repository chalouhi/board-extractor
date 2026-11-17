"""The command: settings and records files in, the board file (or a card file) out.

    board-extractor <settings.json> <records.json> [--out <board.json>] [--today YYYY-MM-DD]
                    [--group <name>] [--kind <name>] [--waiting]
    board-extractor <settings.json> <record.json> [--out <card.json>]

Exit code 0 when done, 1 when the input has problems (nothing is written; the
problems are printed one per line), 2 when the command is used wrongly.
"""

import json
import os
import sys
import tempfile

from . import __version__
from .extract import ExtractorError, board_file, card_file

USAGE = """\
Usage: board-extractor <settings> <records> [options]
       board-extractor <settings> <record>  [--out <path>]

  <settings>        the board's settings file (JSON; see docs/input-format.md)
  <records>         a records file: {"records": [...], "totals": {...}}
                    -> writes the board file
  <record>          one record with its detail, in place of the records file
                    -> writes the card file

  --out <path>      write the file there (default: print it)
  --today <date>    the day due dates are judged by, YYYY-MM-DD (board file only)
  --group <name>    only the cards of one group (board file only)
  --kind <name>     only the cards of one kind (board file only)
  --waiting         only the cards that wait for a person (board file only)
  --version         print the version
  -h, --help        print this help

Exit code 0 when done; 1 when the input has problems (nothing is written, the
problems are printed one per line); 2 when the command is used wrongly."""


class UsageError(Exception):
    pass


def _args(argv):
    o = {"files": [], "out": None, "today": None, "group": None, "kind": None, "waiting": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            o["help"] = True
        elif a == "--version":
            o["version"] = True
        elif a == "--waiting":
            o["waiting"] = True
        elif a in ("--out", "-o", "--today", "--group", "--kind"):
            if i + 1 >= len(argv):
                raise UsageError(f"{a} needs a value")
            name = "out" if a == "-o" else a[2:]
            if o[name] is not None:
                raise UsageError(f"{a} is given twice")
            o[name] = argv[i + 1]
            i += 1
        elif a.startswith("-") and a != "-":
            raise UsageError(f"unknown option {a}")
        else:
            o["files"].append(a)
        i += 1
    if o.get("help") or o.get("version"):
        return o
    if len(o["files"]) != 2:
        raise UsageError("give two files: the settings and the records (or one record)")
    return o


def _read(path, what):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError as e:
        raise UsageError(f"cannot read the {what} file {path}: {e.strerror or e}")


def _write(path, text):
    """Writes the whole file or nothing: a temporary file next to it, then renamed."""
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".board-extractor-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _is_one_record(raw):
    """A file holding one record (and no "records" list) gives the card file."""
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        return False
    return isinstance(data, dict) and "records" not in data


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        o = _args(argv)
        if o.get("help"):
            print(USAGE)
            return 0
        if o.get("version"):
            print(__version__)
            return 0
        settings = _read(o["files"][0], "settings")
        records = _read(o["files"][1], "records")
        one = _is_one_record(records)
        if one and (o["today"] or o["group"] or o["kind"] or o["waiting"]):
            raise UsageError("--today, --group, --kind and --waiting are for the board file; "
                             "a single record gives the card file")
        if o["out"] is not None and o["out"] != "-" and os.path.isdir(o["out"]):
            raise UsageError(f"--out names a folder: {o['out']}")
    except UsageError as e:
        print(f"board-extractor: {e}", file=sys.stderr)
        print("Try board-extractor --help.", file=sys.stderr)
        return 2
    try:
        if one:
            text = card_file(settings, records)
        else:
            text = board_file(settings, records, today=o["today"], group=o["group"], kind=o["kind"],
                              waiting=o["waiting"])
    except ExtractorError as e:
        for line in e.problems:
            print(line, file=sys.stderr)
        return 1
    if o["out"] is None or o["out"] == "-":
        sys.stdout.write(text)
        sys.stdout.flush()
    else:
        try:
            _write(o["out"], text)
        except OSError as e:
            print(f"board-extractor: cannot write {o['out']}: {e.strerror or e}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

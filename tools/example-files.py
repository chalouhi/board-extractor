#!/usr/bin/env python3
"""Prints, as JSON, the files the example board serves when it is new: {"board": text, "cards": {id: text}}.
Used by the tests and by tools/make-picture.js. Writes only a temporary database, then removes it."""

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "example"))

from board_extractor import board_file, card_file  # noqa: E402
import serve  # noqa: E402
from store import Store  # noqa: E402

with tempfile.TemporaryDirectory() as d:
    store = Store(os.path.join(d, "shop.db"))
    data = store.records()
    out = {"board": board_file(serve.SETTINGS, data, today=serve.TODAY),
           "cards": {r["id"]: card_file(serve.SETTINGS, store.record(r["id"])) for r in data["records"]}}
print(json.dumps(out))

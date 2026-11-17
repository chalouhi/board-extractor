import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def path(*parts):
    return os.path.join(ROOT, *parts)


def text(*parts):
    with open(path(*parts), encoding="utf-8") as f:
        return f.read()


def load(*parts):
    return json.loads(text(*parts))


def lines(*parts):
    return text(*parts).splitlines()


def settings(**over):
    """A small valid settings dict."""
    s = {"extractor": 1, "title": "House move", "strip": {"name": "Needs you"},
         "columns": [{"name": "To do", "stages": ["todo"]}, {"name": "Doing", "stages": ["doing"]},
                     {"name": "Done", "stages": ["done"]}]}
    s.update(over)
    return s

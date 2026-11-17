"""For tests/parity.test.js: reads a list of cases as JSON on stdin and prints, for each, the problems the
Python rules find: {"board": file} -> rules.read_problems, {"card": file, "opened": id} -> rules.validate_card."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from board_extractor import rules  # noqa: E402

out = []
for case in json.load(sys.stdin):
    if "board" in case:
        out.append(rules.read_problems(case["board"]))
    else:
        out.append(rules.validate_card(case["card"], case.get("opened")))
sys.stdout.write(json.dumps(out))

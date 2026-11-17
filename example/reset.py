#!/usr/bin/env python3
"""Puts the example board back to the shop sample. Works while the example is running.

    python3 example/reset.py [--db <file>]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from store import DEFAULT_DB, seed  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="Put the example board back to the sample.")
    ap.add_argument("--db", default=DEFAULT_DB, help="the database file (default example/shop.db)")
    a = ap.parse_args(argv)
    seed(a.db)
    print("The example board is back to the sample. Reload the page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Fetch BFCL data files for the simple_python category.

BFCL's official `bfcl-eval` PyPI package pins numpy==1.26.4,
which has no Python 3.13 wheel. The data itself, though, is a
handful of small JSONL files we can fetch directly from the
Gorilla repo and vendor under `data/bfcl/` (gitignored).

Idempotent: skips files that already exist unless `--force`.

Usage:
    python3 scripts/download_bfcl.py
    python3 scripts/download_bfcl.py --force
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "bfcl"

_BASE_URL = (
    "https://raw.githubusercontent.com/ShishirPatil/gorilla/main/"
    "berkeley-function-call-leaderboard/bfcl_eval/data"
)

# (relative-path-in-data-dir, remote URL)
_FILES: list[tuple[str, str]] = [
    (
        "BFCL_v4_simple_python.json",
        f"{_BASE_URL}/BFCL_v4_simple_python.json",
    ),
    (
        "possible_answer/BFCL_v4_simple_python.json",
        f"{_BASE_URL}/possible_answer/BFCL_v4_simple_python.json",
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true",
        help="Re-download even if files already exist.",
    )
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for relpath, url in _FILES:
        out = DATA_DIR / relpath
        if out.exists() and not args.force:
            print(f"[skip] {out.relative_to(REPO_ROOT)} exists")
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        print(f"[fetch] {url}")
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = resp.read()
        except urllib.error.URLError as e:
            print(f"[error] {e}", file=sys.stderr)
            return 1
        out.write_bytes(data)
        print(f"[write] {out.relative_to(REPO_ROOT)} ({len(data):,} bytes)")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

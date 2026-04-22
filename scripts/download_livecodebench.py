#!/usr/bin/env python3
"""Fetch and sanitise a LiveCodeBench release file.

LCB releases a rolling competitive-programming benchmark on
HuggingFace as `livecodebench/code_generation_lite`. Each release
adds an incremental file (`test.jsonl`, `test2.jsonl`, ...,
`test6.jsonl`), indexed by contest date. By default we fetch the
most recent file, which contains the problems least likely to be
present in the subject models' training data.

**Why this script rewrites rather than just downloads.** Upstream
encodes `private_test_cases` as base64 -> zlib -> pickle -> json.
Calling `pickle.loads` on downloaded bytes runs arbitrary code at
load time; we do not want that happening inside the runtime
adapter on every import. Instead this script does the decode once,
at the trust boundary (you running the fetcher, against the
signed HuggingFace CDN), and writes out a clean JSON form with
`private_tests` as a plain array. The runtime adapter then loads
only JSON. If a third party swaps a poisoned payload into the
HuggingFace path, the exploit would fire here rather than on every
benchmark run; and you can choose whether to re-run this script.

Idempotent: skips the rewritten output file if it exists unless
`--force` is passed. Also idempotent on the raw download: the
upstream JSONL is cached in `data/livecodebench/.raw/` and reused
when `--force` is not set.

Usage:
    python3 scripts/download_livecodebench.py
    python3 scripts/download_livecodebench.py --release test5
    python3 scripts/download_livecodebench.py --force
"""

from __future__ import annotations

import argparse
import base64
import json
import pickle
import sys
import urllib.error
import urllib.request
import zlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "livecodebench"
RAW_DIR = DATA_DIR / ".raw"

_RELEASES: dict[str, str] = {
    # Latest-first ordering. Each entry maps `--release` to the
    # upstream filename. See the dataset README at
    # https://huggingface.co/datasets/livecodebench/code_generation_lite
    # for the incremental-vs-cumulative semantics: each file contains
    # only the problems added in that release.
    "test6": "test6.jsonl",
    "test5": "test5.jsonl",
    "test4": "test4.jsonl",
    "test3": "test3.jsonl",
    "test2": "test2.jsonl",
    "test":  "test.jsonl",
}
_DEFAULT_RELEASE = "test6"

_HF_BASE = (
    "https://huggingface.co/datasets/livecodebench/code_generation_lite/"
    "resolve/main"
)


def _download(url: str, out_path: Path) -> None:
    print(f"[fetch] {url}")
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", "0"))
            print(f"[fetch]  size: {total:,} bytes" if total else "[fetch]  streaming")
            data = resp.read()
    except urllib.error.URLError as e:
        raise SystemExit(f"[error] {e}")
    out_path.write_bytes(data)
    print(f"[write] {out_path.relative_to(REPO_ROOT)} ({len(data):,} bytes)")


def _decode_private_tests(encoded: str) -> list[dict[str, Any]]:
    """LCB payload: b64(zlib(pickle(json.dumps(tests))))."""
    decoded = base64.b64decode(encoded)
    decompressed = zlib.decompress(decoded)
    # pickle runs arbitrary code; trusted only in this one-shot,
    # user-invoked, HF-CDN-fetched context. See module docstring.
    json_str = pickle.loads(decompressed)
    if not isinstance(json_str, str):
        raise ValueError(
            f"expected pickle payload to be a str, got {type(json_str).__name__}"
        )
    tests: list[dict[str, Any]] = json.loads(json_str)
    return tests


def _rewrite(raw_path: Path, clean_path: Path) -> None:
    """Decode each record's private tests, drop the heavy encoded
    field, write a clean JSONL out.

    Also counts stdin vs functional vs mixed problems for a summary
    line -- useful because the adapter only supports stdin in v1.
    """
    print(f"[rewrite] {raw_path.relative_to(REPO_ROOT)}")
    n_total = 0
    n_stdin_only = 0
    n_functional_only = 0
    n_mixed = 0

    with raw_path.open() as fin, clean_path.open("w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            n_total += 1
            rec = json.loads(line)
            public_tests = json.loads(rec["public_test_cases"])
            private_tests = _decode_private_tests(rec["private_test_cases"])

            testtypes = {t["testtype"] for t in (public_tests + private_tests)}
            if testtypes == {"stdin"}:
                n_stdin_only += 1
            elif testtypes == {"functional"}:
                n_functional_only += 1
            else:
                n_mixed += 1

            clean = {
                "question_id": rec["question_id"],
                "question_title": rec["question_title"],
                "question_content": rec["question_content"],
                "platform": rec["platform"],
                "contest_id": rec["contest_id"],
                "contest_date": rec["contest_date"],
                "difficulty": rec["difficulty"],
                "starter_code": rec.get("starter_code", ""),
                "public_tests": public_tests,
                "private_tests": private_tests,
                "metadata": rec.get("metadata", "{}"),
            }
            fout.write(json.dumps(clean) + "\n")

    print(f"[rewrite] {n_total} records")
    print(f"[rewrite]   stdin-only      : {n_stdin_only}")
    print(f"[rewrite]   functional-only : {n_functional_only}")
    print(f"[rewrite]   mixed           : {n_mixed}")
    print(f"[write] {clean_path.relative_to(REPO_ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release",
        default=_DEFAULT_RELEASE,
        choices=sorted(_RELEASES.keys()),
        help=f"Release file to fetch (default: {_DEFAULT_RELEASE}).",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-fetch and re-rewrite even if outputs exist.",
    )
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    raw_name = _RELEASES[args.release]
    raw_path = RAW_DIR / raw_name
    clean_path = DATA_DIR / f"{args.release}.jsonl"

    if clean_path.exists() and not args.force:
        print(f"[skip] {clean_path.relative_to(REPO_ROOT)} exists")
        return 0

    if not raw_path.exists() or args.force:
        _download(f"{_HF_BASE}/{raw_name}", raw_path)
    else:
        print(f"[skip] {raw_path.relative_to(REPO_ROOT)} cached")

    _rewrite(raw_path, clean_path)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

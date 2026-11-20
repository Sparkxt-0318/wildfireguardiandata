#!/usr/bin/env python3
"""Fail if a key value appears in the repository (tracked files, or staged files with --staged).

Two checks: (1) every value in keys.env (when that file can be found) must not occur in any file;
(2) known token shapes (Hugging Face, JWT, data.go.kr, NASA FIRMS-style assignments) must not occur.
Prints only file names and the key NAME or pattern name, never a value.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from firewitness.core.keys import load_keys  # noqa: E402

PATTERNS = {
    "huggingface-token": re.compile(r"\bhf_[A-Za-z0-9]{30,}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    # upper-case GUIDs (IRWIN, WFIGS ids) are hex only; a real key of this shape contains a letter beyond F
    "data-go-kr-key": re.compile(r"\b(?=[A-Z0-9-]*[G-Z])[A-Z0-9]{8}(?:-[A-Z0-9]{4}){3}-[A-Z0-9]{10,12}\b"),
    "firms-key-assignment": re.compile(r"(?i)(?:firms|map)_?(?:map_)?key\s*[=:]\s*['\"]?[0-9a-f]{32}\b"),
    "github-token": re.compile(r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{30,}"),
}


def files(staged: bool) -> list[Path]:
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"] if staged else ["git", "ls-files"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
    return [ROOT / f for f in out if f]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--keys", default=None)
    a = ap.parse_args()
    keys = {k: v for k, v in load_keys(a.keys).items() if len(v) >= 8}
    bad: list[str] = []
    for f in files(a.staged):
        if f.name == "check_keys.py" or not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = f.relative_to(ROOT)
        for name, val in keys.items():
            if val in text:
                bad.append(f"{rel}: contains the value of {name}")
        for pname, rx in PATTERNS.items():
            if rx.search(text):
                bad.append(f"{rel}: matches token pattern {pname}")
    if bad:
        print("KEY CHECK FAILED:\n  " + "\n  ".join(bad), file=sys.stderr)
        return 1
    print(f"key check ok ({len(keys)} key values and {len(PATTERNS)} patterns checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

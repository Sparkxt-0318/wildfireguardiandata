"""Shared settings for the early growth rate (track growth). Every number lives in config/growth_us.json."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CFG_FILE = Path(__file__).resolve().parent.parent / "config" / "growth_us.json"
CFG = json.loads(CFG_FILE.read_text())


def load_region() -> dict:
    from firewitness.core import load_region as lr
    return lr(Path(__file__).resolve().parent.parent, "us")


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def canonical_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

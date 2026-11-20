"""Append-only index of raw downloads kept outside the repo (RAW_ROOT/INDEX.md)."""
from __future__ import annotations
import datetime as _dt
import hashlib
import os
from pathlib import Path

RAW_ROOT = Path(os.environ.get("FIREWITNESS_RAW", "/home/user/wildfire 3 (1)/firewitness_raw"))


def sha256_path(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def register(path: Path, source: str, note: str = "") -> None:
    """Add one line to the raw index. Never records credentials: callers pass a bare URL."""
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    idx = RAW_ROOT / "INDEX.md"
    if not idx.exists():
        idx.write_text("# firewitness_raw index\n\n| file | bytes | sha256 | source | fetched (UTC) | note |\n|---|---|---|---|---|---|\n")
    rel = os.path.relpath(path, RAW_ROOT)
    row = "| {} | {} | {} | {} | {} | {} |\n".format(
        rel, path.stat().st_size, sha256_path(path), source,
        _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), note)
    with open(idx, "a") as fh:
        fh.write(row)

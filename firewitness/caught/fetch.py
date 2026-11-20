"""Raw download helper: every raw file goes under "wildfire 3 (1)/firewitness_raw/" and is added to INDEX.md.

Raw files are never modified after download (C3). Their sha256 is recorded at download time; any later
read can verify it with `verify()`.
"""
from __future__ import annotations

import fcntl
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from firewitness.core.hashing import sha256_file

RAW_ROOT = Path(os.environ.get("FIREWITNESS_RAW", "/home/user/wildfire 3 (1)/firewitness_raw"))
INDEX = RAW_ROOT / "INDEX.md"
TRACK = "caught"


def raw_path(rel: str) -> Path:
    return RAW_ROOT / rel


def _index_add(rel: str, url: str, sha: str, nbytes: int, status: str = "kept") -> None:
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    line = f"| {rel} | {url} | {datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ} | {sha} | {nbytes} | {TRACK} | {status} |\n"
    with open(INDEX, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(line)
        fcntl.flock(f, fcntl.LOCK_UN)


def index_note(rel: str, status: str) -> None:
    """Record a later status change (e.g. 'deleted after extraction') as a new index line."""
    _index_add(rel, "-", "-", 0, status)


def fetch(url: str, rel: str, headers: dict | None = None, retries: int = 4, timeout: int = 600,
          session=None) -> Path:
    """Download url to RAW_ROOT/rel unless already there. Returns the local path."""
    import requests

    dst = raw_path(rel)
    if dst.exists() and dst.stat().st_size > 0:
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    s = session or requests
    last = None
    for i in range(retries):
        try:
            with s.get(url, headers=headers or {}, stream=True, timeout=timeout) as r:
                if r.status_code == 404:
                    raise FileNotFoundError(f"404 {url}")
                r.raise_for_status()
                r.raw.decode_content = True
                with open(tmp, "wb") as f:
                    shutil.copyfileobj(r.raw, f, length=1 << 20)
            os.replace(tmp, dst)
            _index_add(rel, url, sha256_file(dst), dst.stat().st_size)
            return dst
        except FileNotFoundError:
            raise
        except Exception as e:  # network errors: back off and retry
            last = e
            time.sleep(2 ** i * 3)
    raise RuntimeError(f"download failed after {retries} tries: {url}: {type(last).__name__}")


def disk_budget_ok(path: str | Path = "/home/user", frac: float = 0.5) -> bool:
    """True while this run's raw folder uses less than `frac` of the free space measured at start."""
    st = shutil.disk_usage(path)
    used_raw = sum(p.stat().st_size for p in RAW_ROOT.rglob("*") if p.is_file()) if RAW_ROOT.exists() else 0
    return used_raw < frac * (st.free + used_raw)

"""Download Landscape Data Commons plot tables (BLM AIM and partner projects) to the raw folder.

Public API, no key. geoIndicators: one row per plot visit (cover by group, heights, coordinates).
geoSpecies is queried per plot visit by plots.fetch_tree_cover (the whole tree table is ~7.7 M rows).
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import requests

from .rawindex import RAW_ROOT, register

API = "https://api.landscapedatacommons.org/api/v1/"


def _pages(table: str, params: dict, page: int = 5000):
    off = 0
    while True:
        for attempt in range(5):
            try:
                r = requests.get(API + table, params={**params, "limit": page, "offset": off}, timeout=180)
                r.raise_for_status()
                rows = r.json()
                break
            except Exception as e:  # network hiccup: back off and retry
                print("retry", table, off, type(e).__name__, file=sys.stderr)
                time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError(f"giving up on {table} offset {off}")
        if not rows:
            return
        yield rows
        off += page


def fetch(table: str, outname: str, params: dict | None = None) -> Path:
    out = RAW_ROOT / "ldc" / outname
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out, "w") as fh:
        for rows in _pages(table, params or {}):
            for r in rows:
                fh.write(json.dumps(r, separators=(",", ":")) + "\n")
            n += len(rows)
            print(table, n, flush=True)
    url = API + table + ("?" + "&".join(f"{k}={v}" for k, v in (params or {}).items()) if params else "")
    register(out, url, f"{n} rows, JSON lines")
    return out


if __name__ == "__main__":
    fetch("geoIndicators", "geoIndicators.jsonl")
    # tree cover is fetched per plot later (plots.fetch_tree_cover): the whole tree table is ~7.7 M rows

"""Open the v0.3 sealed data ONCE (protocol v0.3 section 6): H2 sealed years 2003, 2008, 2014, 2018, 2023, and the gazetteer
sealed incidents (hash(v03|number|year) mod 10 in 0..2, raw coordinates present). Rules are frozen at the commit recorded here.
Refuses to run twice."""
from __future__ import annotations

import json
import subprocess

import pandas as pd

from ..core import load_region
from . import gazetteer as G, gazetteer3 as G3, paths, timeswap as W
from .gates import wilson

OUT = paths.RESULTS / "data" / "sealed_v03.json"
SEALED_YEARS = [2003, 2008, 2014, 2018, 2023]


def run(dry_dev: bool = False):
    """dry_dev=True exercises the same code on DEV data only (one dev year, a few dev incidents); nothing is written."""
    if not dry_dev and OUT.exists():
        raise SystemExit(f"{OUT} exists: the v0.3 sealed data was already opened once")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=paths.REPO, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=paths.REPO, capture_output=True, text=True).stdout.strip()
    cfg = load_region(paths.REPO / "firewitness" / "records", "us")
    res = {"frozen_rules_commit": commit, "tracked_changes_at_open": status}
    # H2
    allr = W.all_frames(cfg)
    yr, pl, cache = W.run_groups(allr, [2005] if dry_dev else SEALED_YEARS)
    if dry_dev:
        P = G3.pool()
        d = G3.match_all(G.Gazetteer(cfg), P[P.split == "dev"].head(40).reset_index(drop=True))
        return {"dry_dev": True, "swap_year_groups": int(len(yr)), "gaz": G3.coverage(d, json.loads(G3.RADII_JSON.read_text()))["matched"]}
    yr.to_json(paths.RESULTS / "data" / "sealed_v03_swap_by_year.json", orient="records", indent=1)
    pl.to_json(paths.RESULTS / "data" / "sealed_v03_swap_pooled.json", orient="records", indent=1)
    res["swap_year_groups"] = int(len(yr))
    res["swap_year_outcomes"] = yr.outcome.value_counts().to_dict()
    res["swap_pooled_groups"] = int(len(pl))
    res["swap_pooled_outcomes"] = pl.outcome.value_counts().to_dict()
    # gazetteer
    radii = json.loads(G3.RADII_JSON.read_text())
    P = G3.pool()
    sealed = P[P.split == "sealed"].reset_index(drop=True)
    Gz = G.Gazetteer(cfg)
    d = G3.match_all(Gz, sealed)
    d.to_csv(paths.RESULTS / "data" / "sealed_v03_gazetteer.csv", index=False)
    res["gazetteer"] = {"incidents": int(len(d)), "classes": d.match_class.value_counts().to_dict(), "coverage": G3.coverage(d, radii)}
    OUT.write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=float)[:3000])

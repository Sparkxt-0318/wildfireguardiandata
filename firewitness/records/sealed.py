"""Open the sealed test split ONCE, at the end of the improvement loop (protocol section 2 and 7).

Refuses to run twice: it writes results/data/sealed_test_records.json and aborts if that file exists.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from ..core import load_region
from . import eval_published as E, geo, link_tasks as LT, locate, paths

OUT = paths.RESULTS / "data" / "sealed_test_records.json"


def run():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists: the sealed test split was already opened once")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=paths.REPO, capture_output=True, text=True).stdout.strip()
    res = {"frozen_rules_commit": commit, "links": {}}
    for name in ("fod_mtbs", "fod_ics", "ics_fired"):
        r, m, _ = LT.run_task(name, split="test", verbose=False)
        res["links"][name] = r
    cfg = load_region(paths.REPO / "firewitness" / "records", "us")
    d = pd.read_parquet(paths.CANON / "ics_raw_all.parquet").reset_index(drop=True)
    ev = locate.Evidence(geo.Admin(cfg), geo.Detections(), geo.Scars())
    P = locate.Params()
    cand, (wit, pri), _ = locate.repair_locations(d, ev, cfg, P, fit_on=(d["src"] == "ics209_2014").to_numpy())
    dec = locate.decide(cand, len(d), P)
    # published cleaning scored on the test years only
    pub = E.load_published()
    res["location_vs_published_test_years"] = E.score(d, dec, split_years_excluded=set(map(str, range(1999, 2014))) - E.TEST)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=float)[:3000])

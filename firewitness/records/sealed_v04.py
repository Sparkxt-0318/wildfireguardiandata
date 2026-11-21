"""Open the v0.4 sealed data ONCE (protocol v0.4 section 4): pooling over the sealed years 2006, 2011, 2015, 2020, 2024 (ICS-209
tables and FPA FOD source systems), and the OK Forestry records of 100 to under 300 acres (never scored) for the AM/PM rules.
Rules are frozen at the commit recorded here. Refuses to run twice."""
from __future__ import annotations

import json
import subprocess

import numpy as np
import pandas as pd

from ..core import load_region
from . import ampm as A, paths, timeoffset as T, timeoffset_run as R, timepool as P
from .gates import wilson

OUT = paths.RESULTS / "data" / "sealed_v04.json"
SEALED_YEARS = [2006, 2011, 2015, 2020, 2024]


def pooling(years, cfg):
    allr = pd.concat([R.ics_frame(cfg), R.fod_frame(300.0)], ignore_index=True)
    allr = allr[(allr.year >= 2001) & (allr.acres >= 300) & allr.state.notna() & allr.lat.notna() & allr.year.isin(years)]
    fd = T.FirstDetection(sorted(set(int(y) for y in years)))
    cache = {}
    for (s, t, y), g in allr.groupby(["system", "table", "year"]):
        if len(g) < 5:
            continue
        d, ul, uu = R.residual_inputs(fd, g)
        cache[(s, t, int(y))] = (d, ul, uu, g.inc.to_numpy(), g.rid.to_numpy())
    return P.run_pooling(cache, None, homogeneity=True)


def ampm_sealed(dry_dev=False):
    f = A.ok_frame()
    if dry_dev:      # dev only: the open-finding groups, to exercise the code
        g = f[(f.acres >= 300) & f.year.isin([2016, 2020, 2022])].reset_index(drop=True)
    else:
        g = f[(f.acres >= 100) & (f.acres < 300) & (f.year >= 2001)].reset_index(drop=True)
    yrs = sorted(int(y) for y in g.year.unique())
    fd = T.FirstDetection(yrs)
    L = A.lags(fd, g)
    res = {"records": int(len(g)), "hour_share_13_23": float((g.hour >= 13).mean()),
           "hour_counts": {int(k): int(v) for k, v in g.hour.astype(int).value_counts().sort_index().items()},
           "pooled": A.evaluate(L, g.inc.to_numpy())}
    for y in (2016, 2020, 2022):
        m = (g.year == y).to_numpy()
        res[str(y)] = A.evaluate(L, g.inc.to_numpy(), mask=m)
    return res


def run(dry_dev: bool = False):
    """dry_dev=True exercises the same code on DEV data only (one dev year, the open-finding OK groups); nothing is written."""
    if not dry_dev and OUT.exists():
        raise SystemExit(f"{OUT} exists: the v0.4 sealed data was already opened once")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=paths.REPO, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=paths.REPO, capture_output=True, text=True).stdout.strip()
    cfg = load_region(paths.REPO / "firewitness" / "records", "us")
    res = {"frozen_rules_commit": commit, "tracked_changes_at_open": status}
    yr, pl = pooling([2005] if dry_dev else SEALED_YEARS, cfg)
    if dry_dev:
        return {"dry_dev": True, "pooled_tables": int(len(pl)), "ampm": ampm_sealed(dry_dev=True)["pooled"]["n"]}
    yr.to_json(paths.RESULTS / "data" / "sealed_v04_by_year.json", orient="records", indent=1)
    pl.to_json(paths.RESULTS / "data" / "sealed_v04_pooled.json", orient="records", indent=1)
    dev = pd.read_json(paths.OUT / "timepool_dev" / "pooled_hom.json")
    m = pl.merge(dev[["system", "table", "outcome", "convention_called"]], on=["system", "table"], suffixes=("", "_dev"), how="inner")
    m = m[m.outcome != "insufficient fires"]
    decided_dev = m[m.convention_called_dev.notna()]
    same = int((decided_dev.convention_called == decided_dev.convention_called_dev).sum())
    opp = int((decided_dev.convention_called.notna() & (decided_dev.convention_called != decided_dev.convention_called_dev)).sum())
    res["pooling"] = {"sealed_pooled_tables": int(len(pl)), "outcomes": pl.outcome.value_counts().to_dict(),
                      "year_group_finals": yr.final.value_counts().to_dict(), "year_groups_decided_by_pool": int(yr.decided_by_pool.sum()),
                      "tables_with_dev_call_and_sealed_call": int(len(decided_dev)), "same_call_as_dev": same, "same_ci": wilson(same, max(len(decided_dev), 1)),
                      "opposite_to_dev": opp}
    res["ampm"] = ampm_sealed()
    OUT.write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=float)[:3500])

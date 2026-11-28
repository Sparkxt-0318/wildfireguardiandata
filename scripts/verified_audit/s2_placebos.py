"""Verified-tier audit, step 2: rebuild the S3 placebo windows with the frozen make_placebos.

Record table = the released S3 label files (FPA FOD is not reachable from the audit machine). Rubric section 2.
Usage: s2_placebos.py [n_procs] [limit]
"""
from __future__ import annotations

import multiprocessing as mp
import sys
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd

from firewitness.caught import perimeters, records
from firewitness.caught.fetch import RAW_ROOT
from firewitness.caught.records import ACRE_M2
from firewitness.caught.run import prepare_windows

REL = "release/caught-v0.1/caught_labels_v0.1_{y}.parquet"
COLS = ["rid", "FOD_ID", "STATE", "FIRE_YEAR", "FIRE_SIZE", "FIRE_SIZE_CLASS", "LATITUDE", "LONGITUDE", "r_loc_m", "r_m",
        "t0", "t1", "t1_source", "split", "searched", "tier", "std_label"]


def released_records() -> pd.DataFrame:
    d = pd.concat([pd.read_parquet(REL.format(y=y), columns=COLS) for y in (2018, 2019, 2020)], ignore_index=True)
    d["t0"] = pd.to_datetime(d.t0).dt.date
    d["t1"] = pd.to_datetime(d.t1).dt.date
    d["disc_date"] = [t + timedelta(days=1) for t in d.t0]
    d["area_m2"] = d.FIRE_SIZE.astype(float) * ACRE_M2
    d["r_fire_m"] = np.sqrt(d.area_m2 / np.pi)
    return d.rename(columns={"searched": "searched_released", "tier": "tier_released"})


_G = {}


def exclusion_indexes(cfg):
    """perim_idx and mtbs_idx exactly as firewitness.caught.run.Sources.__init__ builds them (lines copied verbatim),
    without loading the heat, smoke and burned-area sources that placebo matching does not use."""
    from firewitness.caught import standard
    mt = standard.load_mtbs(cfg).copy()
    mt["d0"] = pd.to_datetime(mt.ig_date) - pd.Timedelta(days=1)
    mt["d1"] = pd.to_datetime(mt.ig_date) + pd.Timedelta(days=1)
    mtbs_idx = standard.PolygonIndex(mt.reset_index(drop=True), "d0", "d1", "Event_ID")
    perims = perimeters.load_all(2018, 2020)
    pr = perims[perims.source != "facts_bb"].copy()
    yr0 = pd.to_datetime(pr["year"].astype("Int64").astype(str) + "-01-01", errors="coerce")
    pr["e0"] = pr.d0.fillna(np.maximum(pr.d1 - pd.Timedelta(days=120), yr0)).fillna(yr0)
    pr["e1"] = pr.d1.fillna(pr.d0 + pd.Timedelta(days=60)).fillna(yr0 + pd.Timedelta(days=365))
    pr = pr.dropna(subset=["e0", "e1"]).reset_index(drop=True)
    perim_idx = standard.PolygonIndex(pr, "e0", "e1", "pid")
    return perim_idx, mtbs_idx


def _init():
    cfg = records.region()
    rec = released_records()
    perim_idx, mtbs_idx = exclusion_indexes(cfg)
    _G.update(cfg=cfg, perim_idx=perim_idx, mtbs_idx=mtbs_idx,
              all_fod=rec[["LATITUDE", "LONGITUDE", "disc_date"]].copy(), states=perimeters.states())


def _chunk(rec_chunk):
    from firewitness.caught.placebo import make_placebos
    g = _G
    return make_placebos(rec_chunk, g["all_fod"], g["perim_idx"], g["mtbs_idx"], g["states"], g["cfg"])


def main():
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    cfg = records.region()
    rec = released_records()
    rec = prepare_windows(rec, cfg)
    print("searched (rebuilt prepare_windows) =", int(rec.searched.sum()), "released =", int(rec.searched_released.sum()),
          "mismatch =", int((rec.searched != rec.searched_released).sum()), flush=True)
    if limit:
        rec = rec.sample(n=limit, random_state=0)
    out = RAW_ROOT / "derived_caught" / ("placebo_windows_S3_audit.parquet" if not limit else f"placebo_windows_S3_audit_n{limit}.parquet")
    t = time.time()
    k = max(1, procs * 8)
    chunks = [rec.iloc[i::k] for i in range(k)]
    _init()  # built once in the parent; forked workers inherit it
    ctx = mp.get_context("fork")
    with ctx.Pool(procs) as pool:
        parts = pool.map(_chunk, chunks)
    plc = pd.concat(parts, ignore_index=True)
    plc.to_parquet(out)
    print(f"placebos {len(plc)} matched {int(plc.matched.sum())} in {time.time() - t:.0f} s -> {out}", flush=True)


if __name__ == "__main__":
    main()

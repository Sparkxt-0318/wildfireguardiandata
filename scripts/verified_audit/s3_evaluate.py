"""Verified-tier audit, step 3: evidence and tiers for the rebuilt S3 placebos, at the frozen code and defaults.

Point and polygon matches for every searched placebo; find_scar only on searched placebos with a non-imagery HEAT
or SMOKE item or an MCD64A1 pixel (rubric section 2); tiers with firewitness.caught.evidence.tier via run.label_row.
Usage: s3_evaluate.py points|mcd|scar|labels [procs]
"""
from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time

import pandas as pd

from firewitness.caught import records
from firewitness.caught.fetch import RAW_ROOT
from firewitness.caught.run import (build_items, label_row, point_matches, polygon_matches, prepare_windows,
                                    run_dir, scar_stage)

sys.path.insert(0, "scripts/verified_audit")
from s2_placebos import released_records  # noqa: E402

NAME = "audit_S3/placebo"
GATE = {"MODIS", "VIIRS_SNPP", "VIIRS_NOAA20", "GOES", "AVHRR", "HMS_ANALYST", "MCD64A1"}
HEAT = {"MODIS", "VIIRS_SNPP", "VIIRS_NOAA20", "GOES", "AVHRR", "HMS_ANALYST", "DNB"}
_G = {}


def windows():
    cfg = records.region()
    plc = pd.read_parquet(RAW_ROOT / "derived_caught" / "placebo_windows_S3_audit.parquet")
    for c in ("t0", "t1", "disc_date"):
        plc[c] = pd.to_datetime(plc[c]).dt.date
    plc = prepare_windows(plc, cfg)
    return plc


def _pts_chunk(w):
    src, big = _G["src"], _G["big"]
    return {r.rid: {"pts": point_matches(src, r), "polys": polygon_matches(src, r, big, True)} for r in w.itertuples()}


MCD_CAND = RAW_ROOT / "derived_caught" / "mcd64a1_audit_candidates.parquet"


def load_sources(with_mcd: bool = False):
    """Sources at the frozen code; MCD64A1 is empty in the first pass and the per-candidate table after (A1)."""
    from firewitness.caught import standard
    from firewitness.caught.pipeline import fod_big_index, sources
    empty = pd.DataFrame({"lat": pd.Series(dtype=float), "lon": pd.Series(dtype=float), "date": pd.Series(dtype=object),
                          "unc_days": pd.Series(dtype=int), "tile": pd.Series(dtype=str),
                          "half_m": pd.Series(dtype=float), "witness": pd.Series(dtype=str)})
    mcd = pd.read_parquet(MCD_CAND) if with_mcd else empty
    standard.load_mcd64a1 = lambda years, cfg: mcd
    cfg = records.region()
    src = sources(cfg)
    rec = released_records()
    _G.update(src=src, big=fod_big_index(rec[["LATITUDE", "LONGITUDE", "FIRE_SIZE_CLASS", "disc_date", "t1"]]))


def stage_points(procs):
    w = windows()
    w = w[w.searched]
    p = run_dir(NAME) / "points.json"
    if p.exists():
        print("points exist", flush=True)
        return
    load_sources()
    t = time.time()
    k = procs * 16
    chunks = [w.iloc[i::k] for i in range(k)]
    with mp.get_context("fork").Pool(procs) as pool:
        parts = pool.map(_pts_chunk, chunks)
    pts = {}
    for d in parts:
        pts.update(d)
    p.write_text(json.dumps(pts, default=str))
    print(f"points for {len(pts)} searched placebos in {time.time() - t:.0f} s", flush=True)


def gate(pts):
    cand, heat = set(), set()
    for rid, v in pts.items():
        ws = {q["witness"] for q in v["pts"]} | {q["witness"] for q in v["polys"]}
        if ws & GATE or "HMS_SMOKE" in ws:
            cand.add(rid)
        if ws & HEAT:
            heat.add(rid)
    return cand, heat


def stage_mcd(procs):
    """A1: MCD64A1 pixels near every candidate, then the candidates' point matches recomputed with them."""
    sys.path.insert(0, "scripts/verified_audit")
    from mcd_windows import pixels_near
    w = windows()
    pts = json.loads((run_dir(NAME) / "points.json").read_text())
    cand, _ = gate(pts)
    wc = w[w.searched & w.rid.isin(cand)]
    if not MCD_CAND.exists():
        t = time.time()
        d, errs = pixels_near(wc)
        print(f"mcd pixels {len(d)} for {len(wc)} candidates in {time.time() - t:.0f} s; errors {len(errs)}: {errs[:5]}",
              flush=True)
        if errs:
            raise SystemExit("MCD64A1 read errors: rerun")
        d.to_parquet(MCD_CAND)
    load_sources(with_mcd=True)
    k = procs * 8
    with mp.get_context("fork").Pool(procs) as pool:
        parts = pool.map(_pts_chunk, [wc.iloc[i::k] for i in range(k)])
    pc_ = {}
    for p in parts:
        pc_.update(p)
    (run_dir(NAME) / "points_candidates.json").write_text(json.dumps(pc_, default=str))
    n = sum(any(q["witness"] == "MCD64A1" for q in v["pts"]) for v in pc_.values())
    print(f"candidates with an MCD64A1 match: {n}", flush=True)


def merged_points():
    pts = json.loads((run_dir(NAME) / "points.json").read_text())
    pc_ = run_dir(NAME) / "points_candidates.json"
    if pc_.exists():
        pts.update(json.loads(pc_.read_text()))
    return pts


def stage_scar(procs):
    import os
    import concurrent.futures.process as _cfp
    _cfp._check_system_limits = lambda: None   # the audit sandbox forbids sysconf(SC_SEM_NSEMS_MAX); harness only
    os.environ["FIREWITNESS_PROCS"] = str(procs)
    w = windows()
    pts = merged_points()
    cand, heat = gate(pts)
    wc = w[w.searched & w.rid.isin(cand)]
    print(f"searched {int(w.searched.sum())}, candidates {len(wc)}, with heat {len(heat)}", flush=True)
    scar_stage(NAME, wc, threads=procs * 6, params=None, procs=procs, heat_rids=heat, log_every=50)


def stage_labels():
    w = windows()
    w = w[w.searched]
    pts = merged_points()
    cand, _ = gate(pts)
    scars = {}
    ck = run_dir(NAME) / "scar.jsonl"
    with open(ck) as fh:
        for line in fh:
            j = json.loads(line)
            if j.get("status") != "error":
                scars[j["rid"]] = j
            else:
                scars.setdefault(j["rid"], j)
    load_sources(with_mcd=True)
    src = _G["src"]
    rows = []
    for r in w.itertuples():
        sc = scars.get(r.rid)
        items = build_items(r, pts[r.rid]["pts"], pts[r.rid]["polys"], sc, src)
        row = label_row(r, items, sc, True)
        row.update({"of_rid": r.of_rid, "LATITUDE": r.LATITUDE, "LONGITUDE": r.LONGITUDE, "r_m": r.r_m,
                    "t0": str(r.t0), "t1": str(r.t1), "FIRE_SIZE_CLASS": r.FIRE_SIZE_CLASS, "FIRE_YEAR": r.FIRE_YEAR,
                    "STATE": r.STATE, "landcover": r.landcover, "candidate": r.rid in cand,
                    "scar_run": r.rid in scars, "scar_error": (sc or {}).get("status") == "error"})
        rows.append(row)
    lab = pd.DataFrame(rows)
    out = RAW_ROOT / "derived_caught" / "audit_S3_placebo_labels.parquet"
    lab.to_parquet(out)
    v = lab[lab.tier == "verified"]
    print("searched", len(lab), "verified", len(v), "probable", int((lab.tier == "probable").sum()), flush=True)
    print("verified by year", v.groupby("FIRE_YEAR").size().to_dict(), "searched by year",
          lab.groupby("FIRE_YEAR").size().to_dict(), flush=True)
    print("scar errors among candidates", int(lab.scar_error.sum()), flush=True)


if __name__ == "__main__":
    st = sys.argv[1]
    procs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    {"points": lambda: stage_points(procs), "mcd": lambda: stage_mcd(procs), "scar": lambda: stage_scar(procs), "labels": stage_labels}[st]()

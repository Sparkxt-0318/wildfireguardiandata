"""Raw extraction for the growth rate (protocol/GROWTH_PROTOCOL.md §3).

Same reader, anchor and boxes as the frozen v0.1 extraction (firewitness/live/extract.py), with the day-0 window
lengthened to [T0 - 12 h, T0 + 6 h] so that six hours after any start time t0 <= T0 are covered, and the same window
on the eight previous days. The band-1 visible channel is not read (not used here). On day 0 the fire product is read
with its Power layer. Output: one npz per fire and satellite in the frozen series format (so the frozen trace-back
runs on it unchanged) plus a meta JSON per fire.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np

from .. import goes
from ..extract import HALF, BOX, enc_bt, fdc_first, sats_for, site_pixels
from .common import CFG

E = CFG["extract"]
NDAYS = E["ndays"]
PRE_H, POST_H = E["pre_h"], E["post_h"]
NSLOT = (PRE_H + POST_H) * 12
RP = CFG["series"]["fdc_region_px"] // 2
FIRE_CODES = CFG["series"]["fire_codes"]


def series_dir() -> Path:
    return goes.RAW_ROOT / "live" / "series"


def fdc_power_at(bucket, prefix, r, c, scan_t, half):
    """FDCC Power (MW) summed over fire-coded pixels of the (2 half + 1)^2 window at the frame with scan start scan_t."""
    fr = goes.frames(bucket, prefix, None, goes.utc(scan_t - 60), goes.utc(scan_t + 60))
    fr = [f for f in fr if abs(f["t"] - scan_t) < 30]
    if not fr:
        return None, 0
    res = goes.read_job({"url": goes.url_of(fr[0]), "kind": "fdcp", "boxes": [(r - half, c - half, 2 * half + 1, 2 * half + 1)]})
    if not res["ok"]:
        return None, 0
    m, p = res["boxes"][0]
    sel = np.isin(m.astype(int), FIRE_CODES)
    ok = sel & np.isfinite(p)
    return (float(p[ok].sum()) if ok.any() else None), int(sel.sum())


def extract_fire(fire: dict, cfg: dict, pool, out_dir: Path | None = None, force=False) -> dict:
    out_dir = out_dir or series_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    fid = fire["fire_id"]
    meta_f = out_dir / f"{fid}.json"
    if meta_f.is_file() and not force:
        return json.loads(meta_f.read_text())
    lat, lon = float(fire["polar_first_lat"]), float(fire["polar_first_lon"])
    disc = float(fire["discovery_t"])
    sats = sats_for(cfg, disc)
    meta = {"fire_id": fid, "lat": lat, "lon": lon, "discovery_t": disc, "polar_first_t": float(fire["polar_first_t"]),
            "sats": {}, "t_start": time.time(), "window_h": [-PRE_H, POST_H]}
    p = cfg["products"]
    a0, a1 = E["fdc_search_h"]
    for role in ("east", "west"):
        s = sats.get(role)
        if not s:
            continue
        px = site_pixels(cfg, s, lat, lon)
        if px is None:
            continue
        ff = fdc_first(cfg, s, px, disc + a0 * 3600, disc + a1 * 3600, pool, cfg["fdc_fire_codes"])
        sm = {"role": role, "bucket": s["bucket"], "r": px["r"], "c": px["c"], "r1": px["r1"], "c1": px["c1"],
              "fdc_first": ff["first"], "fdc_first_low": ff["first_low"], "fdc_search_frames": ff["n_frames"],
              "fdc_search_missing": ff["n_missing"]}
        if ff["first"]:
            pw, npx = fdc_power_at(s["bucket"], p["FDC"]["prefix"], px["r"], px["c"], float(ff["first"][0]), RP)
            sm["fdc_first_power_mw"], sm["fdc_first_npix"] = pw, npx
        meta["sats"][s["name"]] = sm
    cands = [meta["polar_first_t"]] + [v["fdc_first"][0] for v in meta["sats"].values() if v["fdc_first"]]
    T0 = min(cands)
    meta["T0"] = T0
    meta["T0_source"] = "polar" if T0 == meta["polar_first_t"] else "fdc"
    ws = T0 - PRE_H * 3600
    for name, sm in meta["sats"].items():
        r0, c0 = sm["r"] - HALF, sm["c"] - HALF
        jobs, where = [], []
        tscan = np.full((NDAYS, NSLOT), np.nan)
        tavail = np.full((NDAYS, NSLOT), np.nan)
        for d in range(NDAYS):
            a = ws - d * 86400
            b = a + NSLOT * 300
            for prod, band, kind in (("C07", 7, "bt"), ("C14", 14, "bt"), ("ACM", None, "acm"), ("FDC", None, "fdc")):
                fr = goes.frames(sm["bucket"], p[prod]["prefix"], band, goes.utc(a - 60), goes.utc(b))
                for f in fr:
                    k = int(math.floor((f["t"] - a + 60) / 300))
                    if not 0 <= k < NSLOT:
                        continue
                    if prod == "C07":
                        tscan[d, k] = f["t"]
                        tavail[d, k] = f["avail"]
                    knd = "fdcp" if (prod == "FDC" and d == 0) else kind
                    jobs.append({"url": goes.url_of(f), "kind": knd, "boxes": [(r0, c0, BOX, BOX)]})
                    where.append((prod, d, k))
        res = pool.map(goes.read_job, jobs, chunksize=4)
        arr = {"C07": np.zeros((NDAYS, NSLOT, BOX, BOX), np.uint16), "C14": np.zeros((NDAYS, NSLOT, BOX, BOX), np.uint16),
               "ACM": np.full((NDAYS, NSLOT, BOX, BOX), 255, np.uint8),
               "FDC": np.full((NDAYS, NSLOT, BOX, BOX), -1, np.int16)}
        pow0 = np.full((NSLOT, 2 * RP + 1, 2 * RP + 1), np.nan, np.float32)
        nfail, nbytes = 0, 0
        for (prod, d, k), r in zip(where, res):
            if not r["ok"]:
                nfail += 1
                continue
            nbytes += r["nbytes"]
            v = r["boxes"][0]
            if prod in ("C07", "C14"):
                arr[prod][d, k] = enc_bt(v)
            elif prod == "FDC" and d == 0:
                mk = np.where(np.isfinite(v[0]), v[0], -1).astype(np.int16)
                arr["FDC"][d, k] = mk
                pow0[k] = v[1][HALF - RP:HALF + RP + 1, HALF - RP:HALF + RP + 1]
            else:
                arr[prod][d, k] = v
        g = goes.grid_info(sm["bucket"], p["C07"]["prefix"], 7, name)
        lon_g, lat_g = goes.rc_to_lonlat(*np.meshgrid(np.arange(r0, r0 + BOX), np.arange(c0, c0 + BOX), indexing="ij"), g)
        f_out = out_dir / f"{fid}_{name}.npz"
        goes.atomic_savez(f_out, tscan=tscan, tavail=tavail, lat=lat_g.astype(np.float32), lon=lon_g.astype(np.float32),
                          C01=np.zeros((1, 1, 1, 1), np.uint16), FDC_POW0=pow0, **arr)
        sm.update({"n_jobs": len(jobs), "n_fail": nfail, "bytes_read": nbytes, "file": f_out.name,
                   "box_r0": r0, "box_c0": c0})
    meta["t_end"] = time.time()
    tmp = meta_f.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta, indent=1))
    tmp.replace(meta_f)
    return meta


def band7_planck(bucket: str, prefix: str, sat: str, t) -> list[float]:
    """Band-7 Planck constants (fk1, fk2, bc1, bc2) read from one L1b file of the satellite."""
    import h5py
    fr = goes.frames(bucket, prefix, 7, goes.utc(t), goes.utc(t + 3600))
    h = h5py.File(goes.RangeFile(goes.url_of(fr[0])), "r")
    return [float(h[k][()]) for k in ("planck_fk1", "planck_fk2", "planck_bc1", "planck_bc2")]

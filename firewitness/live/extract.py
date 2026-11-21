"""Per-fire series extraction (protocol §2).

For each fire and each satellite that sees it: find the anchor T0 (first standard detection), then read the
40x40 box around the site for day 0 and the eight previous days, same clock window. Output one compressed npz per
fire and satellite under firewitness_raw/live/series/ (re-derivable; not in git) and append to the raw INDEX.md.
"""
from __future__ import annotations

import csv
import json
import math
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from . import goes
from .goes import RAW_ROOT

SERIES_DIR = RAW_ROOT / "live" / "series"
INDEX = RAW_ROOT / "INDEX.md"
BOX = 40
HALF = BOX // 2
NDAYS = 9          # day 0 and days -1 .. -8
PRE_H, POST_H = 12, 2
NSLOT = (PRE_H + POST_H) * 12
ENC_OFF, ENC_SC = 150.0, 100.0   # BT stored as uint16 (K - 150) * 100 ; 0 = missing


def enc_bt(a):
    v = np.where(np.isfinite(a), np.clip((a - ENC_OFF) * ENC_SC, 1, 65535), 0)
    return v.astype(np.uint16)


def dec_bt(v):
    a = v.astype(np.float32) / ENC_SC + ENC_OFF
    a[v == 0] = np.nan
    return a


def enc_refl(a):
    v = np.where(np.isfinite(a), np.clip(a * 10000 + 1, 1, 65535), 0)
    return v.astype(np.uint16)


def dec_refl(v):
    a = (v.astype(np.float32) - 1) / 10000
    a[v == 0] = np.nan
    return a


def solar_zenith(lat, lon, t):
    """Approximate solar zenith angle (deg) at epoch seconds t."""
    d = datetime.fromtimestamp(t, tz=timezone.utc)
    n = d.timetuple().tm_yday
    g = 2 * math.pi / 365.0 * (n - 1 + (d.hour - 12) / 24)
    decl = 0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) \
        + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g)
                    - 0.040849 * math.sin(2 * g))
    tst = d.hour * 60 + d.minute + d.second / 60 + eqt + 4 * lon
    ha = math.radians(tst / 4 - 180)
    la = math.radians(lat)
    c = math.sin(la) * math.sin(decl) + math.cos(la) * math.cos(decl) * math.cos(ha)
    return math.degrees(math.acos(max(-1, min(1, c))))


def sats_for(cfg, t):
    """(east, west) satellite dicts operating at epoch t."""
    out = {}
    for s in cfg["satellites"]:
        a = goes.utc(s["from"]).timestamp()
        b = goes.utc(s["to"]).timestamp() if s["to"] else 1e12
        if a <= t < b:
            out[s["role"]] = s
    return out


def site_pixels(cfg, sat, lat, lon):
    p = cfg["products"]
    g2 = goes.grid_info(sat["bucket"], p["C07"]["prefix"], 7, sat["name"])
    g1 = goes.grid_info(sat["bucket"], p["C01"]["prefix"], 1, sat["name"])
    r, c = goes.lonlat_to_rc(lon, lat, g2)
    r1, c1 = goes.lonlat_to_rc(lon, lat, g1)
    if not (np.isfinite(r) and np.isfinite(c)):
        return None
    r, c, r1, c1 = int(round(float(r))), int(round(float(c))), int(round(float(r1))), int(round(float(c1)))
    if not (HALF <= r < g2["ny"] - HALF and HALF <= c < g2["nx"] - HALF):
        return None
    return {"r": r, "c": c, "r1": r1, "c1": c1, "g2": g2, "g1": g1}


def fdc_first(cfg, sat, px, t0, t1, pool, codes):
    """First FDCC frame in [t0, t1) with a fire code in the 5x5 window at the site. Returns (scan t, avail t, code)."""
    fr = goes.frames(sat["bucket"], cfg["products"]["FDC"]["prefix"], None, goes.utc(t0), goes.utc(t1))
    jobs = [{"url": goes.url_of(f), "kind": "fdc", "boxes": [(px["r"] - 2, px["c"] - 2, 5, 5)]} for f in fr]
    res = pool.map(goes.read_job, jobs, chunksize=1)
    first, first_low, nmiss = None, None, 0
    for f, r in zip(fr, res):
        if not r["ok"]:
            nmiss += 1
            continue
        m = r["boxes"][0]
        if first is None and np.isin(m, codes).any():
            first = (f["t"], f["avail"], int(m[np.isin(m, codes)].max()))
        if first_low is None and np.isin(m, cfg["fdc_fire_codes_incl_low"]).any():
            first_low = (f["t"], f["avail"])
        if first is not None and first_low is not None:
            break
    return {"first": first, "first_low": first_low, "n_frames": len(fr), "n_missing": nmiss}


def extract_fire(fire: dict, cfg: dict, pool, out_dir: Path = SERIES_DIR, force=False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    fid = fire["fire_id"]
    meta_f = out_dir / f"{fid}.json"
    if meta_f.is_file() and not force:
        return json.loads(meta_f.read_text())
    lat, lon = float(fire["polar_first_lat"]), float(fire["polar_first_lon"])
    disc = float(fire["discovery_t"])
    sats = sats_for(cfg, disc)
    meta = {"fire_id": fid, "lat": lat, "lon": lon, "discovery_t": disc, "polar_first_t": float(fire["polar_first_t"]),
            "sats": {}, "t_start": time.time()}
    # stage 1: anchor search
    for role in ("east", "west"):
        s = sats.get(role)
        if not s:
            continue
        px = site_pixels(cfg, s, lat, lon)
        if px is None:
            continue
        ff = fdc_first(cfg, s, px, disc - 12 * 3600, disc + 48 * 3600, pool, cfg["fdc_fire_codes"])
        meta["sats"][s["name"]] = {"role": role, "bucket": s["bucket"], "r": px["r"], "c": px["c"], "r1": px["r1"],
                                   "c1": px["c1"], "fdc_first": ff["first"], "fdc_first_low": ff["first_low"],
                                   "fdc_search_frames": ff["n_frames"], "fdc_search_missing": ff["n_missing"]}
    cands = [meta["polar_first_t"]] + [v["fdc_first"][0] for v in meta["sats"].values() if v["fdc_first"]]
    T0 = min(cands)
    meta["T0"] = T0
    meta["T0_source"] = "polar" if T0 == meta["polar_first_t"] else "fdc"
    ws = T0 - PRE_H * 3600
    p = cfg["products"]
    for name, sm in meta["sats"].items():
        s = {"name": name, "bucket": sm["bucket"]}
        r0, c0 = sm["r"] - HALF, sm["c"] - HALF
        r10, c10 = sm["r1"] - HALF, sm["c1"] - HALF
        jobs, where = [], []
        tscan = np.full((NDAYS, NSLOT), np.nan)
        tavail = np.full((NDAYS, NSLOT), np.nan)
        for d in range(NDAYS):
            a = ws - d * 86400
            b = a + NSLOT * 300
            for prod, band, kind in (("C07", 7, "bt"), ("C14", 14, "bt"), ("ACM", None, "acm"), ("FDC", None, "fdc"),
                                     ("C01", 1, "refl")):
                fr = goes.frames(s["bucket"], p[prod]["prefix"], band, goes.utc(a - 60), goes.utc(b))
                for f in fr:
                    k = int(math.floor((f["t"] - a + 60) / 300))
                    if not 0 <= k < NSLOT:
                        continue
                    if prod == "C01" and solar_zenith(lat, lon, f["t"]) >= 85:
                        continue
                    if prod == "C07":
                        tscan[d, k] = f["t"]
                        tavail[d, k] = f["avail"]
                    box = (r10, c10, BOX, BOX) if prod == "C01" else (r0, c0, BOX, BOX)
                    jobs.append({"url": goes.url_of(f), "kind": kind, "boxes": [box]})
                    where.append((prod, d, k, f["avail"]))
        res = pool.map(goes.read_job, jobs, chunksize=4)
        arr = {"C07": np.zeros((NDAYS, NSLOT, BOX, BOX), np.uint16), "C14": np.zeros((NDAYS, NSLOT, BOX, BOX), np.uint16),
               "C01": np.zeros((NDAYS, NSLOT, BOX, BOX), np.uint16),
               "ACM": np.full((NDAYS, NSLOT, BOX, BOX), 255, np.uint8),
               "FDC": np.full((NDAYS, NSLOT, BOX, BOX), -1, np.int16)}
        avail = {k: np.full((NDAYS, NSLOT), np.nan) for k in ("C14", "ACM", "FDC", "C01")}
        nfail, nbytes = 0, 0
        for (prod, d, k, av), r in zip(where, res):
            if not r["ok"]:
                nfail += 1
                continue
            nbytes += r["nbytes"]
            v = r["boxes"][0]
            if prod in ("C07", "C14"):
                arr[prod][d, k] = enc_bt(v)
            elif prod == "C01":
                arr[prod][d, k] = enc_refl(v)
            else:
                arr[prod][d, k] = v
            if prod != "C07":
                avail[prod][d, k] = av
        lon_g, lat_g = goes.rc_to_lonlat(*np.meshgrid(np.arange(r0, r0 + BOX), np.arange(c0, c0 + BOX), indexing="ij"),
                                         goes.grid_info(s["bucket"], p["C07"]["prefix"], 7, name))
        f_out = out_dir / f"{fid}_{name}.npz"
        goes.atomic_savez(f_out, tscan=tscan, tavail=tavail, avail_C14=avail["C14"], avail_ACM=avail["ACM"],
                            avail_FDC=avail["FDC"], avail_C01=avail["C01"], lat=lat_g.astype(np.float32),
                            lon=lon_g.astype(np.float32), **arr)
        sm.update({"n_jobs": len(jobs), "n_fail": nfail, "bytes_read": nbytes, "file": f_out.name,
                   "box_r0": r0, "box_c0": c0, "box1_r0": r10, "box1_c0": c10})
        _index(f_out, f"GOES {name} ABI L1b C07/C14/C01 + L2 ACMC/FDCC, {len(jobs)} files (range reads, box {BOX}x{BOX})", nbytes)
    meta["t_end"] = time.time()
    tmp = meta_f.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta, indent=1))
    tmp.replace(meta_f)
    return meta


def _index(path: Path, source: str, nbytes: int):
    try:
        with open(INDEX, "a") as fh:
            fh.write(f"| {datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ} | live | {path.relative_to(RAW_ROOT)} | {source} | "
                     f"{nbytes} read, {path.stat().st_size} stored | derived series (raw chunks not kept) |\n")
    except Exception:
        pass


def load_fires(path) -> list[dict]:
    with open(path) as fh:
        return list(csv.DictReader(fh))


def load_series(fid: str, sat: str, d: Path = SERIES_DIR) -> dict:
    z = np.load(d / f"{fid}_{sat}.npz")
    out = {k: z[k] for k in z.files}
    out["BT7"] = dec_bt(out.pop("C07"))
    out["BT14"] = dec_bt(out.pop("C14"))
    out["REF1"] = dec_refl(out.pop("C01"))
    return out

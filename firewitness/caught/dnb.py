"""Night look: VIIRS day/night band (Black Marble VNP46A2, moon- and BRDF-corrected, 15 arcsec) where the
background is dark. A window's night is a DNB item if a clear pixel in the disc is brighter than its own
baseline (median of the clear nights 30 to 3 days before the window) by max(5 robust sd, 3 nW cm-2 sr-1).

Tiles are streamed: each daily tile is downloaded raw, the needed pixels are extracted, and the file is deleted
(the index keeps its sha256). Scope (DECISIONS D-510): the tiles and year of slice S1 (California 2020).
"""
from __future__ import annotations

import math
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from firewitness.core.keys import get_key

from .fetch import RAW_ROOT, fetch, index_note

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
NPIX = 2400
STEP = 10.0 / NPIX
K_SIGMA, MIN_EXCESS = 5.0, 3.0


def tile_of(lat, lon):
    return int(math.floor((lon + 180) / 10)), int(math.floor((90 - lat) / 10))


def pixel_of(lat, lon, h, v):
    top = 90 - 10 * v
    left = -180 + 10 * h
    return int((top - lat) / STEP), int((lon - left) / STEP)


def _session():
    import requests
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {get_key('EARTHDATA_TOKEN')}"
    return s


def granule_url(h, v, d: date, s) -> str | None:
    lon = -180 + 10 * h + 5
    lat = 90 - 10 * v - 5
    r = s.get(CMR, params={"short_name": "VNP46A2", "temporal": f"{d}T00:00:00Z,{d}T23:59:59Z",
                           "point": f"{lon},{lat}", "page_size": 5}, timeout=60)
    for e in r.json()["feed"]["entry"]:
        for link in e["links"]:
            u = link["href"]
            if (u.startswith("https") and u.endswith(".h5") and f"h{h:02d}v{v:02d}" in u
                    and f".A{d:%Y%j}." in u):  # CMR's temporal match also returns the neighbouring day
                return u
    return None


def extract(windows: pd.DataFrame, name: str, threads: int = 6) -> dict:
    """{rid: {"nights": [(date, value, clear, mqf)...] per pixel...}} -> per-window DataFrame of pixel values."""
    import h5py

    need = defaultdict(set)   # (h, v) -> days
    pix = defaultdict(list)   # (h, v) -> [(rid, row, col)]
    for w in windows.itertuples():
        h, v = tile_of(w.LATITUDE, w.LONGITUDE)
        r0, c0 = pixel_of(w.LATITUDE, w.LONGITUDE, h, v)
        rr = int(math.ceil((w.r_m + 230) / 463.0))
        rr = min(rr, 3)
        for dr in range(-rr, rr + 1):
            for dc in range(-rr, rr + 1):
                r, c = r0 + dr, c0 + dc
                if 0 <= r < NPIX and 0 <= c < NPIX:
                    pix[(h, v)].append((w.rid, r, c))
        d = w.t0 - timedelta(days=30)
        while d <= w.t1:
            need[(h, v)].add(d)
            d += timedelta(days=1)
    out = RAW_ROOT / "derived_caught" / "dnb" / name
    out.mkdir(parents=True, exist_ok=True)
    s = _session()
    rows = []

    def one(hv, d):
        h, v = hv
        f = out / f"vals_h{h:02d}v{v:02d}_{d}.npz"
        if f.exists():
            return f
        u = granule_url(h, v, d, s)
        if u is None:
            np.savez(f, missing=True)
            return f
        rel = f"dnb/{u.rsplit('/', 1)[1]}"
        p = fetch(u, rel, session=s)
        try:
            with h5py.File(p) as hf:
                g = hf["HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields"]
                rc = np.array([(r, c) for _, r, c in pix[hv]])
                ntl = g["DNB_BRDF-Corrected_NTL"][()]
                mqf = g["Mandatory_Quality_Flag"][()]
                cld = g["QF_Cloud_Mask"][()]
                np.savez(f, ntl=ntl[rc[:, 0], rc[:, 1]], mqf=mqf[rc[:, 0], rc[:, 1]], cld=cld[rc[:, 0], rc[:, 1]])
        finally:
            p.unlink(missing_ok=True)
            index_note(rel, "deleted after extraction")
        return f

    jobs = [(hv, d) for hv, ds in need.items() for d in sorted(ds)]
    with ThreadPoolExecutor(threads) as ex:
        list(ex.map(lambda j: one(*j), jobs))
    return {"pix": pix, "need": need, "dir": out}


def detect(windows: pd.DataFrame, ex: dict) -> dict:
    """{rid: [item dicts]} DNB night-light anomalies inside each window."""
    out = defaultdict(list)
    for hv, plist in ex["pix"].items():
        rids = np.array([p[0] for p in plist])
        days = sorted(ex["need"][hv])
        vals = {}
        for d in days:
            f = ex["dir"] / f"vals_h{hv[0]:02d}v{hv[1]:02d}_{d}.npz"
            if not f.exists():
                continue
            z = np.load(f)
            if "ntl" not in z:
                continue
            ntl = z["ntl"].astype(float)   # nW cm-2 sr-1 (float32 in collection 2)
            ok = (z["mqf"] != 255) & (((z["cld"].astype(int) >> 6) & 3) <= 1) & (ntl >= 0) & (ntl < 6000)
            vals[d] = np.where(ok, ntl, np.nan)
        if not vals:
            continue
        for w in windows[windows.rid.isin(set(rids))].itertuples():
            sel = rids == w.rid
            base_days = [d for d in vals if w.t0 - timedelta(days=30) <= d <= w.t0 - timedelta(days=3)]
            if len(base_days) < 5:
                continue
            B = np.array([vals[d][sel] for d in base_days])
            med = np.nanmedian(B, axis=0)
            sd = 1.4826 * np.nanmedian(np.abs(B - med), axis=0)
            nvalid = np.sum(np.isfinite(B), axis=0)
            d = w.t0
            while d <= w.t1:
                if d in vals:
                    x = vals[d][sel]
                    hit = np.isfinite(x) & (nvalid >= 5) & (x - med >= np.maximum(K_SIGMA * sd, MIN_EXCESS))
                    if hit.any():
                        pl = [p for p, m in zip(ex["pix"][hv], sel) if m]
                        hp = [pl[i] for i in np.nonzero(hit)[0]]
                        h, v = hv
                        for _, r, c in hp:
                            lat = 90 - 10 * v - (r + 0.5) * STEP
                            lon = -180 + 10 * h + (c + 0.5) * STEP
                            out[w.rid].append({"witness": "DNB", "d0": str(d), "d1": str(d), "lat": lat, "lon": lon,
                                               "half_m": 330.0})
                d += timedelta(days=1)
    return dict(out)

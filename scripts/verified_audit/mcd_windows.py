"""MCD64A1 burned pixels near given windows (rubric amendment A1).

Same tiles (Planetary Computer modis-64A1-061, item months Dec 2017 to Jan 2021) and the same reduction as
firewitness.caught.standard.load_mcd64a1 (pixel centre lat/lon, burn date from day of year, uncertainty days,
dedup on lat/lon/date, half_m = half the 463 m pixel diagonal); only a window around each disc is read.
"""
from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import numpy as np
import pandas as pd

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
FIRST, LAST = date(2017, 12, 1), date(2021, 1, 31)
_cat = None


def _catalog():
    global _cat
    if _cat is None:
        import planetary_computer as pc
        import pystac_client
        _cat = pystac_client.Client.open(STAC, modifier=pc.sign_inplace)
    return _cat


def _one(args):
    import planetary_computer as pc
    import rasterio
    from pyproj import Transformer
    from rasterio.windows import from_bounds

    lat, lon, r_m, t0, t1 = args
    a = max(FIRST, t0 - timedelta(days=100))
    b = min(LAST, t1 + timedelta(days=100))
    if a > b:
        return [], None
    pad = r_m + 1500.0
    dlat = pad / 111_000.0
    dlon = pad / (111_000.0 * max(math.cos(math.radians(lat)), 0.05))
    bbox = [lon - dlon, lat - dlat, lon + dlon, lat + dlat]
    import time
    for k in range(7):
        try:
            items = list(_catalog().search(collections=["modis-64A1-061"], bbox=bbox, datetime=f"{a}/{b}").items())
            break
        except Exception as e:  # rate limit: back off
            err = e
            time.sleep(3 * 2 ** k)
    else:
        return [], f"stac {type(err).__name__}"
    rows = []
    for it in items:
        it = pc.sign(it)
        try:
            with rasterio.open(it.assets["Burn_Date"].href) as s:
                tr_ = Transformer.from_crs("EPSG:4326", s.crs, always_xy=True)
                xs, ys = tr_.transform([bbox[0], bbox[2], bbox[0], bbox[2]], [bbox[1], bbox[1], bbox[3], bbox[3]])
                win = from_bounds(min(xs), min(ys), max(xs), max(ys), s.transform).round_offsets().round_lengths()
                win = win.intersection(rasterio.windows.Window(0, 0, s.width, s.height))
                bd = s.read(1, window=win)
                wtr = s.window_transform(win)
                crs = s.crs
            with rasterio.open(it.assets["Burn_Date_Uncertainty"].href) as s:
                un = s.read(1, window=win)
        except rasterio.errors.WindowError:
            continue
        except Exception as e:
            return [], f"read {it.id} {type(e).__name__}"
        r, cc = np.nonzero(bd > 0)
        if not len(r):
            continue
        x, y = rasterio.transform.xy(wtr, r, cc)
        lo, la = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform(np.asarray(x), np.asarray(y))
        year = int(it.id.split(".")[1][1:5])
        dates = pd.to_datetime([f"{year}-01-01"] * len(r)) + pd.to_timedelta(bd[r, cc].astype(int) - 1, unit="D")
        rows.append(pd.DataFrame({"lat": la, "lon": lo, "date": dates.date, "unc_days": un[r, cc].astype(int),
                                  "tile": it.id}))
    return rows, None


def pixels_near(w: pd.DataFrame, threads: int = 6):
    args = [(float(r.LATITUDE), float(r.LONGITUDE), float(r.r_m), r.t0, r.t1) for r in w.itertuples()]
    with ThreadPoolExecutor(threads) as ex:
        res = list(ex.map(_one, args))
    errs = [(w.rid.iloc[i], e) for i, (_, e) in enumerate(res) if e]
    parts = [p for rows, _ in res for p in rows]
    cols = ["lat", "lon", "date", "unc_days", "tile"]
    d = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)
    d = d.drop_duplicates(["lat", "lon", "date"])
    d["half_m"] = 0.5 * 463.3127 * np.sqrt(2)
    d["witness"] = "MCD64A1"
    return d.reset_index(drop=True), errs

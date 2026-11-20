"""Rule R3b: observed spread faster than the class can produce (protocol section 3, family 3).

Observed normal spread rate = 1 / |grad T| of the arrival-time raster (3x3 median smoothed), compared with the head-fire
rate of the cell's class from pyretechnics (Rothermel) under the maximum observed hourly wind of the interval between the
two perimeters that bracket the cell, the cell's slope and aspect, and the fast-spread moisture scenario.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

from . import spread

NODATA = -9999.0


def _med3(a):
    pad = np.pad(a, 1, constant_values=np.nan)
    st = np.stack([pad[i:i + a.shape[0], j:j + a.shape[1]] for i in range(3) for j in range(3)])
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return np.nanmedian(st, axis=0)


def observed_ros(arrival_hours: np.ndarray, cell: float = 30.0) -> np.ndarray:
    """m/min; nan where arrival is missing or flat (inside the first perimeter)."""
    T = arrival_hours.astype("float64")
    T[T == NODATA] = np.nan
    Ts = _med3(T)
    gy, gx = np.gradient(Ts, cell)             # hours per metre
    g = np.hypot(gx, gy)
    with np.errstate(divide="ignore", invalid="ignore"):
        ros = 1.0 / (g * 60.0)
    ros[~np.isfinite(ros) | (g < 1e-7)] = np.nan
    return ros


def interval_winds(fire_dir: Path):
    """For each perimeter interval k: (t_k hours, t_{k+1} hours, max 10 m wind m/s, wind-from direction deg at that hour)."""
    meta = json.loads((fire_dir / "meta.json").read_text())
    per = gpd.read_file(fire_dir / "perimeters.geojson")
    t0 = pd.Timestamp(meta["first_perimeter_utc"])
    th = np.array(sorted(((pd.Timestamp(t) - t0).total_seconds() / 3600.0) for t in per.t.unique()))
    w = pd.read_csv(fire_dir / "weather.csv", parse_dates=["time"])
    wh = (w.time - t0).dt.total_seconds().values / 3600.0
    out = []
    for a, b in zip(th[:-1], th[1:]):
        m = (wh >= a) & (wh <= b)
        if not m.any():
            m = np.ones(len(w), bool)
        i = np.argmax(np.where(m, w.wind_speed_10m.values, -1))
        out.append((a, b, float(w.wind_speed_10m.values[i]), float(w.wind_direction_10m.values[i])))
    return out


def r3b_mask(fire_dir: Path, fbfm: np.ndarray, cfg: dict):
    """-> (violation mask, observed ros, bound) on the fire grid. Raises spread.Unavailable if pyretechnics is absent."""
    R = cfg["rules"]["R3b"]
    mo = R["moisture"]
    with rasterio.open(fire_dir / "arrival_hours.tif") as s:
        T = s.read(1)
    ch = rasterio.open(fire_dir / "ch.tif").read(1).astype(float) / 10.0
    cc = rasterio.open(fire_dir / "cc.tif").read(1).astype(float) / 100.0
    slope = rasterio.open(fire_dir / "slope_deg.tif").read(1).astype(float)
    aspect = rasterio.open(fire_dir / "aspect.tif").read(1).astype(float)
    ros = observed_ros(T)
    iv = interval_winds(fire_dir)
    Tn = np.where(T == NODATA, np.nan, T)
    k = np.full(T.shape, -1)
    for i, (a, b, ws, wd) in enumerate(iv):
        k[(Tn >= a) & (Tn <= b) & (k < 0)] = i
    cls = fbfm.astype(int)
    burnable = np.isin(cls, [c for g, cs in cfg["groups"].items() if g != "NB" for c in cs])
    cand = np.isfinite(ros) & burnable & (k >= 0)
    bound = np.full(T.shape, np.nan)
    rr, cc_ = np.nonzero(cand)
    ws = np.array([iv[i][2] for i in k[rr, cc_]])
    wd = np.array([iv[i][3] for i in k[rr, cc_]])
    keys = np.stack([cls[rr, cc_], np.round(ws * 2).astype(int), np.round(wd / 10).astype(int),
                     np.round(np.nan_to_num(slope[rr, cc_]) / 2).astype(int), np.round(np.nan_to_num(aspect[rr, cc_]) / 15).astype(int),
                     np.round(ch[rr, cc_] / 2).astype(int), np.round(cc[rr, cc_] * 10).astype(int)], axis=1)
    uk, inv = np.unique(keys, axis=0, return_inverse=True)
    vals = np.zeros(len(uk))
    for j, (n, w2, d10, s2, a15, h2, c10) in enumerate(uk):
        vals[j] = spread.head_rate(int(n), w2 / 2.0, float(d10 * 10), math.tan(math.radians(s2 * 2.0)), float(a15 * 15), float(h2 * 2.0),
                                   min(1.0, c10 / 10.0), mo["d1"], mo["d10"], mo["d100"], mo["herb"], mo["woody"])
    bound[rr, cc_] = vals[inv.ravel()]
    timber_canopy = np.isin(cls, cfg["groups"]["TU"] + cfg["groups"]["TL"] + cfg["groups"]["SB"]) & (cc * 100 >= R["canopy_silent_cc"])
    viol = cand & (bound > 0) & (ros > R["factor"] * bound) & ~timber_canopy
    return viol, ros, bound

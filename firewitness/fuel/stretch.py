"""Stretch (protocol section 11): does replacing contradicted cells by the suggested class bring a simple spread
calculation closer to the observed arrival times?  Labelled stretch; not a gate.

Simple spread calculation: minimum travel time over a 90 m grid (8 neighbours), elliptical spread from the Rothermel
head-fire rate of each cell's class (pyretechnics via spread.py) under the mean observed wind of the burning period,
the cell's slope/aspect/canopy, and the fast-spread moisture scenario of R3b; ignition = the first perimeter.
The same calculation is run on the original and on the replaced fuel map.
"""
from __future__ import annotations
import heapq
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from . import spread

DIRS = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
F = 3  # 90 m


def modal_downsample(a, f=F):
    h, w = (a.shape[0] // f) * f, (a.shape[1] // f) * f
    b = a[:h, :w].reshape(h // f, f, w // f, f).transpose(0, 2, 1, 3).reshape(h // f, w // f, f * f)
    vals = np.sort(b, axis=2)
    out = np.zeros(vals.shape[:2], a.dtype)
    best = np.zeros(vals.shape[:2], int)
    for k in range(f * f):
        cnt = (vals == vals[:, :, k:k + 1]).sum(axis=2)
        upd = cnt > best
        best = np.where(upd, cnt, best)
        out = np.where(upd, vals[:, :, k], out)
    return out


def mean_wind(fire_dir: Path):
    """Mean 10 m wind speed (m/s) and vector-mean 'from' direction over the period between first and last perimeter."""
    meta = json.loads((fire_dir / "meta.json").read_text())
    w = pd.read_csv(fire_dir / "weather.csv", parse_dates=["time"])
    t0, t1 = pd.Timestamp(meta["first_perimeter_utc"]), pd.Timestamp(meta["last_perimeter_utc"])
    m = w[(w.time >= t0) & (w.time <= t1)]
    m = m if len(m) else w
    th = np.deg2rad(m.wind_direction_10m.values)
    u, v = (m.wind_speed_10m.values * np.sin(th)).mean(), (m.wind_speed_10m.values * np.cos(th)).mean()
    return float(m.wind_speed_10m.mean()), float((math.degrees(math.atan2(u, v)) + 360) % 360)


def rate_grid(fb, slope, aspect, ch, cc, wind, wdir, mo):
    """Head-fire rate (m/min) per 90 m cell."""
    H, W = fb.shape
    red = lambda a: a[:H * F, :W * F].reshape(H, F, W, F).mean(axis=(1, 3))  # noqa: E731
    sl, asp, chm, ccv = red(np.nan_to_num(slope)), red(np.nan_to_num(aspect)), red(ch) / 10.0, red(cc) / 100.0
    keys = np.stack([fb, np.round(sl / 3).astype(int), np.round(asp / 30).astype(int), np.round(chm / 4).astype(int),
                     np.round(ccv * 5).astype(int)], axis=-1).reshape(-1, 5)
    uk, inv = np.unique(keys, axis=0, return_inverse=True)
    vals = np.array([spread.head_rate(int(n), round(wind, 1), round(wdir / 5) * 5.0, math.tan(math.radians(s * 3.0)), a * 30.0,
                                      h * 4.0, min(1.0, c / 5.0), mo["d1"], mo["d10"], mo["d100"], mo["herb"], mo["woody"])
                     for n, s, a, h, c in uk])
    return vals[inv.ravel()].reshape(H, W)


def travel_time(rate, ignition, wind, wdir, cell=30.0 * F):
    """Arrival hours on the 90 m grid (inf = not reached). Ellipse eccentricity from a mph-wind length-to-width ratio."""
    H, W = rate.shape
    down = math.radians((wdir + 180) % 360)
    lw = 1.0 + 0.25 * wind * 2.237
    e = math.sqrt(max(lw * lw - 1.0, 0.0)) / lw
    T = np.full((H, W), np.inf)
    pq = []
    for i, j in zip(*np.nonzero(ignition)):
        T[i, j] = 0.0
        pq.append((0.0, int(i), int(j)))
    heapq.heapify(pq)
    while pq:
        t, i, j = heapq.heappop(pq)
        if t > T[i, j]:
            continue
        for di, dj in DIRS:
            a, b = i + di, j + dj
            if not (0 <= a < H and 0 <= b < W):
                continue
            r_src, r_dst = rate[i, j], rate[a, b]
            if r_src <= 0 or r_dst <= 0:
                continue
            th = math.atan2(dj, -di) - down
            fac = (1 - e) / (1 - e * math.cos(th))
            r = 0.5 * (r_src + r_dst) * fac
            tt = t + cell * (math.sqrt(2) if di and dj else 1.0) / max(r, 1e-6) / 60.0
            if tt < T[a, b]:
                T[a, b] = tt
                heapq.heappush(pq, (tt, a, b))
    return T


def run_fire(fire_dir: Path, fb_orig, fb_new, cfg):
    """MAE (hours) of predicted vs observed arrival for the original and the replaced map, plus share of observed cells reached."""
    mo = cfg["rules"]["R3b"]["moisture"]
    with rasterio.open(fire_dir / "arrival_hours.tif") as s:
        obs = s.read(1)
    ch = rasterio.open(fire_dir / "ch.tif").read(1).astype(float)
    cc = rasterio.open(fire_dir / "cc.tif").read(1).astype(float)
    sl = rasterio.open(fire_dir / "slope_deg.tif").read(1).astype(float)
    asp = rasterio.open(fire_dir / "aspect.tif").read(1).astype(float)
    wind, wdir = mean_wind(fire_dir)
    obs_c = np.where(obs == -9999, np.nan, obs)
    ign = np.nan_to_num(obs_c, nan=1e9) <= 0
    H, W = obs.shape[0] // F, obs.shape[1] // F
    ign_c = ign[:H * F, :W * F].reshape(H, F, W, F).any(axis=(1, 3))
    obs90 = _nanmean_blocks(obs_c, H, W)
    m = np.isfinite(obs90) & (obs90 > 0)
    Ts = {}
    for name, fb in (("original", fb_orig), ("replaced", fb_new)):
        rate = rate_grid(modal_downsample(fb.astype(np.int16)), sl, asp, ch, cc, wind, wdir, mo)
        Ts[name] = travel_time(rate, ign_c, wind, wdir)
    # one scale factor per fire, fitted on the ORIGINAL map and applied to both (daily perimeters make absolute rates coarse)
    r0 = m & np.isfinite(Ts["original"]) & (Ts["original"] > 0)
    k = float(np.median(obs90[r0] / Ts["original"][r0])) if r0.any() else float("nan")
    from scipy.stats import spearmanr
    res = {}
    for name, T in Ts.items():
        reached = m & np.isfinite(T)
        mae = float(np.abs(k * T[reached] - obs90[reached]).mean()) if reached.any() else float("nan")
        rho = float(spearmanr(T[reached], obs90[reached])[0]) if reached.sum() > 10 else float("nan")
        res[name] = {"mae_h_scaled": mae, "spearman": rho, "reached_share": float(reached.sum() / max(m.sum(), 1)), "n": int(m.sum())}
    res["scale"], res["wind_mps"], res["wind_from"] = k, wind, wdir
    return res


def _nanmean_blocks(a, H, W):
    b = a[:H * F, :W * F].reshape(H, F, W, F).transpose(0, 2, 1, 3).reshape(H, W, F * F)
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return np.nanmean(b, axis=2)

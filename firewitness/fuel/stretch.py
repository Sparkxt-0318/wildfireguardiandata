"""Stretch (protocol section 11): does replacing contradicted cells by the suggested class bring a simple spread
calculation closer to the observed arrival times?  Labelled stretch; not a gate.

Simple spread calculation: minimum travel time over a 90 m grid (8 neighbours), elliptical spread from the Rothermel
head-fire rate of each cell's class (pyretechnics, see spread.py) under the mean observed wind of the burning period,
the cell's slope and aspect, the fast-spread moisture scenario of R3b; ignition = cells inside the first perimeter.
"""
from __future__ import annotations
import heapq
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from . import spread

DIRS = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]


def _modal_downsample(a, f):
    h, w = (a.shape[0] // f) * f, (a.shape[1] // f) * f
    b = a[:h, :w].reshape(h // f, f, w // f, f).transpose(0, 2, 1, 3).reshape(h // f, w // f, f * f)
    vals = np.sort(b, axis=2)
    # mode of each block via run lengths on the sorted axis
    out = np.zeros(vals.shape[:2], a.dtype)
    best = np.zeros(vals.shape[:2], int)
    for k in range(f * f):
        cnt = (vals == vals[:, :, k:k + 1]).sum(axis=2)
        upd = cnt > best
        best = np.where(upd, cnt, best)
        out = np.where(upd, vals[:, :, k], out)
    return out


def mean_wind(weather: pd.DataFrame, t0, t1):
    w = weather[(weather.time >= t0) & (weather.time <= t1)]
    if w.empty:
        w = weather
    s = w.wind_speed_10m.values
    th = np.deg2rad(w.wind_direction_10m.values)
    u, v = (s * np.sin(th)).mean(), (s * np.cos(th)).mean()   # mean of "from" vectors
    return float(np.hypot(u, v) if False else s.mean()), float((math.degrees(math.atan2(u, v)) + 360) % 360)


def travel_time(fbfm, slope_deg, aspect, ch, cc, ignition, wind_mps, wind_from, moisture, factor=3, cell=30.0):
    """Arrival time in hours on the coarse grid (np.inf = not reached)."""
    f = factor
    fb = _modal_downsample(fbfm.astype(np.int16), f)
    H, W = fb.shape
    sl = slope_deg[:H * f, :W * f].reshape(H, f, W, f).mean(axis=(1, 3))
    asp = aspect[:H * f, :W * f].reshape(H, f, W, f).mean(axis=(1, 3))
    chm = ch[:H * f, :W * f].reshape(H, f, W, f).mean(axis=(1, 3)) / 10.0       # LANDFIRE CH is m*10
    ccv = cc[:H * f, :W * f].reshape(H, f, W, f).mean(axis=(1, 3)) / 100.0
    ig = ignition[:H * f, :W * f].reshape(H, f, W, f).any(axis=(1, 3))
    rate = np.zeros((H, W)); ecc = np.zeros((H, W)); sdir = np.zeros((H, W))
    m = moisture
    for (i, j), n in np.ndenumerate(fb):
        pass  # placeholder to keep vectorised below
    uniq = {}
    for i in range(H):
        for j in range(W):
            n = int(fb[i, j])
            key = (n, int(round(sl[i, j] / 3.0)), int(round(asp[i, j] / 30.0)), int(round(chm[i, j] / 4.0)), int(round(ccv[i, j] / 0.2)))
            if key not in uniq:
                rr = spread.head_rate(n, round(wind_mps, 1), round(wind_from / 5.0) * 5.0,
                                      math.tan(math.radians(key[1] * 3.0)), key[2] * 30.0, key[3] * 4.0, min(1.0, key[4] * 0.2),
                                      m["d1"], m["d10"], m["d100"], m["herb"], m["woody"])
                uniq[key] = rr
            rate[i, j] = uniq[key]
    # head direction approximated by the wind's downwind direction (slope effect on direction ignored: simple calculation)
    down = math.radians((wind_from + 180) % 360)
    lw = 1.0 + 0.25 * wind_mps * 2.237            # Anderson (1983) style length-to-width from the mph wind
    e = math.sqrt(max(lw * lw - 1.0, 0)) / lw
    inf = float("inf")
    T = np.full((H, W), inf)
    pq = []
    for i, j in zip(*np.nonzero(ig[:H, :W])):
        T[i, j] = 0.0
        pq.append((0.0, int(i), int(j)))
    heapq.heapify(pq)
    cs = cell * f
    while pq:
        t, i, j = heapq.heappop(pq)
        if t > T[i, j]:
            continue
        r_head = rate[i, j]
        if r_head <= 0:
            continue
        for di, dj in DIRS:
            a, b = i + di, j + dj
            if not (0 <= a < H and 0 <= b < W):
                continue
            dist = cs * (math.sqrt(2) if di and dj else 1.0)
            bearing = math.atan2(dj, -di)               # clockwise from north
            th = bearing - down
            r = r_head * (1 - e) / (1 - e * math.cos(th))
            r2 = rate[a, b]
            if r2 <= 0:
                continue
            r = min(r, r_head * (r2 / r_head if r2 < r_head else 1.0)) if False else 0.5 * (r + r2 * (1 - e) / (1 - e * math.cos(th)))
            tt = t + dist / max(r, 1e-6) / 60.0            # m/min -> hours
            if tt < T[a, b]:
                T[a, b] = tt
                heapq.heappush(pq, (tt, a, b))
    return T


def score(pred_hours, obs_hours, mask):
    """Mean absolute error in hours over cells that burned in reality and were reached (and the share reached)."""
    m = mask & np.isfinite(pred_hours)
    if not m.any():
        return float("nan"), 0.0
    return float(np.abs(pred_hours[m] - obs_hours[m]).mean()), float(m.sum() / max(mask.sum(), 1))

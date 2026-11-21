"""v0.2 tool: table-wide time offsets against satellite first detections (protocol v0.2, section 2).

One offset per group (source system x table x year), estimated from many fires and applied to the whole group,
never chosen per record. A fire cannot be detected before it starts: under the true convention the earliest
detections do not precede the implied start; if the table is shifted, they precede it by about the shift.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from . import geo, paths

STATE_TZ = {}
_TZ = {"America/New_York": "CT DE DC FL GA IN KY ME MD MA MI NH NJ NY NC OH PA RI SC TN VT VA WV",
        "America/Chicago": "AL AR IL IA KS LA MN MS MO NE ND OK SD TX WI",
        "America/Denver": "AZ CO ID MT NM UT WY",
        "America/Los_Angeles": "CA NV OR WA", "America/Anchorage": "AK", "Pacific/Honolulu": "HI"}
for tz, ss in _TZ.items():
    for s in ss.split():
        STATE_TZ[s] = tz
STATE_TZ["AZ"] = "America/Phoenix"      # no daylight saving time


class FirstDetection:
    """FIRMS detections with UTC hour-of-epoch; query: earliest detection near a point inside a day window."""

    def __init__(self, years):
        frames = []
        for y in years:
            for f in sorted((paths.RAW / "firms").glob(f"*_{y}_United_States.csv")):
                d = pd.read_csv(f, usecols=["latitude", "longitude", "acq_date", "acq_time"], dtype={"acq_time": str})
                day = (pd.to_datetime(d["acq_date"]) - pd.Timestamp("1970-01-01")).dt.days.to_numpy(np.int64)
                hhmm = pd.to_numeric(d["acq_time"], errors="coerce").fillna(0).to_numpy(np.int64)
                t = day * 24.0 + (hhmm // 100) + (hhmm % 100) / 60.0
                frames.append(pd.DataFrame({"lat": d["latitude"].to_numpy(np.float32), "lon": d["longitude"].to_numpy(np.float32), "t": t}))
        d = pd.concat(frames, ignore_index=True)
        self.lat, self.lon, self.t = d.lat.to_numpy(), d.lon.to_numpy(), d.t.to_numpy()
        self.tree = cKDTree(geo.xyz(self.lat, self.lon))

    def first(self, lat, lon, t0, t1, radius_km=5.0):
        """Earliest detection time (UTC hours since epoch) within radius and [t0, t1] per point; NaN if none."""
        lat, lon, t0, t1 = map(lambda a: np.asarray(a, float), (lat, lon, t0, t1))
        out = np.full(len(lat), np.nan)
        ok = np.flatnonzero(np.isfinite(lat) & np.isfinite(lon) & np.isfinite(t0) & np.isfinite(t1))
        lists = self.tree.query_ball_point(geo.xyz(lat[ok], lon[ok]), geo.km_to_chord(radius_km), workers=4)
        for k, h in zip(ok, lists):
            if h:
                tt = self.t[h]
                m = (tt >= t0[k]) & (tt <= t1[k])
                if m.any():
                    out[k] = tt[m].min()
        return out


def local_to_utc_hours(start: pd.Series, states) -> np.ndarray:
    """Naive local clock datetimes -> UTC hours since epoch, using each state's main time zone (daylight saving included)."""
    out = np.full(len(start), np.nan)
    st = pd.Series(list(states), index=start.index)
    for tz in sorted(set(STATE_TZ.values())):
        sel = st.map(STATE_TZ).eq(tz).to_numpy() & start.notna().to_numpy()
        if not sel.any():
            continue
        loc = start[sel].dt.tz_localize(tz, ambiguous="NaT", nonexistent="NaT")
        utc = loc.dt.tz_convert("UTC").dt.tz_localize(None)
        out[sel] = ((utc - pd.Timestamp("1970-01-01")) / pd.Timedelta(hours=1)).to_numpy()
    return out


def naive_hours(start: pd.Series) -> np.ndarray:
    return ((start - pd.Timestamp("1970-01-01")) / pd.Timedelta(hours=1)).to_numpy(float)


def residuals(fd: FirstDetection, lat, lon, start: pd.Series, states, window_hours=(-24, 96)):
    """r_i = first detection (UTC h) minus the start implied if the recorded time is local clock time."""
    u = local_to_utc_hours(start, states)
    d = fd.first(lat, lon, u + window_hours[0], u + window_hours[1])
    return d - u


LAG_WINDOW = (-2.0, 24.0)      # hours: a detection inside this window after the implied start counts as "plausible"
VIOL = -3.0                    # hours: a detection earlier than this before the implied start is a violation
MIN_GAIN = 0.01                # protocol v0.2 amendment of 2026-11-21: margin of the share gain
VIOL_FACTOR = 0.75             # violations must fall to at most this fraction


def utc_to_local_naive(start: pd.Series, states) -> pd.Series:
    """Recorded value read as UTC -> naive local clock time of the state's main time zone."""
    out = pd.Series(pd.NaT, index=start.index, dtype="datetime64[ns]")
    st = pd.Series(list(states), index=start.index)
    for tz in sorted(set(STATE_TZ.values())):
        sel = st.map(STATE_TZ).eq(tz).to_numpy() & start.notna().to_numpy()
        if sel.any():
            out[sel] = start[sel].dt.tz_localize("UTC").dt.tz_convert(tz).dt.tz_localize(None)
    return out


def hypothesis_shares(d: np.ndarray, u_local: np.ndarray, u_utc: np.ndarray, shifts=range(-12, 13)) -> dict:
    """Share of fires whose first detection falls in the plausible lag window under each convention.
    H0 recorded=local, H1 recorded=UTC, S<k> recorded runs late by k hours relative to local."""
    out = {}
    def share(r):
        return float(((r >= LAG_WINDOW[0]) & (r <= LAG_WINDOW[1])).mean())
    out["H0"] = share(d - u_local)
    out["H1"] = share(d - u_utc)
    for k in shifts:
        if k:
            out[f"S{k:+d}"] = share(d - (u_local + k))      # implied start moved later by k: recorded runs EARLY by k if k>0
    return out


def _best_shift(sh: dict):
    ks = [k for k in sh if k.startswith("S")]
    k = max(ks, key=lambda x: sh[x])
    return k, sh[k]


def estimate_group(d, u_local, u_utc, cluster=None, n_boot=500, seed=0, min_n=30) -> dict:
    """d: first detection (UTC h), u_local / u_utc: implied start under H0 (recorded = local) / H1 (recorded = UTC).

    Decision (protocol v0.2 section 2): H1 (UTC) if its share of plausible lags exceeds H0's by a clear margin
    (bootstrap lower bound above 0.03, both split halves agree); else a fixed shift if one beats both H0 and H1 the
    same way; else no offset found. n counts fires with a first detection."""
    d, u_local, u_utc = (np.asarray(a, float) for a in (d, u_local, u_utc))
    ok = np.isfinite(d) & np.isfinite(u_local) & np.isfinite(u_utc)
    n = int(ok.sum())
    res = {"n": n}
    if n < min_n:
        res["outcome"] = "insufficient fires"
        return res
    d, ul, uu = d[ok], u_local[ok], u_utc[ok]
    cl = np.arange(n) if cluster is None else np.asarray(cluster)[ok]
    sh = hypothesis_shares(d, ul, uu)
    ks, vs = _best_shift(sh)
    res.update({"share_H0": round(sh["H0"], 3), "share_H1": round(sh["H1"], 3), "best_shift": ks, "share_best_shift": round(vs, 3)})
    u, inv = np.unique(cl, return_inverse=True)
    groups = [np.flatnonzero(inv == i) for i in range(len(u))]
    rng = np.random.default_rng(seed)
    g1, gs = [], []
    for _ in range(n_boot):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        s2 = hypothesis_shares(d[idx], ul[idx], uu[idx])
        g1.append(s2["H1"] - s2["H0"])
        k2, v2 = _best_shift(s2)
        gs.append(v2 - max(s2["H0"], s2["H1"]))
    res["gain_H1_over_H0"] = float(sh["H1"] - sh["H0"])
    res["gain_H1_ci"] = (float(np.percentile(g1, 2.5)), float(np.percentile(g1, 97.5)))
    res["gain_shift_over_best_of_H0_H1"] = float(vs - max(sh["H0"], sh["H1"]))
    res["gain_shift_ci"] = (float(np.percentile(gs, 2.5)), float(np.percentile(gs, 97.5)))
    half = (np.arange(n) % 2) == 0
    halves = [hypothesis_shares(d[m], ul[m], uu[m]) for m in (half, ~half)]
    res["split_half_gain_H1"] = [float(h["H1"] - h["H0"]) for h in halves]
    res["violations_H0"] = float(((d - ul) < VIOL).mean())
    res["violations_H1"] = float(((d - uu) < VIOL).mean())
    if res["gain_H1_ci"][0] > MIN_GAIN and all(g > MIN_GAIN for g in res["split_half_gain_H1"]) and res["violations_H1"] <= res["violations_H0"] * VIOL_FACTOR:
        res["outcome"] = "offset: recorded in UTC"
        res["convention"] = "H1"
    elif res["gain_H1_ci"][1] < -MIN_GAIN or (sh["H0"] >= max(sh["H1"], vs) - 0.005):
        res["outcome"] = "no offset found (local clock time fits)"
    elif res["gain_shift_ci"][0] > MIN_GAIN and halves and all(_best_shift(h)[0] == ks for h in halves):
        res["outcome"] = f"offset: corrected by {int(ks[1:]):+d} h"
        res["convention"] = ks
    else:
        res["outcome"] = "no offset found (not clear)"
    return res

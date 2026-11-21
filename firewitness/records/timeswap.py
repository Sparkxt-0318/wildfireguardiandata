"""v0.3 day-month swap test (protocol v0.3 section 2): per group (source system x table x year, and pooled), does reading the
recorded date as day-month instead of month-day make the satellite first detections fit better.  Never per record."""
from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from . import paths, timeoffset as T
from .timeoffset_run import ics_frame

MIN_ACRES = 300.0
MIN_GAP_DAYS = 10          # the two readings must differ by this many days, so their windows do not overlap
FIT_DAYS = (-1, 3)         # first detection UTC date minus the implied start date, in days
SEARCH_DAYS = (-3, 15)     # per-reading search window, days from the implied start date
MIN_N = 30
M_SWAP = 0.10              # provisional margins of the protocol; changes only by amendment, from dev
M_NONE = 0.0


def fod_date_frame(min_acres=MIN_ACRES) -> pd.DataFrame:
    c = sqlite3.connect(paths.WORK / "fpafod" / "Data" / "FPA_FOD_20260615.gpkg")
    d = pd.read_sql("select FOD_ID, SOURCE_SYSTEM, FIRE_YEAR, DISCOVERY_DATE, FIRE_SIZE, LATITUDE, LONGITUDE, STATE from Fires where FIRE_SIZE >= ?", c, params=(min_acres,))
    return pd.DataFrame({"rid": "fod:" + d.FOD_ID.astype(str), "table": "fpafod", "system": d.SOURCE_SYSTEM, "inc": "fod:" + d.FOD_ID.astype(str),
                         "lat": d.LATITUDE, "lon": d.LONGITUDE, "start": pd.to_datetime(d.DISCOVERY_DATE.str[:10], errors="coerce"),
                         "acres": d.FIRE_SIZE, "state": d.STATE, "year": d.FIRE_YEAR.astype(int)})


def all_frames(cfg) -> pd.DataFrame:
    a = ics_frame(cfg)[["rid", "table", "system", "inc", "lat", "lon", "start", "acres", "state", "year"]]
    allr = pd.concat([a, fod_date_frame()], ignore_index=True)
    allr = allr[(allr.year >= 2001) & (allr.acres >= MIN_ACRES) & allr.state.notna() & allr.lat.notna() & allr.start.notna()]
    return allr.reset_index(drop=True)


def swapped_date(start: pd.Series) -> pd.Series:
    y, m, d = start.dt.year, start.dt.month, start.dt.day
    ok = d <= 12
    s = pd.to_datetime(pd.DataFrame({"year": y, "month": np.where(ok, d, m), "day": np.where(ok, m, d)}), errors="coerce")
    return s.where(ok)


def eligible_mask(g: pd.DataFrame) -> np.ndarray:
    s = g.start
    sw = swapped_date(s)
    gap = (sw.dt.normalize() - s.dt.normalize()).dt.days.abs()
    return ((s.dt.day <= 12) & (s.dt.day != s.dt.month) & sw.notna() & (gap >= MIN_GAP_DAYS)).to_numpy()


def fit_flags(fd: T.FirstDetection, g: pd.DataFrame):
    """For the eligible fires of g: first-detection fit under the recorded reading and under the swapped reading."""
    g = g[eligible_mask(g)].reset_index(drop=True)
    days = {}
    for name, s in (("o", g.start.dt.normalize()), ("s", swapped_date(g.start).dt.normalize())):
        D = ((s - pd.Timestamp("1970-01-01")) / pd.Timedelta(days=1)).to_numpy(float)
        f = fd.first(g.lat.to_numpy(), g.lon.to_numpy(), 24 * (D + SEARCH_DAYS[0]), 24 * (D + SEARCH_DAYS[1]))
        diff = np.floor(f / 24.0) - D
        days[name] = (f, ((diff >= FIT_DAYS[0]) & (diff <= FIT_DAYS[1])).astype(float))
    has = np.isfinite(days["o"][0]) | np.isfinite(days["s"][0])
    g = g[has].reset_index(drop=True)
    return g, days["o"][1][has], days["s"][1][has]


def estimate(fit_o, fit_s, cluster, n_boot=500, seed=0, min_n=MIN_N, m_swap=M_SWAP, m_none=M_NONE):
    n = int(len(fit_o))
    if n < min_n:
        return {"n": n, "outcome": "insufficient fires"}
    cl = np.asarray(cluster)
    keys, inv = np.unique(cl, return_inverse=True)
    gain = float(fit_s.mean() - fit_o.mean())
    rng = np.random.default_rng(seed)
    d = fit_s - fit_o
    sums = np.bincount(inv, weights=d, minlength=len(keys))
    cnt = np.bincount(inv, minlength=len(keys)).astype(float)
    boots = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, len(keys), len(keys))
        boots[b] = sums[pick].sum() / max(cnt[pick].sum(), 1.0)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    odd = (inv % 2 == 1)
    halves = [float(d[odd].mean()) if odd.any() else float("nan"), float(d[~odd].mean()) if (~odd).any() else float("nan")]
    if lo > m_swap and min(halves) > m_swap:
        out = "swap: day-month order"
    elif hi < m_none:
        out = "no swap"
    else:
        out = "not clear"
    return {"n": n, "share_orig": float(fit_o.mean()), "share_swap": float(fit_s.mean()), "gain_swap_over_orig": gain,
            "gain_ci": [float(lo), float(hi)], "split_half_gain": halves, "outcome": out}


def run_groups(allr: pd.DataFrame, years, pooled_label=None, n_boot=500):
    """Year groups and pooled (system x table) groups for the given years. Returns (year table, pooled table, cache)."""
    sel = allr[allr.year.isin(list(years))]
    fd = T.FirstDetection(sorted(set(int(y) for y in years)))
    rows, cache = [], {}
    for (sysm, tab, yr), g in sel.groupby(["system", "table", "year"]):
        gg, fo, fs = fit_flags(fd, g)
        cache[(sysm, tab, int(yr))] = (fo, fs, gg.inc.to_numpy(), gg.rid.to_numpy())
        r = estimate(fo, fs, gg.inc.to_numpy(), n_boot=n_boot)
        rows.append({"system": sysm, "table": tab, "year": int(yr), "records_in_group": int(len(g)), "eligible_records": int(eligible_mask(g).sum()), **r})
    keys = {}
    for (sysm, tab, yr) in cache:
        keys.setdefault((sysm, tab), []).append(yr)
    pooled = []
    for (sysm, tab), yrs in keys.items():
        fo, fs, cl = [np.concatenate([cache[(sysm, tab, y)][i] for y in yrs]) for i in (0, 1, 2)]
        pooled.append({"system": sysm, "table": tab, "years": f"{min(yrs)}-{max(yrs)}", **estimate(fo, fs, cl, n_boot=n_boot)})
    return pd.DataFrame(rows), pd.DataFrame(pooled), cache


def planted_trials(cache, groups, sizes=(100, 300, 1000), trials=60, seed=0, minority=0.3, n_boot=300):
    """Plant a table-wide swap (the recorded reading is the swapped one), nothing, and a minority swap into subsamples of dev groups."""
    from .gates import wilson
    rng = np.random.default_rng(seed)
    keys = {}
    for (s, t, y) in cache:
        keys.setdefault((s, t), []).append(y)
    pools = []
    for (s, t) in groups:
        ys = keys.get((s, t), [])
        if ys:
            fo, fs, cl = [np.concatenate([cache[(s, t, y)][i] for y in ys]) for i in (0, 1, 2)]
            pools.append((fo, fs, cl))
    out = {}
    for n in sizes:
        tot = swap_found = swap_false = minority_found = 0
        for fo, fs, cl in pools:
            if len(fo) < n:
                continue
            for _ in range(trials):
                idx = rng.choice(len(fo), n, replace=False)
                o, s, c = fo[idx], fs[idx], cl[idx]
                tot += 1
                swap_found += estimate(s, o, c, n_boot=n_boot)["outcome"].startswith("swap")
                swap_false += estimate(o, s, c, n_boot=n_boot)["outcome"].startswith("swap")
                flip = rng.random(n) < minority
                o2, s2 = np.where(flip, s, o), np.where(flip, o, s)
                minority_found += estimate(o2, s2, c, n_boot=n_boot)["outcome"].startswith("swap")
        out[str(n)] = {"trials": tot, "planted_swap_called": int(swap_found), "planted_ci": wilson(int(swap_found), max(tot, 1)),
                       "unplanted_called_swap": int(swap_false), "unplanted_ci": wilson(int(swap_false), max(tot, 1)),
                       "minority_%d_called_swap" % int(minority * 100): int(minority_found)}
    return out

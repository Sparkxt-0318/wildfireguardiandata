"""v0.4 AM/PM hypothesis for the unexplained -12 hour shift of the OK Forestry list (protocol v0.4 section 3)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import paths, timeoffset as T

RULES = ("R0", "R1", "R2", "R3")
LAG = T.LAG_WINDOW


def ok_frame() -> pd.DataFrame:
    """OK Forestry list: local discovery date plus hhmm, one row per fire, all acres."""
    from .statelists import _read
    b = _read(paths.RAW / "state_lists/ok_historical_fire_occurrence.ndjson")
    d0 = pd.to_datetime(pd.to_numeric(b.FireDiscoveryDate, errors="coerce"), unit="ms").dt.normalize()
    hh = pd.to_numeric(b.FireDiscoveryTime, errors="coerce")
    okt = hh.notna() & (hh >= 0) & (hh <= 2359) & ((hh % 100) < 60)
    start = d0 + pd.to_timedelta(np.where(okt, (hh // 100) * 60 + (hh % 100), np.nan), unit="m")
    f = pd.DataFrame({"rid": "ok:" + b.OBJECTID.astype(str), "inc": "ok:" + b.OBJECTID.astype(str), "lat": b.Latitude.fillna(b._lat), "lon": b.Longitude.fillna(b._lon),
                      "start": start, "hour": np.where(okt, (hh // 100), np.nan), "acres": pd.to_numeric(b.FinalFireAcreQuantity, errors="coerce"), "state": "OK"})
    f["year"] = f.start.dt.year
    return f[okt.to_numpy()].reset_index(drop=True)


def apply_rule(start: pd.Series, rule: str) -> pd.Series:
    """Recorded clock time -> corrected clock time under a table-wide AM/PM rule (then read as local time)."""
    h = start.dt.hour
    if rule == "R0":
        return start
    if rule == "R1":
        return start - pd.Timedelta(hours=12)
    if rule == "R2":      # PM lost: recorded hours 1..11 gain 12 h
        return start + pd.to_timedelta(np.where((h >= 1) & (h <= 11), 12, 0), unit="h")
    if rule == "R3":      # AM/PM flipped: hours 0..11 gain 12 h, hours 12..23 lose 12 h, same date
        return start + pd.to_timedelta(np.where(h <= 11, 12, -12), unit="h")
    raise ValueError(rule)


def lags(fd: T.FirstDetection, g: pd.DataFrame) -> dict:
    """One first detection per fire over a window that covers every rule's implied start; lag = detection minus implied start."""
    us = {r: T.local_to_utc_hours(apply_rule(g["start"].reset_index(drop=True), r), g["state"].tolist()) for r in RULES}
    u_utc = T.naive_hours(g["start"].reset_index(drop=True))
    stack = np.vstack(list(us.values()) + [u_utc])
    d = fd.first(g["lat"].to_numpy(), g["lon"].to_numpy(), np.nanmin(stack, axis=0) - 24, np.nanmax(stack, axis=0) + 96)
    ok = np.isfinite(d)
    return {"ok": ok, "d": d, **{r: d - us[r] for r in RULES}}


def share(lag):
    return float(((lag >= LAG[0]) & (lag <= LAG[1])).mean()) if len(lag) else float("nan")


def evaluate(L: dict, cluster, n_boot=500, seed=0, mask=None) -> dict:
    """Fit share per rule on the fires with a detection, and the bootstrap interval of the gain of R2/R3 over the better of R0 and R1."""
    ok = L["ok"] if mask is None else (L["ok"] & mask)
    lag = {r: L[r][ok] for r in RULES}
    n = int(ok.sum())
    out = {"n": n, **{f"share_{r}": share(lag[r]) for r in RULES}}
    if n < 10:
        return out
    cl = np.asarray(cluster)[ok]
    keys, inv = np.unique(cl, return_inverse=True)
    hit = {r: ((lag[r] >= LAG[0]) & (lag[r] <= LAG[1])).astype(float) for r in RULES}
    sums = {r: np.bincount(inv, weights=hit[r], minlength=len(keys)) for r in RULES}
    cnt = np.bincount(inv, minlength=len(keys)).astype(float)
    rng = np.random.default_rng(seed)
    gains = {r: np.empty(n_boot) for r in ("R2", "R3")}
    for b in range(n_boot):
        pick = rng.integers(0, len(keys), len(keys))
        c = max(cnt[pick].sum(), 1.0)
        s = {r: sums[r][pick].sum() / c for r in RULES}
        base = max(s["R0"], s["R1"])
        for r in ("R2", "R3"):
            gains[r][b] = s[r] - base
    base0 = max(out["share_R0"], out["share_R1"])
    for r in ("R2", "R3"):
        out[f"gain_{r}_over_best_of_R0_R1"] = out[f"share_{r}"] - base0
        out[f"gain_{r}_ci"] = [float(np.percentile(gains[r], 2.5)), float(np.percentile(gains[r], 97.5))]
    out["gain_R1_over_R0"] = out["share_R1"] - out["share_R0"]
    return out

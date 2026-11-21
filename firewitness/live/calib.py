"""v0.2 candidate (dev exploration): empirical null of the site score u by local solar hour.

u is mapped through the placebo distribution of its local hour, F_h, to a standard normal score
u' = Phi^-1(F_h(u)) (tails extrapolated with the Gaussian beyond the last quantile)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.special import ndtri

QS = np.concatenate([np.linspace(0.0, 0.99, 100), 1 - np.logspace(-2.3, -6, 30)])


def build_table(evals_base, ukey, firms, fids, n_per=4000, seed=0):
    from . import detector as dt
    rng = np.random.default_rng(seed)
    by = [[] for _ in range(24)]
    for fid in fids:
        base = dt.ensure_base(fid, firms)
        uE, _ = dt.ensure_u(fid, ukey, base)
        lon = base["lon"].astype(float)
        for d in range(1, 9):
            ts = base["tscanE"][d]
            ok = np.isfinite(ts)
            clean = base["clean"][d]
            for k in np.where(ok)[0]:
                lh = ((ts[k] / 3600 + lon[clean] / 15) % 24).astype(int)
                u = uE[d][k][clean].astype(float)
                f = np.isfinite(u)
                for h in np.unique(lh[f]):
                    x = u[f & (lh == h)]
                    if len(x) > 50:
                        x = rng.choice(x, 50, replace=False)
                    by[h].append(x)
    table = {}
    for h in range(24):
        x = np.concatenate(by[h]) if by[h] else np.zeros(1)
        table[h] = np.quantile(x, QS).tolist()
    return {"qs": QS.tolist(), "table": table}


def transform(u, local_hour, cal):
    qs = np.asarray(cal["qs"])
    out = np.full(np.shape(u), np.nan, np.float32)
    u = np.asarray(u, float)
    lh = np.asarray(local_hour).astype(int) % 24
    for h in np.unique(lh[np.isfinite(u)]):
        q = np.asarray(cal["table"][str(h)] if str(h) in cal["table"] else cal["table"][h])
        sel = (lh == h) & np.isfinite(u)
        p = np.interp(u[sel], q, qs, left=0.0, right=qs[-1])
        p = np.clip(p, 1e-7, 1 - 1e-7)
        z = ndtri(p)
        beyond = u[sel] > q[-1]
        z = np.where(beyond, ndtri(qs[-1]) + (u[sel] - q[-1]), z)   # beyond the last quantile: grow linearly
        out[sel] = z
    return out

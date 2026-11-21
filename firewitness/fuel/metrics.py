"""Gate statistics (protocol section 6). Plot-level table in, numbers with intervals out."""
from __future__ import annotations
import math

import numpy as np
import pandas as pd

BLOCK = 10000  # 10 km cluster blocks
SEED_F1 = 53053
SEED_PLACEBO = 53054
L_F2 = 0.10
N_BOOT = 2000


def wilson(k: int, n: int, z: float = 1.959964):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def add_blocks(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["block"] = (np.floor(df.x / BLOCK).astype(int).astype(str) + "_" + np.floor(df.y / BLOCK).astype(int).astype(str))
    return df


def _ratio(cs):
    """cs: array (clusters, 4) = [n_c, d_c, n_k, d_k]; ratio of disagreement rates contradicted / consistent."""
    s = cs.sum(axis=0)
    if s[0] == 0 or s[2] == 0 or s[3] == 0:
        return float("nan")
    return (s[1] / s[0]) / (s[3] / s[2])


def f1(df: pd.DataFrame, a: str = "contradicted", b: str = "consistent", n_boot: int = N_BOOT, seed: int = SEED_F1,
       min_a: int = 25, min_b: int = 100) -> dict:
    """df needs columns verdict (str), disagree (bool), block. Ratio = P(dis|a)/P(dis|b) with cluster bootstrap."""
    df = df[df.verdict.isin([a, b])]
    g = df.groupby("block")
    tab = pd.DataFrame({
        "nc": g.apply(lambda d: (d.verdict == a).sum(), include_groups=False),
        "dc": g.apply(lambda d: ((d.verdict == a) & d.disagree).sum(), include_groups=False),
        "nk": g.apply(lambda d: (d.verdict == b).sum(), include_groups=False),
        "dk": g.apply(lambda d: ((d.verdict == b) & d.disagree).sum(), include_groups=False)})
    arr = tab.values.astype(float)
    out = {"n_a": int(arr[:, 0].sum()), "dis_a": int(arr[:, 1].sum()), "n_b": int(arr[:, 2].sum()),
           "dis_b": int(arr[:, 3].sum()), "clusters": int(len(arr))}
    out["rate_a"] = out["dis_a"] / out["n_a"] if out["n_a"] else float("nan")
    out["rate_b"] = out["dis_b"] / out["n_b"] if out["n_b"] else float("nan")
    out["ratio"] = _ratio(arr) if len(arr) else float("nan")
    if len(arr) < 2:
        out.update(lo=float("nan"), hi=float("nan"), evaluable=False, passed=False)
        return out
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(arr), size=(n_boot, len(arr)))
    sums = arr[idx].sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratios = (sums[:, 1] / sums[:, 0]) / (sums[:, 3] / sums[:, 2])
    ratios = ratios[np.isfinite(ratios)]
    out["lo"], out["hi"] = (float(np.percentile(ratios, 2.5)), float(np.percentile(ratios, 97.5))) if len(ratios) else (float("nan"),) * 2
    out["boot_valid"] = int(len(ratios))
    out["evaluable"] = out["n_a"] >= min_a and out["n_b"] >= min_b
    out["passed"] = bool(out["evaluable"] and out["lo"] > 1.0)
    return out


def f2(df: pd.DataFrame, limit: float = L_F2, n_boot: int = N_BOOT, seed: int = SEED_F1) -> dict:
    """Among plots that agree with the map, share called contradicted; Wilson upper bound must be below `limit`."""
    ag = add_blocks(df) if "block" not in df else df
    ag = ag[~ag.disagree]
    n = int(len(ag))
    k = int((ag.verdict == "contradicted").sum())
    lo, hi = wilson(k, n)
    out = {"n_agree": n, "k_contradicted": k, "share": k / n if n else float("nan"), "wilson_lo": lo, "wilson_hi": hi, "limit": limit}
    if n:
        g = ag.groupby("block")
        arr = np.stack([g.size().values, g.apply(lambda d: (d.verdict == "contradicted").sum(), include_groups=False).values], axis=1).astype(float)
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, len(arr), size=(n_boot, len(arr)))
        s = arr[idx].sum(axis=1)
        sh = s[:, 1] / s[:, 0]
        out["boot_lo"], out["boot_hi"] = float(np.percentile(sh, 2.5)), float(np.percentile(sh, 97.5))
    out["passed"] = bool(n > 0 and hi < limit)
    return out


def spatial_placebo(df: pd.DataFrame, verdict_lookup, seed: int = SEED_PLACEBO, min_km: float = 5.0) -> dict:
    """Give every plot the verdict of a random cell of the same tile >= min_km away; recompute the F1 ratio.
    `verdict_lookup(tile, x, y)` -> verdict string at an arbitrary location."""
    rng = np.random.default_rng(seed)
    rows = []
    for tile, d in df.groupby("tile"):
        xs, ys = d.x.values, d.y.values
        x0, x1, y0, y1 = xs.min() - 20000, xs.max() + 20000, ys.min() - 20000, ys.max() + 20000
        for r in d.itertuples():
            for _ in range(50):
                px, py = rng.uniform(x0, x1), rng.uniform(y0, y1)
                if math.hypot(px - r.x, py - r.y) >= min_km * 1000:
                    v = verdict_lookup(tile, px, py)
                    if v is not None:
                        rows.append((r.block, v, r.disagree))
                        break
    pf = pd.DataFrame(rows, columns=["block", "verdict", "disagree"])
    return f1(pf, n_boot=N_BOOT, seed=SEED_PLACEBO, min_a=1, min_b=1)

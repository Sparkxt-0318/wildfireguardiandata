"""Gate statistics: Clopper-Pearson intervals (C1) and paired cluster bootstrap of recall differences (C2)."""
from __future__ import annotations

import math

import pandas as pd

from firewitness.core.placebo import cluster_bootstrap, paired_cluster_bootstrap


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    from scipy.stats import beta
    if n == 0:
        return (float("nan"), float("nan"))
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def cell_year(r) -> tuple:
    return (math.floor(r["LATITUDE"] * 2) / 2, math.floor(r["LONGITUDE"] * 2) / 2, int(r["FIRE_YEAR"]))


def c2_table(lab: pd.DataFrame, n_boot: int = 2000, min_n: int = 30, seed: int = 0) -> pd.DataFrame:
    """Recall of ours (verified or probable) and of the standard label, by size class, with paired bootstrap."""
    rows = []
    recs = lab.to_dict("records")
    groups = [("all", recs)] + [(k, [r for r in recs if r["FIRE_SIZE_CLASS"] == k])
                                for k in sorted(lab.FIRE_SIZE_CLASS.unique())]
    for k, rs in groups:
        n = len(rs)
        if n == 0:
            continue
        ours = sum(r["caught_ours"] for r in rs) / n
        std = sum(r["caught_std"] for r in rs) / n
        ver = sum(r["caught_verified"] for r in rs) / n
        row = {"class": k, "n": n, "recall_ours": ours, "recall_std": std, "recall_verified": ver,
               "diff": ours - std, "lo": None, "hi": None, "excludes_zero": None, "gated": n >= min_n and k != "all"}
        if n >= 5:
            b = paired_cluster_bootstrap(rs, cell_year, lambda s: sum(r["caught_ours"] for r in s) / len(s),
                                         lambda s: sum(r["caught_std"] for r in s) / len(s), n=n_boot, seed=seed)
            row.update(lo=b["lo"], hi=b["hi"], excludes_zero=b["excludes_zero"] and b["lo"] > 0,
                       n_clusters=b["n_clusters"])
            bv = paired_cluster_bootstrap(rs, cell_year, lambda s: sum(r["caught_verified"] for r in s) / len(s),
                                          lambda s: sum(r["caught_std"] for r in s) / len(s), n=n_boot, seed=seed)
            row.update(ver_minus_std=ver - std, ver_lo=bv["lo"], ver_hi=bv["hi"])
        rows.append(row)
    return pd.DataFrame(rows)


def c1_table(lab_p: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, d in [("searched", lab_p[lab_p.searched.astype(bool)]), ("all matched", lab_p[lab_p.LATITUDE.notna()])]:
        n = len(d)
        for t in ("verified", "probable"):
            k = int((d.tier == t).sum())
            lo, hi = clopper_pearson(k, n)
            rows.append({"scope": scope, "tier": t, "k": k, "n": n, "rate": k / n if n else float("nan"),
                         "lo": lo, "hi": hi})
    return pd.DataFrame(rows)

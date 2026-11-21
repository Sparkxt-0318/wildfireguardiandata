"""v0.4 pooling (protocol v0.4 section 2): pool the years of one (source system x table) so that small year groups can be decided.
The v0.2 estimator and its margins are unchanged; only the grouping and the homogeneity condition are new."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import timeoffset as T

MARGIN = T.MIN_GAIN


def _conv_gain(d, ul, uu, conv):
    """Gain of the called convention over the alternative, for one subset of fires."""
    sh = T.hypothesis_shares(np.asarray(d, float), np.asarray(ul, float), np.asarray(uu, float))
    if conv == "H1":
        return sh["H1"] - sh["H0"]
    if conv == "H0":
        return sh["H0"] - sh["H1"]
    return sh[conv] - max(sh["H0"], sh["H1"])


def conv_of(res: dict):
    o = res.get("outcome", "")
    if o == "offset: recorded in UTC":
        return "H1"
    if o.startswith("offset: corrected by"):
        return res.get("convention")
    if o.startswith("no offset found (local"):
        return "H0"
    return None


def pooled_call(parts: dict, homogeneity=True, n_boot=500, seed=0):
    """parts: {year: (d, ul, uu, cluster)}. Returns the pooled estimator result with the homogeneity check applied."""
    years = sorted(parts)
    d, ul, uu, cl = [np.concatenate([parts[y][i] for y in years]) for i in range(4)]
    res = T.estimate_group(d, ul, uu, cl, n_boot=n_boot, seed=seed)
    res["years"] = f"{years[0]}-{years[-1]}"
    res["n_years"] = len(years)
    conv = conv_of(res)
    res["convention_called"] = conv
    if homogeneity and conv is not None and len(years) >= 2:
        halves = [years[0::2], years[1::2]]
        gains = []
        for h in halves:
            dd, a, b = [np.concatenate([parts[y][i] for y in h]) for i in range(3)]
            ok = np.isfinite(dd) & np.isfinite(a) & np.isfinite(b)
            gains.append(float(_conv_gain(dd[ok], a[ok], b[ok], conv)) if ok.sum() >= 10 else float("nan"))
        res["half_year_gains"] = gains
        if not all(g > MARGIN for g in gains):
            res["outcome_before_homogeneity"] = res["outcome"]
            res["outcome"] = "no offset found (not clear: years differ)"
            res["convention_called"] = None
    return res


def build_parts(cache: dict, years=None):
    """cache: {(system, table, year): (d, ul, uu, cluster, rid)} -> {(system, table): {year: (d, ul, uu, cluster)}}, finite fires only."""
    out = {}
    for (s, t, y), (d, ul, uu, cl, _rid) in cache.items():
        if years is not None and y not in years:
            continue
        ok = np.isfinite(d) & np.isfinite(ul) & np.isfinite(uu)
        out.setdefault((s, t), {})[y] = (d[ok], ul[ok], uu[ok], np.asarray(cl)[ok])
    return out


def run_pooling(cache: dict, years=None, homogeneity=True, n_boot=500):
    """Year-group calls (v0.2 rule), pooled calls, and how the pooled call is used."""
    parts = build_parts(cache, years)
    year_rows, pool_rows = [], []
    for (s, t), yp in parts.items():
        pc = pooled_call(yp, homogeneity=homogeneity, n_boot=n_boot)
        conv = pc.get("convention_called")
        decided = left_out = 0
        for y, (d, ul, uu, cl) in sorted(yp.items()):
            r = T.estimate_group(d, ul, uu, cl, n_boot=n_boot)
            row = {"system": s, "table": t, "year": int(y), **{k: r.get(k) for k in ("n", "outcome", "gain_H1_over_H0")}}
            if r["outcome"] == "insufficient fires":
                row["final"] = pc["outcome"] if pc["outcome"] != "insufficient fires" and (conv is not None or pc["outcome"].startswith("no offset found (local")) else "insufficient fires"
                row["decided_by_pool"] = row["final"] != "insufficient fires"
                decided += int(row["decided_by_pool"])
            else:
                row["final"] = r["outcome"]
                row["decided_by_pool"] = False
                if conv is not None and not (_conv_gain(d, ul, uu, conv) > 0):
                    row["contradicts_pool"] = True
                    left_out += 1
            year_rows.append(row)
        pool_rows.append({"system": s, "table": t, **{k: pc.get(k) for k in ("years", "n_years", "n", "outcome", "outcome_before_homogeneity", "convention_called", "gain_H1_over_H0", "gain_H1_ci", "gain_shift_over_best_of_H0_H1", "gain_shift_ci", "half_year_gains", "share_H0", "share_H1", "best_shift")},
                          "year_groups_decided": decided, "year_groups_contradicting": left_out})
    return pd.DataFrame(year_rows), pd.DataFrame(pool_rows)


def leave_one_year_out(cache: dict, years, homogeneity=True, n_boot=200):
    """Dev check of the rule: for each year group with 30 fires or more, the call of the same table pooled over the other years
    against the year's own call. Returns rows (system, table, year, n, own, pooled_others, agree)."""
    parts = build_parts(cache, years)
    rows = []
    for (s, t), yp in parts.items():
        for y, (d, ul, uu, cl) in sorted(yp.items()):
            if len(d) < 30:
                continue
            own = T.estimate_group(d, ul, uu, cl, n_boot=n_boot)
            rest = {k: v for k, v in yp.items() if k != y}
            if not rest or sum(len(v[0]) for v in rest.values()) < 30:
                continue
            pc = pooled_call(rest, homogeneity=homogeneity, n_boot=n_boot)
            co, cp = conv_of(own), pc.get("convention_called")
            rows.append({"system": s, "table": t, "year": int(y), "n": int(len(d)), "own": own["outcome"], "pooled_others": pc["outcome"], "own_conv": co, "pooled_conv": cp,
                         "own_decided": co is not None, "pooled_decided": cp is not None, "agree": (co is not None and co == cp), "opposite": (co is not None and cp is not None and co != cp)})
    return pd.DataFrame(rows)

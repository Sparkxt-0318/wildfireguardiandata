"""Early growth attributes, placebo thresholds and gates (protocol/GROWTH_PROTOCOL.md §4-§7).

Self-contained: needs only numpy, pandas and scipy, and reads only the released compact files, so the same file is
shipped in the release (growth_stats.py) and recomputes every number of results/GROWTH_RESULTS.md.

Inputs (pandas DataFrames, column names as released):
  fires   one row per fire and satellite: fire_id, sat, role, set, split, size_class, acres, t0, t0_kind, T0,
          site_lon, fdc_first, fdc_first_power_mw, perm_id
  series  one row per fire, satellite and frame: fire_id, sat, tau_min, P, P_lo, P_hi, N, fdc_P, fdc_npow
  placebo one row per placebo anchor and frame: fire_id, sat, day, di, dj, kind, tau_min, P, N
P and N are missing (NaN) on frames that are not clear.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

SLOPE_ATTRS = ["slope_1h", "slope_3h", "slope_6h", "logslope_3h", "npix_slope_1h", "npix_slope_3h", "npix_slope_6h"]
TOL = 2.5   # minutes: a frame belongs to [0, W] when its offset from t0 lies in [-2.5 min, W + 2.5 min]


# ---------------------------------------------------------------- robust line fit and the bootstrap over frames
def pair_slopes(t, y):
    t = np.asarray(t, float)
    y = np.asarray(y, float)
    dt = t[None, :] - t[:, None]
    with np.errstate(all="ignore"):
        S = (y[None, :] - y[:, None]) / dt
    S[dt == 0] = np.nan
    return S


def theil_sen(t, y) -> float:
    n = len(t)
    if n < 2:
        return float("nan")
    S = pair_slopes(t, y)
    iu = np.triu_indices(n, 1)
    v = S[iu]
    v = v[np.isfinite(v)]
    return float(np.median(v)) if len(v) else float("nan")


def seed_of(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def block_boot_slopes(t, y, B: int, block: int, seed: int) -> np.ndarray:
    """Moving-block bootstrap over the clear frames (in time order) of the Theil-Sen slope; B values."""
    n = len(t)
    if n < 2:
        return np.full(B, np.nan)
    b = min(block, n)
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(n / b))
    st = rng.integers(0, n - b + 1, size=(B, nb))
    idx = (st[:, :, None] + np.arange(b)[None, None, :]).reshape(B, -1)[:, :n]
    S = pair_slopes(t, y)
    iu0, iu1 = np.triu_indices(n, 1)
    v = S[idx[:, iu0], idx[:, iu1]]
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmedian(v, axis=1)


# ---------------------------------------------------------------- windows and attributes
def window_frames(tau_min, ok, W_h, cfg):
    """Clear frames of [t0, t0 + W] and whether the window is usable (protocol §4: enough frames, both ends)."""
    a = cfg["attributes"]
    tau = np.asarray(tau_min, float)
    inw = (tau >= -TOL) & (tau <= 60 * W_h + TOL)
    sel = inw & np.asarray(ok, bool)
    n = int(sel.sum())
    expected = 12 * W_h + 1
    need = max(a["min_frames"], int(math.ceil(a["min_frames_frac"] * expected)))
    known = n >= need
    if known:
        tc = tau[sel]
        known = bool(tc.min() <= a["edge_frac"] * 60 * W_h + TOL and tc.max() >= (1 - a["edge_frac"]) * 60 * W_h - TOL)
    return sel, n, known


def point_attrs(tau_min, P, N, cfg) -> dict:
    """Attribute values (no interval) for one series: used for placebo anchors and as fire point estimates."""
    a = cfg["attributes"]
    out = {}
    ok = np.isfinite(P)
    th = np.asarray(tau_min, float) / 60.0
    for W in a["windows_h"]:
        sel, n, known = window_frames(tau_min, ok, W, cfg)
        out[f"n_clear_{W}h"] = n
        out[f"slope_{W}h"] = theil_sen(th[sel], P[sel]) if known else float("nan")
        out[f"npix_slope_{W}h"] = theil_sen(th[sel], N[sel]) if known else float("nan")
        if W == a["log_window_h"]:
            out[f"logslope_{W}h"] = theil_sen(th[sel], np.log(P[sel] + a["log_offset_mw"])) if known else float("nan")
    p0 = np.where(ok & (np.asarray(tau_min) >= -TOL) & (np.asarray(tau_min) <= a["p0_max_delay_min"] + TOL))[0]
    out["p0_mw"] = float(P[p0[0]]) if len(p0) else float("nan")
    out["_p0_idx"] = int(p0[0]) if len(p0) else -1
    return out


def fire_attrs(fid, sat, tau_min, P, P_lo, P_hi, N, cfg) -> dict:
    """Point values, bootstrap intervals and clear-frame counts for one fire-satellite series."""
    a, bs = cfg["attributes"], cfg["bootstrap"]
    out = point_attrs(tau_min, P, N, cfg)
    i0 = out.pop("_p0_idx")
    out["p0_lo"] = float(P_lo[i0]) if i0 >= 0 else float("nan")
    out["p0_hi"] = float(P_hi[i0]) if i0 >= 0 else float("nan")
    ok = np.isfinite(P)
    th = np.asarray(tau_min, float) / 60.0
    for W in a["windows_h"]:
        sel, n, known = window_frames(tau_min, ok, W, cfg)
        ys = {f"slope_{W}h": P[sel], f"npix_slope_{W}h": N[sel]}
        if W == a["log_window_h"]:
            ys[f"logslope_{W}h"] = np.log(P[sel] + a["log_offset_mw"])
        for k, y in ys.items():
            if known:
                b = block_boot_slopes(th[sel], y, bs["B"], bs["block"], seed_of(fid, sat, k))
                lo, hi = np.nanpercentile(b, bs["q"])
            else:
                lo = hi = float("nan")
            out[f"{k}_lo"], out[f"{k}_hi"] = float(lo), float(hi)
    g, glo, ghi = out["logslope_3h"], out["logslope_3h_lo"], out["logslope_3h_hi"]
    out["doubling_time_h"] = math.log(2) / g if g > 0 else float("nan")
    out["doubling_time_lo"] = math.log(2) / ghi if ghi > 0 else float("nan")
    out["doubling_time_hi"] = (math.log(2) / glo if glo > 0 else float("inf")) if ghi > 0 else float("nan")
    return out


def local_solar_hour(t0_iso: str, lon: float) -> float:
    t = datetime.fromisoformat(t0_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
    h = t.hour + t.minute / 60 + t.second / 3600 + lon / 15.0
    return round(h % 24, 2)


# ---------------------------------------------------------------- placebo thresholds and states
def placebo_attrs(placebo: pd.DataFrame, cfg) -> pd.DataFrame:
    rows = []
    for key, g in placebo.groupby(["fire_id", "sat", "day", "di", "dj"], sort=True):
        g = g.sort_values("tau_min")
        v = point_attrs(g.tau_min.to_numpy(), g.P.to_numpy(float), g.N.to_numpy(float), cfg)
        v.pop("_p0_idx")
        rows.append(dict(zip(["fire_id", "sat", "day", "di", "dj"], key), kind=g.kind.iloc[0], **v))
    return pd.DataFrame(rows)


def thresholds(pa: pd.DataFrame, cfg) -> dict:
    """Per satellite and attribute: the 99th percentile of |placebo value| (p0: of the placebo P at the anchor),
    from the placebo anchors of Set A and Set B dev fires."""
    q = cfg["placebo"]["quantile"]
    out = {}
    for sat, g in pa.groupby("sat"):
        d = {}
        for k in SLOPE_ATTRS:
            x = np.abs(g[k].to_numpy(float))
            x = x[np.isfinite(x)]
            d[k] = {"thr": float(np.percentile(x, q)) if len(x) else float("nan"), "n": int(len(x))}
        x = g["p0_mw"].to_numpy(float)
        x = x[np.isfinite(x)]
        d["p0_mw"] = {"thr": float(np.percentile(x, q)) if len(x) else float("nan"), "n": int(len(x))}
        out[sat] = d
    return out


def state(value, thr, signed=True) -> str:
    if value is None or not np.isfinite(value):
        return "unknown"
    v = abs(value) if signed else value
    return "measured" if v > thr else "flat"


# ---------------------------------------------------------------- intervals
def wilson(k, n, z=1.96):
    if n == 0:
        return [float("nan")] * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [p, max(0.0, c - w), min(1.0, c + w)]


def auc(score, y) -> float:
    s = np.asarray(score, float)
    y = np.asarray(y, bool)
    pos, neg = s[y], s[~y]
    if not len(pos) or not len(neg):
        return float("nan")
    from scipy.stats import rankdata
    r = rankdata(np.concatenate([pos, neg]))
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def spearman(x, y) -> float:
    from scipy.stats import spearmanr
    if len(x) < 3:
        return float("nan")
    return float(spearmanr(x, y).correlation)


def fire_boot(df: pd.DataFrame, fn, B: int, seed: int, key="fire_id"):
    """Bootstrap by fire: resample fires with replacement (all their rows), return the B values of fn(df)."""
    rng = np.random.default_rng(seed)
    ids = np.array(sorted(df[key].unique()))
    groups = {f: g for f, g in df.groupby(key)}
    out = []
    for _ in range(B):
        pick = rng.choice(ids, size=len(ids), replace=True)
        out.append(fn(pd.concat([groups[f] for f in pick], ignore_index=True)))
    return np.asarray(out, float)


def ci(vals, q=(2.5, 97.5)):
    v = np.asarray(vals, float)
    v = v[np.isfinite(v)]
    return [float(x) for x in np.percentile(v, q)] if len(v) else [float("nan")] * 2


# ---------------------------------------------------------------- the table
def build_table(fires: pd.DataFrame, series: pd.DataFrame, thr: dict, cfg) -> pd.DataFrame:
    rows = []
    sg = {k: g.sort_values("tau_min") for k, g in series.groupby(["fire_id", "sat"])}
    for _, f in fires.sort_values(["fire_id", "sat"]).iterrows():
        g = sg.get((f.fire_id, f.sat))
        row = {c: f[c] for c in ["fire_id", "perm_id", "set", "split", "size_class", "acres", "sat", "role", "t0",
                                  "t0_kind", "T0"]}
        row["local_solar_hour_t0"] = local_solar_hour(f.t0, float(f.site_lon))
        if g is None:
            rows.append(row)
            continue
        v = fire_attrs(f.fire_id, f.sat, g.tau_min.to_numpy(float), g.P.to_numpy(float), g.P_lo.to_numpy(float),
                       g.P_hi.to_numpy(float), g.N.to_numpy(float), cfg)
        t = thr.get(f.sat, {})
        row.update({"p0_mw": v["p0_mw"], "p0_lo": v["p0_lo"], "p0_hi": v["p0_hi"],
                    "p0_state": state(v["p0_mw"], t.get("p0_mw", {}).get("thr", np.nan), signed=False)})
        for k in SLOPE_ATTRS:
            row.update({k: v[k], f"{k}_lo": v[f"{k}_lo"], f"{k}_hi": v[f"{k}_hi"],
                        f"{k}_state": state(v[k], t.get(k, {}).get("thr", np.nan))})
            if k == "logslope_3h":
                row.update({"doubling_time_h": v["doubling_time_h"], "doubling_time_lo": v["doubling_time_lo"],
                            "doubling_time_hi": v["doubling_time_hi"]})
        for W in cfg["attributes"]["windows_h"]:
            row[f"n_clear_{W}h"] = v[f"n_clear_{W}h"]
            row[f"n_expected_{W}h"] = 12 * W + 1
        row["fdc_first"] = f.fdc_first
        row["fdc_first_power_mw"] = f.fdc_first_power_mw
        rows.append(row)
    tab = pd.DataFrame(rows)
    # the satellite used for per-fire numbers: most clear frames in [t0, t0 + 3 h], ties -> east
    tab["selected"] = False
    for fid, g in tab.groupby("fire_id"):
        g = g.assign(_n=g["n_clear_3h"].fillna(-1), _e=(g.role == "east").astype(int))
        i = g.sort_values(["_n", "_e"], ascending=False).index[0]
        tab.loc[i, "selected"] = True
    return tab


# ---------------------------------------------------------------- gates
def g1(pa_sealed: pd.DataFrame, thr: dict, cfg) -> dict:
    out = {}
    for k in SLOPE_ATTRS:
        x = pa_sealed[["sat", k]].dropna()
        called = sum(abs(v) > thr[s][k]["thr"] for s, v in zip(x.sat, x[k]))
        out[k] = {"called_measured": int(called), "n_anchors": int(len(x)), "share": wilson(called, len(x)),
                  "by_sat": {s: [int(sum(abs(v) > thr[s][k]["thr"] for v in gg[k])), int(len(gg))]
                             for s, gg in x.groupby("sat")}}
    ok = all(v["n_anchors"] > 0 and v["share"][0] <= cfg["gates"]["G1_max_share"] for v in out.values())
    return {"by_attribute": out, "n_sealed_anchors": int(len(pa_sealed)), "pass": bool(ok)}


def g2(fires_s: pd.DataFrame, series: pd.DataFrame, cfg) -> dict:
    G = cfg["gates"]
    rows = []
    for (fid, sat), g in series[series.fire_id.isin(fires_s.fire_id)].groupby(["fire_id", "sat"]):
        tau = g.tau_min.to_numpy(float)
        sel = (tau >= -TOL) & (tau <= 180 + TOL) & np.isfinite(g.P.to_numpy(float)) & (g.fdc_npow.to_numpy() > 0)
        if sel.sum() < G["G2_min_common_frames"]:
            continue
        th = tau[sel] / 60
        rows.append({"fire_id": fid, "sat": sat, "n_common": int(sel.sum()),
                     "ours": theil_sen(th, g.P.to_numpy(float)[sel]), "fdc": theil_sen(th, g.fdc_P.to_numpy(float)[sel])})
    d = pd.DataFrame(rows, columns=["fire_id", "sat", "n_common", "ours", "fdc"])
    rho = spearman(d.ours, d.fdc) if len(d) else float("nan")
    b = fire_boot(d, lambda x: spearman(x.ours, x.fdc), G["boot_B"], G["boot_seed"]) if len(d) >= 3 else []
    enough = len(d) >= G["G2_min_n"]
    return {"n_fire_satellites": int(len(d)), "n_fires": int(d.fire_id.nunique()), "spearman": rho, "ci": ci(b),
            "median_common_frames": float(d.n_common.median()) if len(d) else float("nan"),
            "pass": (bool(rho >= G["G2_min_spearman"]) if enough else None),
            "verdict": ("PASS" if rho >= G["G2_min_spearman"] else "FAIL") if enough else "not enough data",
            "_rows": d}


def g3(tab_s: pd.DataFrame, cfg) -> dict:
    G = cfg["gates"]
    k = "slope_3h"
    two = tab_s[tab_s[f"{k}_state"] != "unknown"].groupby("fire_id").filter(lambda g: len(g) == 2)
    piv = two.pivot(index="fire_id", columns="role", values=k).dropna()
    st = two.pivot(index="fire_id", columns="role", values=f"{k}_state").reindex(piv.index)
    rho = spearman(piv.east, piv.west) if len(piv) else float("nan")
    dd = piv.reset_index()
    b = fire_boot(dd, lambda x: spearman(x.east, x.west), G["boot_B"], G["boot_seed"]) if len(dd) >= 3 else []
    both = st[(st.east == "measured") & (st.west == "measured")].index
    agree = int((np.sign(piv.loc[both, "east"]) == np.sign(piv.loc[both, "west"])).sum())
    sh = wilson(agree, len(both))
    enough = len(piv) >= G["G3_min_n"]
    ok = enough and rho >= G["G3_min_spearman"] and len(both) > 0 and sh[0] >= G["G3_min_sign_share"]
    return {"n_fires_both_known": int(len(piv)), "spearman": rho, "ci": ci(b), "n_fires_both_measured": int(len(both)),
            "sign_agree": agree, "sign_share": sh, "pass": bool(ok) if enough else None,
            "verdict": ("PASS" if ok else "FAIL") if enough else "not enough data"}


def first_operational_power(fires: pd.DataFrame) -> pd.Series:
    """Per fire: the fire product's power at its first detection on either satellite (none -> 0 MW)."""
    out = {}
    for fid, g in fires.groupby("fire_id"):
        g = g[g.fdc_first.notna() & (g.fdc_first.astype(str) != "")]
        if not len(g):
            out[fid] = 0.0
            continue
        r = g.sort_values(["fdc_first", "role"]).iloc[0]
        p = r.fdc_first_power_mw
        out[fid] = float(p) if p is not None and np.isfinite(float(p)) else 0.0
    return pd.Series(out)


def g4(tab_s: pd.DataFrame, fires_s: pd.DataFrame, cfg) -> dict:
    G = cfg["gates"]
    sel = tab_s[tab_s.selected].copy()
    sel["large"] = sel.size_class.isin(G["G4_large_classes"])
    sel["fdc_first_power_any"] = sel.fire_id.map(first_operational_power(fires_s))
    d = sel[np.isfinite(sel.slope_3h.astype(float)) & np.isfinite(sel.p0_mw.astype(float))][
        ["fire_id", "large", "slope_3h", "p0_mw", "fdc_first_power_any"]].reset_index(drop=True)

    def stats(x):
        a = auc(x.slope_3h, x.large)
        b = auc(x.p0_mw, x.large)
        c = auc(x.fdc_first_power_any, x.large)
        return [a, b, c, a - b, a - c]
    pt = stats(d) if len(d) else [float("nan")] * 5
    rng = np.random.default_rng(G["boot_seed"])
    bs = []
    for _ in range(G["boot_B"]):
        x = d.iloc[rng.integers(0, len(d), len(d))]
        bs.append(stats(x))
    bs = np.asarray(bs, float) if bs else np.full((1, 5), np.nan)
    names = ["auc_growth_3h", "auc_power_t0", "auc_fdc_first_power", "diff_vs_power_t0", "diff_vs_fdc_first_power"]
    res = {n: {"value": float(v), "ci": ci(bs[:, i])} for i, (n, v) in enumerate(zip(names, pt))}
    res.update({"n_fires": int(len(d)), "n_large": int(d.large.sum()), "n_small": int((~d.large).sum()),
                "n_sealed_fires": int(fires_s.fire_id.nunique()),
                "better_than_power_t0": bool(res["diff_vs_power_t0"]["ci"][0] > 0),
                "better_than_fdc_first_power": bool(res["diff_vs_fdc_first_power"]["ci"][0] > 0)})
    return res


def headline_counts(tab: pd.DataFrame, fires: pd.DataFrame) -> dict:
    out = {}
    for name, m in (("A", fires.set == "A"), ("dev", fires.split == "dev"), ("sealed", fires.split == "sealed")):
        ids = set(fires[m].fire_id)
        t = tab[tab.fire_id.isin(ids) & tab.selected]
        k = int((t.slope_3h_state == "measured").sum())
        out[name] = {"fires_tried": len(ids), "fires_with_series": int(len(t)), "measured_3h": k,
                     "share_3h": wilson(k, len(ids)),
                     "flat_3h": int((t.slope_3h_state == "flat").sum()),
                     "unknown_3h": int(len(ids) - k - (t.slope_3h_state == "flat").sum())}
        for W in (1, 6):
            out[name][f"measured_{W}h"] = int((t[f"slope_{W}h_state"] == "measured").sum())
    return out


def curves(tab_s: pd.DataFrame, series: pd.DataFrame, cfg, step=5, max_min=360) -> pd.DataFrame:
    """Figure data: for sealed selected fire-satellites, P at each 5-min offset; median and quartiles by group."""
    G = cfg["gates"]
    sel = tab_s[tab_s.selected]
    grid = np.arange(0, max_min + step, step)
    rows = []
    for _, f in sel.iterrows():
        g = series[(series.fire_id == f.fire_id) & (series.sat == f.sat)]
        tau, P = g.tau_min.to_numpy(float), g.P.to_numpy(float)
        for x in grid:
            j = np.where(np.abs(tau - x) <= TOL)[0]
            v = P[j[0]] if len(j) else np.nan
            rows.append({"fire_id": f.fire_id, "group": "large" if f.size_class in G["G4_large_classes"] else "small",
                         "tau_min": int(x), "P": v})
    d = pd.DataFrame(rows)
    out = d.dropna().groupby(["group", "tau_min"]).P.agg(
        median="median", q25=lambda s: s.quantile(0.25), q75=lambda s: s.quantile(0.75), n="count").reset_index()
    nf = d.dropna().groupby("group").fire_id.nunique()
    out["n_fires"] = out.group.map(nf)
    return out

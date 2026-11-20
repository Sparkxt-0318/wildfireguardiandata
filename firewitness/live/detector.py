"""Part B detector: per-pixel two-witness CUSUM, fitted on dev placebo series and dev fires (protocol §6).

Statistic. Per satellite, S = CUSUM of the site score u (k, cap). For a site seen by both satellites
    G = max( S_E, S_W, [S_E >= m and S_W >= m] * (S_E + S_W) / rho )
(rho > 1 lets two weaker witnesses alert together below the single-satellite threshold); single satellite: G = S.
Alert when G >= h. One alert per evidence episode: the site is not alerted again until G returns to 0
(protocol amendment 3). h is set from placebo series so that alerts per pixel-site-day equal the budget.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from . import signal as sg
from .extract import BOX, HALF, NDAYS, load_series
from .traceback import DERIVED, FirmsClean, series_meta

UDIR = DERIVED / "u"


@dataclass(frozen=True)
class Config:
    ukey: str = "dT"          # feature: dT | dTd | bt7, optional suffix _c<n> (compactness filter)
    cap: float = 8.0
    k: float = 0.5
    rho: float = 1.5          # inf = no two-witness rule
    m: float = 1.0
    vis_weight: float = 0.0
    decay: float = 1.0        # S multiplier on a frame with no value

    def to_json(self):
        d = asdict(self)
        d["rho"] = None if math.isinf(self.rho) else self.rho
        return d

    @staticmethod
    def from_json(d):
        d = dict(d)
        if d.get("rho") is None:
            d["rho"] = math.inf
        return Config(**d)


# ---------------------------------------------------------------- u arrays per fire, cached
def parse_ukey(ukey):
    parts = ukey.split("_")
    feat = parts[0]
    compact = None
    for p in parts[1:]:
        if p.startswith("c"):
            compact = int(p[1:])
    return feat, compact


def compute_u(series: dict, ukey: str) -> np.ndarray:
    feat, compact = parse_ukey(ukey)
    if feat == "vis":
        from .replay import vis_u
        return vis_u(series)
    base = "dT" if feat == "dTd" else feat
    f = sg.feature(series, base)
    r = sg.residual(f)
    if feat == "dTd":
        from .replay import sameday_ref
        r = r - sameday_ref(r)
    z = sg.scene_filter(sg.zscore_all(r, NDAYS))
    if compact is not None:
        z = sg.compact_filter(z, compact)
    return sg.site_u(z, cap=99.0)


def nearest_map(sR, sO):
    la, lo = sR["lat"], sR["lon"]
    lb, lob = sO["lat"].ravel(), sO["lon"].ravel()
    d = (la[..., None] - lb) ** 2 + ((lo[..., None] - lob) * np.cos(np.radians(la[..., None]))) ** 2
    return np.unravel_index(np.argmin(d, -1), sO["lat"].shape)


def fire_dir(fid):
    return UDIR / fid


def ensure_base(fid: str, firms: FirmsClean) -> dict | None:
    """Static per-fire arrays: availability, scan times, clean-site mask, mapping, info."""
    d = fire_dir(fid)
    f = d / "base.npz"
    if f.is_file():
        z = np.load(f, allow_pickle=True)
        out = {k: z[k] for k in z.files}
        out["info"] = json.loads(str(out["info"]))
        return out
    meta = series_meta(fid)
    if meta is None:
        return None
    from .replay import clean_sites, op_time
    sats = meta["sats"]
    east = [s for s, v in sats.items() if v["role"] == "east"]
    west = [s for s, v in sats.items() if v["role"] == "west"]
    ref = east[0] if east else west[0]
    other = west[0] if (east and west) else None
    sR = load_series(fid, ref)
    sO = load_series(fid, other) if other else None
    out = {"availE": sR["tavail"], "tscanE": sR["tscan"], "clean": clean_sites_recent(sR, sO, meta, firms),
           "lat": sR["lat"], "lon": sR["lon"]}
    if sO is not None:
        ii, jj = nearest_map(sR, sO)
        out["mapW_i"], out["mapW_j"] = ii.astype(np.int16), jj.astype(np.int16)
        out["availW"] = sO["tavail"]
    info = {"fid": fid, "ref": ref, "other": other, "T0": meta["T0"], "op": op_time(meta),
            "op_E": sats[ref]["fdc_first"][1] if sats[ref]["fdc_first"] else None,
            "op_W": sats[other]["fdc_first"][1] if other and sats[other]["fdc_first"] else None,
            "discovery_t": meta["discovery_t"], "polar_first_t": meta["polar_first_t"]}
    out["info"] = np.array(json.dumps(info))
    d.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(f, **out)
    out["info"] = info
    return out


def clean_sites_recent(sR, sO, meta, firms):
    """Placebo-eligible pixel-sites (protocol §5) with the recent-fire mask: no FIRMS detection within 5 km in the
    9 days before the window (a live rule: such sites are not evaluated)."""
    from .replay import clean_sites
    from .firelist import haversine_km
    ok = clean_sites(sR, sO, meta, firms)
    for d in range(NDAYS):
        ts = sR["tscan"][d]
        if not np.isfinite(ts).any():
            continue
        t0 = np.nanmin(ts)
        near = firms.idx.near(meta["lat"], meta["lon"], 70.0, t0 - 9 * 86400, t0)
        for n in near:
            dk = haversine_km(firms.idx.d["lat"][n], firms.idx.d["lon"][n], sR["lat"], sR["lon"])
            ok[d] &= dk > 5.0
    return ok


def ensure_u(fid: str, ukey: str, base: dict) -> tuple[np.ndarray, np.ndarray | None]:
    d = fire_dir(fid)
    fe, fw = d / f"uE_{ukey}.npy", d / f"uW_{ukey}.npy"
    info = base["info"]
    if fe.is_file() and (info["other"] is None or fw.is_file() or ukey.startswith("vis")):
        uE = np.load(fe)
        uW = np.load(fw) if fw.is_file() else None
        return uE, uW
    sR = load_series(fid, info["ref"])
    uE = compute_u(sR, ukey).astype(np.float16)
    np.save(fe, uE)
    uW = None
    if info["other"] and not ukey.startswith("vis"):
        sO = load_series(fid, info["other"])
        uo = compute_u(sO, ukey)
        uW = uo[:, :, base["mapW_i"], base["mapW_j"]].astype(np.float16)
        np.save(fw, uW)
    return uE, uW


# ---------------------------------------------------------------- statistic
def g_series(uE, uW, cfg: Config, vE=None):
    """G over time for sites: uE, uW [T, N] (uW None = single). Returns G [T, N] (float32)."""
    T, N = uE.shape
    SE = np.zeros(N, np.float32)
    SW = np.zeros(N, np.float32)
    G = np.zeros((T, N), np.float32)
    for t in range(T):
        x = np.minimum(uE[t].astype(np.float32), cfg.cap)
        if vE is not None and cfg.vis_weight:
            v = vE[t].astype(np.float32)
            x = np.where(np.isfinite(x) & np.isfinite(v), x + cfg.vis_weight * np.maximum(v, 0), x)
        fx = np.isfinite(x)
        SE = np.where(fx, np.maximum(0, SE + np.where(fx, x, 0) - cfg.k), SE * cfg.decay)
        if uW is None:
            G[t] = SE
            continue
        y = np.minimum(uW[t].astype(np.float32), cfg.cap)
        fy = np.isfinite(y)
        SW = np.where(fy, np.maximum(0, SW + np.where(fy, y, 0) - cfg.k), SW * cfg.decay)
        g = np.maximum(SE, SW)
        if not math.isinf(cfg.rho):
            both = (SE >= cfg.m) & (SW >= cfg.m)
            g = np.maximum(g, np.where(both, (SE + SW) / cfg.rho, 0))
        G[t] = g
    return G


def run_maxima(G):
    """Maxima of the runs (episodes) of G > 0 for each site; G [T, N]. Returns a flat array."""
    T, N = G.shape
    cur = np.zeros(N, np.float32)
    out = []
    for t in range(T):
        g = G[t]
        end = (g <= 0) & (cur > 0)
        if end.any():
            out.append(cur[end].copy())
        cur = np.where(g > 0, np.maximum(cur, g), 0)
    if (cur > 0).any():
        out.append(cur[cur > 0])
    return np.concatenate(out) if out else np.zeros(0, np.float32)


def fire_eval(fid: str, cfg: Config, firms: FirmsClean, need_placebo=True, post_h=2.0):
    """Per fire: placebo run maxima and site-days; the fire site's running max of G with alert times."""
    base = ensure_base(fid, firms)
    if base is None:
        return None
    uE, uW = ensure_u(fid, cfg.ukey, base)
    vE = None
    if cfg.vis_weight:
        vE, _ = ensure_u(fid, "vis", base)
    info = base["info"]
    aE = base["availE"]
    aW = base.get("availW")
    out = {"fid": fid, "info": info}
    # fire site: 9 site centres around the site pixel, day 0
    cen = [(HALF + i, HALF + j) for i in (-1, 0, 1) for j in (-1, 0, 1)]
    ci = np.array([c[0] for c in cen])
    cj = np.array([c[1] for c in cen])
    G = g_series(uE[0][:, ci, cj], uW[0][:, ci, cj] if uW is not None else None, cfg,
                 vE[0][:, ci, cj] if vE is not None else None)
    g = G.max(1)
    tav = aE[0].copy()
    if aW is not None:
        tav = np.fmax(tav, aW[0])
    end = info["T0"] + post_h * 3600
    ok = np.isfinite(tav) & (tav <= end)
    g = np.where(ok, g, 0)
    out["fire_runmax"] = np.maximum.accumulate(g)
    out["fire_tav"] = tav
    out["fire_G"] = g
    if need_placebo:
        rm, sd = [], 0.0
        for d in range(NDAYS):
            idx = np.argwhere(base["clean"][d])
            if not len(idx):
                continue
            Gp = g_series(uE[d][:, idx[:, 0], idx[:, 1]], uW[d][:, idx[:, 0], idx[:, 1]] if uW is not None else None,
                          cfg, vE[d][:, idx[:, 0], idx[:, 1]] if vE is not None else None)
            rm.append(run_maxima(Gp))
            sd += len(idx) * np.isfinite(base["tscanE"][d]).sum() * 300 / 86400
        out["placebo_runmax"] = np.concatenate(rm) if rm else np.zeros(0, np.float32)
        out["site_days"] = sd
    return out


def threshold_for_budget(evals, budget):
    """Smallest h with (episodes with max >= h) / site-days <= budget, pooled over evals."""
    rm = np.sort(np.concatenate([e["placebo_runmax"] for e in evals]))[::-1]
    sd = sum(e["site_days"] for e in evals)
    nmax = int(math.floor(budget * sd))
    if nmax >= len(rm):
        return 0.0, sd
    return float(rm[nmax]) + 1e-3, sd


def false_rate(evals, h):
    n = sum(int((e["placebo_runmax"] >= h).sum()) for e in evals)
    sd = sum(e["site_days"] for e in evals)
    return n / sd if sd else float("nan"), n, sd


def alert_time(e, h):
    i = np.where(e["fire_runmax"] >= h)[0]
    return float(e["fire_tav"][i[0]]) if len(i) else None


def lead(e, h):
    a = alert_time(e, h)
    o = e["info"]["op"]
    if a is None and o is None:
        return None
    if a is None:
        return -math.inf
    if o is None:
        return math.inf
    return (o - a) / 60.0


def clipped_mean(leads, lo=-120.0, hi=240.0):
    v = [min(max(x, lo), hi) for x in leads if x is not None]
    return float(np.mean(v)) if v else float("nan")


# ---------------------------------------------------------------- clustered placebo events (amendment 3)
def episodes(G, floor=1.0):
    """Episodes (runs of G > 0) with max >= floor. G [T, N]. Returns arrays site, start, end, gmax."""
    T, N = G.shape
    cur = np.zeros(N, np.float32)
    st = np.full(N, -1)
    out_s, out_a, out_b, out_m = [], [], [], []
    for t in range(T + 1):
        g = G[t] if t < T else np.zeros(N, np.float32)
        end = (g <= 0) & (cur > 0)
        if end.any():
            idx = np.where(end & (cur >= floor))[0]
            out_s.append(idx)
            out_a.append(st[idx])
            out_b.append(np.full(len(idx), t - 1))
            out_m.append(cur[idx])
        start = (g > 0) & (cur <= 0)
        st = np.where(start, t, st)
        cur = np.where(g > 0, np.maximum(cur, g), 0)
    cat = lambda x, dt: np.concatenate(x).astype(dt) if x else np.zeros(0, dt)
    return cat(out_s, np.int32), cat(out_a, np.int16), cat(out_b, np.int16), cat(out_m, np.float32)


def count_clusters(ep_sites_rc, ep_start, ep_end, ep_max, h):
    """Number of clusters among episodes with max >= h: episodes are linked when their sites are 8-adjacent and
    their [start, end] intervals overlap."""
    sel = np.where(ep_max >= h)[0]
    if len(sel) <= 1:
        return len(sel)
    rc = ep_sites_rc[sel]
    a, b = ep_start[sel], ep_end[sel]
    parent = list(range(len(sel)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    order = np.argsort(a)
    for ii in range(len(sel)):
        for jj in range(ii + 1, len(sel)):
            if abs(int(rc[ii, 0]) - int(rc[jj, 0])) <= 1 and abs(int(rc[ii, 1]) - int(rc[jj, 1])) <= 1 \
                    and a[ii] <= b[jj] and a[jj] <= b[ii]:
                ri, rj = find(ii), find(jj)
                if ri != rj:
                    parent[ri] = rj
    return len({find(i) for i in range(len(sel))})


def placebo_episodes(fid, cfg, firms, base=None, floor=None):
    """Clean-site episodes of one fire's placebo series per day, as a list of (rc, start, end, max) per day,
    plus site-days."""
    base = base or ensure_base(fid, firms)
    uE, uW = ensure_u(fid, cfg.ukey, base)
    vE = ensure_u(fid, "vis", base)[0] if cfg.vis_weight else None
    floor = cfg.cap if floor is None else floor
    days, sd = [], 0.0
    for d in range(NDAYS):
        idx = np.argwhere(base["clean"][d])
        if not len(idx):
            continue
        Gp = g_series(uE[d][:, idx[:, 0], idx[:, 1]], uW[d][:, idx[:, 0], idx[:, 1]] if uW is not None else None,
                      cfg, vE[d][:, idx[:, 0], idx[:, 1]] if vE is not None else None)
        s, a, b, m = episodes(Gp, floor)
        days.append((idx[s].astype(np.int16), a, b, m))
        sd += len(idx) * np.isfinite(base["tscanE"][d]).sum() * 300 / 86400
    return days, sd

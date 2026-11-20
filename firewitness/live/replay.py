"""Part B: the live detector (two-witness CUSUM) and its strictly causal replay (protocol §6).

Sites live on the reference grid: GOES-East's box when the fire is seen by both satellites, else the single
satellite's box. The West stream of a site is the West pixel nearest to the East pixel centre.
Frames are combined slot by slot (5-min CONUS cadence); an alert's time is the availability time of the latest
frame it used.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np

from . import signal as sg
from .extract import BOX, HALF, NDAYS, NSLOT, SERIES_DIR, load_series
from .traceback import DERIVED, FirmsClean, anchor_slot, series_meta

REPLAY_DIR = DERIVED / "replay"
EXCL_PX = 10          # day-0 placebo sites must be >= 10 px (20 km) from the fire site


@dataclass
class Detector:
    feat: str = "dT"
    k: float = 0.5
    cap: float = 8.0
    h1: float = 20.0
    h2: float = 12.0
    m: float = 1.0
    cloud_decay: float = 1.0      # factor applied to S on a frame with no value (1 = hold)
    vis_weight: float = 0.0       # weight of the visible score added in daytime (candidate)

    def to_json(self):
        return asdict(self)


def feature_u(series: dict, feat: str) -> np.ndarray:
    """u for all pixel-sites and days for one satellite and one feature."""
    if feat in ("dT", "bt7"):
        f = sg.feature(series, feat)
        r = sg.residual(f)
    elif feat == "dTd":
        f = sg.feature(series, "dT")
        r = sg.residual(f)
        r = r - sameday_ref(r)
    else:
        raise ValueError(feat)
    z = sg.scene_filter(sg.zscore_all(r, NDAYS))
    return sg.site_u(z, cap=99.0)


def sameday_ref(r, lo=36, hi=12):
    """Median of r over slots [t-lo, t-hi) on the same day (causal); needs >= 6 values."""
    import warnings
    out = np.full_like(r, np.nan)
    T = r.shape[1]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for t in range(T):
            a, b = max(0, t - lo), max(0, t - hi)
            if b - a < 6:
                continue
            w = r[:, a:b]
            c = np.isfinite(w).sum(1)
            m = np.nanmedian(w, 1)
            m[c < 6] = np.nan
            out[:, t] = m
    return out


def vis_u(series: dict) -> np.ndarray:
    """Visible (band 1, 1 km) smoke score aggregated to the 2 km grid: max over the 2x2 1-km pixels' z."""
    ref = series["REF1"]
    # cloud: no ACM at 1 km; use the 2 km ACM (with buffer) upsampled
    ref = sg.bt14_spatial_ref(series["BT14"], series["ACM"])
    clear2 = sg.clear_from_cloud(sg.effective_cloud(series["ACM"], series["BT14"], ref))
    clear1 = np.repeat(np.repeat(clear2, 2, -2), 2, -1)[..., :BOX, :BOX]
    # the 1 km box covers only the central 20x20 2-km pixels
    f = np.where(clear1, ref, np.nan)
    r = sg.residual(f)
    z = sg.scene_filter(sg.zscore_all(r, NDAYS))
    u1 = sg.site_u(z, cap=99.0)
    out = np.full(series["BT7"].shape, np.nan, np.float32)
    D, T = out.shape[:2]
    blk = u1.reshape(D, T, BOX // 2, 2, BOX // 2, 2)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        m = np.nanmax(np.nanmax(blk, 5), 3)
    out[:, :, HALF - BOX // 4:HALF + BOX // 4, HALF - BOX // 4:HALF + BOX // 4] = m
    return out


def prepare(fid: str, feats=("dT",), firms: FirmsClean | None = None, force=False) -> Path | None:
    """Build the replay arrays of one fire: u per feature on the reference grid (East, and West mapped), avail
    times, clean-site masks, the fire site, the operational time."""
    meta = series_meta(fid)
    if meta is None:
        return None
    REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    out = REPLAY_DIR / f"{fid}.npz"
    have = {}
    if out.is_file() and not force:
        z = np.load(out, allow_pickle=True)
        have = {k: z[k] for k in z.files}
        if all(f"uE_{f}" in have for f in feats):
            return out
    sats = meta["sats"]
    east = [s for s, v in sats.items() if v["role"] == "east"]
    west = [s for s, v in sats.items() if v["role"] == "west"]
    ref = east[0] if east else west[0]
    other = west[0] if (east and west) else None
    sR = load_series(fid, ref)
    sO = load_series(fid, other) if other else None
    res = dict(have)
    for f in feats:
        if f"uE_{f}" in res:
            continue
        if f == "vis":
            res[f"uE_{f}"] = vis_u(sR).astype(np.float16)
            if sO is not None:
                res[f"uW_{f}"] = None
            continue
        res[f"uE_{f}"] = feature_u(sR, f).astype(np.float16)
        if sO is not None:
            uo = feature_u(sO, f)
            res[f"uW_{f}"] = uo[:, :, res_map(sR, sO)[0], res_map(sR, sO)[1]].astype(np.float16)
    if "clean" not in res:
        if firms is None:
            firms = FirmsClean()
        res["clean"] = clean_sites(sR, sO, meta, firms)
        res["availE"] = sR["tavail"]
        res["tscanE"] = sR["tscan"]
        if sO is not None:
            res["availW"] = sO["tavail"]
            ii, jj = res_map(sR, sO)
            fd = sO["FDC"]
            res["fdcW_site"] = fd[0][:, ii, jj][:, HALF, HALF]
        res["info"] = np.array(json.dumps({"fid": fid, "ref": ref, "other": other, "T0": meta["T0"],
                                           "op": op_time(meta), "discovery_t": meta["discovery_t"],
                                           "polar_first_t": meta["polar_first_t"]}))
    res = {k: v for k, v in res.items() if v is not None}
    np.savez_compressed(out, **res)
    return out


def res_map(sR, sO):
    """For each pixel of the reference box, the indices of the nearest pixel of the other satellite's box."""
    la, lo = sR["lat"], sR["lon"]
    lb, lob = sO["lat"].ravel(), sO["lon"].ravel()
    d = (la[..., None] - lb) ** 2 + ((lo[..., None] - lob) * np.cos(np.radians(la[..., None]))) ** 2
    k = np.argmin(d, -1)
    return np.unravel_index(k, sO["lat"].shape)


def op_time(meta) -> float | None:
    """Availability time of the first operational fire-product detection (either satellite), or None."""
    av = [v["fdc_first"][1] for v in meta["sats"].values() if v["fdc_first"]]
    return min(av) if av else None


def clean_sites(sR, sO, meta, firms: FirmsClean) -> np.ndarray:
    """[D, H, W] bool: the pixel-site may serve as a placebo series on that day (protocol §5)."""
    from scipy.ndimage import maximum_filter
    D = NDAYS
    ok = np.zeros((D, BOX, BOX), bool)
    for d in range(D):
        fd = sR["FDC"][d]
        hot = (((fd >= 10) & (fd <= 15)) | ((fd >= 30) & (fd <= 35))).any(0)
        if sO is not None:
            ii, jj = res_map(sR, sO)
            fo = sO["FDC"][d]
            hot |= (((fo >= 10) & (fo <= 15)) | ((fo >= 30) & (fo <= 35))).any(0)[ii, jj]
        hot5 = maximum_filter(hot, size=5, mode="constant")
        ok[d] = ~hot5
        ts = sR["tscan"][d]
        if not np.isfinite(ts).any():
            ok[d] = False
            continue
        t0, t1 = np.nanmin(ts), np.nanmax(ts)
        near = firms.idx.near(meta["lat"], meta["lon"], 60.0, t0 - 86400, t1 + 86400)
        if len(near):
            from .firelist import haversine_km
            for n in near:
                dk = haversine_km(firms.idx.d["lat"][n], firms.idx.d["lon"][n], sR["lat"], sR["lon"])
                ok[d] &= dk > 5.0
    yy, xx = np.mgrid[0:BOX, 0:BOX]
    ok[0] &= np.maximum(abs(yy - HALF), abs(xx - HALF)) >= EXCL_PX
    edge = 5   # annulus (4) + site (1)
    ok[:, :edge] = ok[:, -edge:] = False
    ok[:, :, :edge] = ok[:, :, -edge:] = False
    return ok


# ---------------------------------------------------------------- detector core
def run_detector(uE, uW, availE, availW, det: Detector, vE=None):
    """Run the two-witness CUSUM over slots. uE/uW: [T, N] (uW may be None). Returns alerts as a list per site of
    (slot, alert_time). Vectorised over sites N."""
    T, N = uE.shape
    SE = np.zeros(N, np.float32)
    SW = np.zeros(N, np.float32)
    first = np.full(N, np.nan)
    count = np.zeros(N, np.int32)
    first_slot = np.full(N, -1)
    for t in range(T):
        x = np.minimum(uE[t].astype(np.float32), det.cap)
        if vE is not None and det.vis_weight:
            v = vE[t].astype(np.float32)
            x = np.where(np.isfinite(v) & np.isfinite(x), x + det.vis_weight * np.maximum(v, 0), x)
        fin = np.isfinite(x)
        SE = np.where(fin, np.maximum(0, SE + np.where(fin, x, 0) - det.k), SE * det.cloud_decay)
        tE = availE[t] if np.isfinite(availE[t]) else np.nan
        tt = np.full(N, tE)
        if uW is not None:
            y = np.minimum(uW[t].astype(np.float32), det.cap)
            fy = np.isfinite(y)
            SW = np.where(fy, np.maximum(0, SW + np.where(fy, y, 0) - det.k), SW * det.cloud_decay)
            tW = availW[t] if availW is not None and np.isfinite(availW[t]) else np.nan
            a1 = (SE >= det.h1) | (SW >= det.h1)
            a2 = (SE >= det.m) & (SW >= det.m) & (SE + SW >= det.h2)
            a = a1 | a2
            tt = np.where(a2 & ~(SE >= det.h1), np.fmax(tE, tW), np.where(SE >= det.h1, tE, tW))
        else:
            a = SE >= det.h1
        if a.any():
            newf = a & (count == 0)
            first = np.where(newf, tt, first)
            first_slot = np.where(newf, t, first_slot)
            count += a
            SE = np.where(a, 0, SE)
            SW = np.where(a, 0, SW)
    return count, first, first_slot


def load_prepared(fid: str):
    z = np.load(REPLAY_DIR / f"{fid}.npz", allow_pickle=True)
    d = {k: z[k] for k in z.files}
    d["info"] = json.loads(str(d["info"]))
    return d


def fire_replay(P: dict, det: Detector, post_h: float = 2.0):
    """Replay at the fire site on day 0 (window start to T0 + 2 h)."""
    f = det.feat
    uE = P[f"uE_{f}"][0, :, HALF, HALF][:, None]
    uW = P[f"uW_{f}"][0, :, HALF, HALF][:, None] if f"uW_{f}" in P else None
    vE = P["uE_vis"][0, :, HALF, HALF][:, None] if (det.vis_weight and "uE_vis" in P) else None
    aE = P["availE"][0]
    aW = P["availW"][0] if "availW" in P else None
    # the CUSUM uses the 3x3 site centred on the fire site: alert if any of the 3x3 site centres alerts
    cnt, first, slot = run_detector(_nb(P[f"uE_{f}"][0]), _nb(P[f"uW_{f}"][0]) if uW is not None else None, aE, aW, det,
                                    _nb(P["uE_vis"][0]) if vE is not None else None)
    info = P["info"]
    end = info["T0"] + post_h * 3600
    ft = first[np.isfinite(first)]
    ft = ft[ft <= end]
    alert = float(ft.min()) if len(ft) else None
    return {"alert": alert, "op": info["op"], "T0": info["T0"], "discovery_t": info["discovery_t"],
            "polar_first_t": info["polar_first_t"]}


def _nb(u):
    """[T, H, W] -> [T, 9] series of the 3x3 site centres around the fire site (the site may be off by a pixel)."""
    return np.stack([u[:, HALF + i, HALF + j] for i in (-1, 0, 1) for j in (-1, 0, 1)], 1)


def placebo_alerts(P: dict, det: Detector):
    """False alerts on clean placebo pixel-sites. Returns (n_alerts, site_days)."""
    f = det.feat
    clean = P["clean"]
    tot, sd = 0, 0.0
    for d in range(NDAYS):
        idx = np.argwhere(clean[d])
        if not len(idx):
            continue
        uE = P[f"uE_{f}"][d][:, idx[:, 0], idx[:, 1]]
        uW = P[f"uW_{f}"][d][:, idx[:, 0], idx[:, 1]] if f"uW_{f}" in P else None
        vE = P["uE_vis"][d][:, idx[:, 0], idx[:, 1]] if (det.vis_weight and "uE_vis" in P) else None
        aE = P["availE"][d]
        aW = P["availW"][d] if "availW" in P else None
        cnt, _, _ = run_detector(uE, uW, aE, aW, det, vE)
        tot += int(cnt.sum())
        nsl = np.isfinite(P["tscanE"][d]).sum()
        sd += len(idx) * nsl * 300 / 86400
    return tot, sd


def lead_minutes(r, clip=(-120, 240)):
    """op - alert in minutes, with the protocol's conventions; None = excluded."""
    a, o = r["alert"], r["op"]
    if a is None and o is None:
        return None
    if a is None:
        return -math.inf
    if o is None:
        return math.inf
    return (o - a) / 60.0


def score(leads, clip=(-120, 240)):
    v = [min(max(x, clip[0]), clip[1]) for x in leads if x is not None]
    return float(np.mean(v)) if v else float("nan")

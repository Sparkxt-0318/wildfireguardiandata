"""Trace-back v0.2 (protocol/LIVE_PROTOCOL_v0.2.md): smoke witness in the visible band and fire size at onset.

The thermal onset is the frozen v0.1 variant A2. This module adds (1) a plume score from ABI band 1 (0.47 um, 1 km)
against each pixel's own history, judged in a window around the thermal onset, with a placebo-calibrated threshold
p*, and (2) FRP and burning area at a given frame from the 3.9 um radiance excess over the v0.1 background model.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy.ndimage import label

from . import signal as sg
from .extract import HALF, NDAYS, load_series, solar_zenith
from .firelist import haversine_km

SIGMA = 5.670374419e-8
CFG_FILE = Path(__file__).parent / "config" / "traceback_v02_us.json"
PLANCK = {  # band 7 Planck constants of the L1b files (read 2026-11-21 from one file per satellite)
    "G16": (202263.0, 3698.18994140625, 0.4336099922657013, 0.9993900060653687),
    "G17": (203135.0, 3703.5, 0.44554001092910767, 0.9993799924850464),
    "G18": (200441.0, 3687.050048828125, 0.44868001341819763, 0.9993699789047241),
    "G19": (202263.0, 3698.18994140625, 0.4336099922657013, 0.9993900060653687),
}
FIRE_CODES = (10, 11, 12, 13, 14, 30, 31, 32, 33, 34)


# ---------------------------------------------------------------- band-7 radiance and the T^4 coefficient
def planck_L(T, sat):
    fk1, fk2, bc1, bc2 = PLANCK[sat]
    with np.errstate(all="ignore"):
        return fk1 / (np.exp(fk2 / (bc1 + bc2 * np.asarray(T, float))) - 1.0)


def band7_a(sat, t_lo=650.0, t_hi=1350.0):
    T = np.linspace(t_lo, t_hi, 141)
    L = planck_L(T, sat)
    return float(np.sum(L * T ** 4) / np.sum(T ** 8))


def pixel_area_m2(lat, lon):
    """Ground area of each pixel of a box from the distances to its neighbours (km -> m^2)."""
    dx = np.full(lat.shape, np.nan)
    dy = np.full(lat.shape, np.nan)
    dx[:, :-1] = haversine_km(lat[:, :-1], lon[:, :-1], lat[:, 1:], lon[:, 1:])
    dx[:, -1] = dx[:, -2]
    dy[:-1] = haversine_km(lat[:-1], lon[:-1], lat[1:], lon[1:])
    dy[-1] = dy[-2]
    return dx * dy * 1e6


# ---------------------------------------------------------------- FRP at a frame
def bt7_background(series):
    """BT7 background (protocol v0.2 §4): annulus median at the frame + median over the 7 background days (+-5 min)
    of (BT7 - annulus median). Also the robust scale of that difference (K, v0.1 floor 0.5 K); the radiance
    uncertainty s_L is this scale times dL/dT at the background temperature (first-order conversion)."""
    f = sg.feature(series, "bt7")
    r = sg.residual(f)
    ann = series["BT7"] - r                  # clear annulus median at the same frame (NaN where the pixel is masked)
    med, sc = sg.history_stats(r, sg.bg_days(0, NDAYS))    # day 0 only: [T, H, W]
    return ann[0] + med, sc


def frp_at(series, sat, k, ci=HALF, cj=HALF, bg=None, area=None):
    """FRP (MW) of the 3x3 pixels around (ci, cj) at day-0 frame k, with a 95 % interval, T_bg (K) and area."""
    if bg is None:
        bg = bt7_background(series)
    bt_bg, sc = bg
    if area is None:
        area = pixel_area_m2(series["lat"].astype(float), series["lon"].astype(float))
    a = band7_a(sat)
    sl = (slice(ci - 1, ci + 2), slice(cj - 1, cj + 2))
    T = series["BT7"][0, k][sl].astype(float)
    Tb = bt_bg[k][sl].astype(float)
    s = sc[k][sl].astype(float)
    A = area[sl]
    ok = np.isfinite(T) & np.isfinite(Tb) & np.isfinite(s) & np.isfinite(A)
    if not ok.any():
        return None
    L = planck_L(T, sat)
    Lb = planck_L(Tb, sat)
    dLdT = planck_L(Tb + 0.5, sat) - planck_L(Tb - 0.5, sat)
    ex = np.where(ok, np.maximum(L - Lb, 0.0), 0.0)
    frp = float(np.sum(A * SIGMA * ex / a)) / 1e6
    sd = float(np.sqrt(np.sum(np.where(ok, (A * SIGMA * dLdT * s / a) ** 2, 0.0)))) / 1e6
    lo = max(0.0, frp - 1.96 * sd - 0.10 * frp)
    hi = frp + 1.96 * sd + 0.10 * frp
    tbg = float(np.nanmedian(np.where(ok, Tb, np.nan)))
    return {"frp_mw": frp, "frp_lo": lo, "frp_hi": hi, "t_bg": tbg, "n_pix": int(ok.sum()),
            "area_m2": frp * 1e6 / (SIGMA * (800.0 ** 4 - tbg ** 4)),
            "area_lo_m2": lo * 1e6 / (SIGMA * (1200.0 ** 4 - tbg ** 4)),
            "area_hi_m2": hi * 1e6 / (SIGMA * (600.0 ** 4 - tbg ** 4))}


def fdc_frp(meta_sat: dict, scan_t: float, cfg: dict):
    """Operational FRP (MW): FDCC Power summed over the fire-coded pixels of the 5x5 window at the site at the
    product frame with scan start scan_t. Returns (frp or None, n fire pixels)."""
    from . import goes
    fr = goes.frames(meta_sat["bucket"], cfg["products"]["FDC"]["prefix"], None, goes.utc(scan_t - 60),
                     goes.utc(scan_t + 60))
    fr = [f for f in fr if abs(f["t"] - scan_t) < 30]
    if not fr:
        return None, 0
    r = goes.read_job({"url": goes.url_of(fr[0]), "kind": "fdcp",
                       "boxes": [(meta_sat["r"] - 2, meta_sat["c"] - 2, 5, 5)]})
    if not r["ok"]:
        return None, 0
    m, p = r["boxes"][0]
    sel = np.isin(m.astype(int), FIRE_CODES)
    ok = sel & np.isfinite(p)
    if not ok.any():
        return None, int(sel.sum())
    return float(p[ok].sum()), int(sel.sum())


# ---------------------------------------------------------------- smoke witness
def plume_series(series, lat, lon, cfg=None, z_bright=3.0, radius_px=3):
    """Plume score P[day, slot] (bright pixels in components within radius_px of the site) and a daytime flag."""
    ref = series["REF1"].astype(np.float32)
    D, T = ref.shape[:2]
    ref_ = sg.bt14_spatial_ref(series["BT14"], series["ACM"])
    cloud2 = sg.effective_cloud(series["ACM"], series["BT14"], ref_)
    q = HALF // 2   # the 1 km box covers 2 km box indices HALF-10 .. HALF+9
    c1 = np.repeat(np.repeat(cloud2[:, :, HALF - q:HALF + q, HALF - q:HALF + q], 2, 2), 2, 3)
    rho = np.where(c1, np.nan, ref)
    z = np.full_like(rho, np.nan)
    for d in range(D):
        med, _ = sg.history_stats(rho, sg.bg_days(d, D))
        samples = []
        for dd in sg.bg_days(d, D):
            for dk in (-1, 0, 1):
                x = np.full_like(rho[dd], np.nan)
                if dk >= 0:
                    x[:T - dk] = rho[dd, dk:]
                else:
                    x[-dk:] = rho[dd, :T + dk]
                samples.append(x)
        st = np.stack(samples)
        mad, _ = sg.nanmedian0(np.abs(st - med))
        s = np.maximum(0.005, 1.4826 * mad)
        z[d] = (rho[d] - med) / s
    yy, xx = np.mgrid[0:z.shape[2], 0:z.shape[3]]
    near = (yy - HALF) ** 2 + (xx - HALF) ** 2 <= radius_px ** 2
    P = np.zeros((D, T), np.int32)
    for d in range(D):
        for k in range(T):
            b = np.isfinite(z[d, k]) & (z[d, k] >= z_bright)
            if not b[near].any():
                continue
            lab, n = label(b, structure=np.ones((3, 3)))
            ids = np.unique(lab[near & b])
            ids = ids[ids > 0]
            P[d, k] = int(np.isin(lab, ids).sum())
    day = np.zeros((D, T), bool)
    ts = series["tscan"]
    for d in range(D):
        for k in range(T):
            if np.isfinite(ts[d, k]):
                day[d, k] = solar_zenith(lat, lon, float(ts[d, k])) < 80
    return P, day


def plume_present(P, day, p):
    """[D, T] bool: plume present at a daytime frame with P >= p there and at the previous daytime frame."""
    D, T = P.shape
    out = np.zeros((D, T), bool)
    for d in range(D):
        prev = False
        for k in range(T):
            if not day[d, k]:
                continue
            cur = bool(P[d, k] >= p)
            out[d, k] = cur and prev
            prev = cur
    return out


def window_slots(tscan_day, t_center, before_min=60, after_min=15):
    ts = tscan_day
    return np.where(np.isfinite(ts) & (ts >= t_center - before_min * 60) & (ts <= t_center + after_min * 60))[0]


def placebo_windows(P, day, tscan, T0, p, min_day_frames=6):
    """Temporal placebo windows (days 1..8) at the clock time T0 - 30 min: list of (judged, present)."""
    out = []
    for d in range(1, P.shape[0]):
        tc = T0 - 1800 - d * 86400
        k = window_slots(tscan[d], tc)
        if (day[d, k]).sum() < min_day_frames:
            continue
        pres = plume_present(P[d:d + 1], day[d:d + 1], p)[0]
        out.append(bool(pres[k].any()))
    return out


def support(P, day, tscan, t_D, p, min_day_frames=6):
    """Is a thermal onset at t_D (day 0) supported by a plume? None if W has < min_day_frames daytime frames."""
    k = window_slots(tscan[0], t_D)
    nday = int(day[0, k].sum())
    if nday < min_day_frames:
        return None
    pres = plume_present(P[0:1], day[0:1], p)[0]
    hit = k[pres[k]]
    res = {"supported": bool(len(hit)), "n_day_frames": nday, "P_max_in_W": int(P[0, k].max())}
    if len(hit):
        # first frame of the plume run (consecutive daytime frames with plume present) that reaches W
        dk = np.where(day[0])[0]
        pos = int(np.searchsorted(dk, hit[0]))
        while pos - 1 >= 0 and pres[dk[pos - 1]]:
            pos -= 1
        j = int(dk[pos])
        res["t_plume"] = float(tscan[0, j])
        res["plume_lead_min"] = (t_D - float(tscan[0, j])) / 60.0
    return res


# ---------------------------------------------------------------- runners
from .traceback import DERIVED  # noqa: E402
DERIVED_V02 = DERIVED / "v02"


def plume_record(fid: str, sat: str, force=False):
    """P, daytime flag and scan times for one fire-satellite (cached under derived/v02/plume)."""
    from .goes import atomic_savez
    from .traceback import series_meta
    f = DERIVED_V02 / "plume" / f"{fid}_{sat}.npz"
    if f.is_file() and not force:
        try:
            z = np.load(f)
            return {k: z[k] for k in z.files}
        except Exception:  # noqa: BLE001
            f.unlink(missing_ok=True)
    meta = series_meta(fid)
    s = load_series(fid, sat)
    P, day = plume_series(s, meta["lat"], meta["lon"])
    f.parent.mkdir(parents=True, exist_ok=True)
    rec = {"P": P, "day": day, "tscan": s["tscan"], "T0": np.array(meta["T0"])}
    atomic_savez(f, **rec)
    return rec


def _plume_job(args):
    try:
        plume_record(*args)
        return args, None
    except Exception as e:  # noqa: BLE001
        return args, repr(e)


def plume_records(pairs, procs=3):
    from multiprocessing import get_context
    with get_context("fork").Pool(procs) as pool:
        return [r for r in pool.imap_unordered(_plume_job, pairs) if r[1]]


def placebo_share_curve(recs, p_max=400):
    """Pooled share of temporal placebo windows with a plume present, for p = 1 .. p_max."""
    out = []
    for p in range(1, p_max + 1):
        w = [x for r in recs for x in placebo_windows(r["P"], r["day"], r["tscan"], float(r["T0"]), p)]
        out.append((p, sum(w), len(w)))
        if len(w) and sum(w) == 0:
            break
    return out


def choose_p_star(curve, max_share=0.02):
    for p, k, n in curve:
        if n and k / n <= max_share:
            return p, k, n
    return None


# ---------------------------------------------------------------- frozen settings and the one test run
def freeze(p_star: dict, h_A: dict, code_commit: str, dev_summary: dict) -> dict:
    cfg = {"protocol": "protocol/LIVE_PROTOCOL_v0.2.md", "frozen_utc": None, "code_commit": code_commit,
           "thermal": {"variant": "A2", "h_A": h_A, "k": 0.5},
           "smoke": {"band": 1, "z_bright": 3.0, "radius_km": 3, "scale_floor": 0.005, "sza_max_deg": 80,
                     "window_min": [-60, 15], "min_day_frames": 6, "placebo_clock_offset_min": -30,
                     "p_star": p_star["p"], "p_star_dev_windows": [p_star["k"], p_star["n"]], "max_dev_share": 0.02},
           "size": {"a_band7": {s: band7_a(s) for s in ("G16", "G17", "G18")}, "a_fit_K": [650, 1350],
                    "Tf_K": [600, 800, 1200], "approx_pct": 10, "site": "3x3"},
           "dev_summary": dev_summary}
    import time as _t
    cfg["frozen_utc"] = _t.strftime("%Y-%m-%dT%H:%MZ", _t.gmtime())
    CFG_FILE.write_text(json.dumps(cfg, indent=1) + "\n")
    return cfg


def load_frozen() -> dict:
    return json.loads(CFG_FILE.read_text())


def _iso(t):
    import time as _t
    return None if t is None else _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime(float(t)))


def size_rows(recs, rows_by_key, cfg_region):
    """FRP and area at each onset frame, and at each satellite's first operational detection (S1)."""
    from .traceback import series_meta
    onset, calib = [], []
    for r in recs:
        fid, sat = r["fire_id"], r["sat"]
        row = rows_by_key[(fid, sat)]
        s = load_series(fid, sat)
        bg = bt7_background(s)
        area = pixel_area_m2(s["lat"].astype(float), s["lon"].astype(float))
        ts = s["tscan"][0]
        tD = row["_t"]["t_D"]
        if tD is not None:
            k = int(np.nanargmin(np.abs(ts - tD)))
            e = frp_at(s, sat, k, bg=bg, area=area)
            onset.append({"fire_id": fid, "sat": sat, "t_D": _iso(tD), **({kk: (round(v, 3) if isinstance(v, float) else v)
                                                                            for kk, v in e.items()} if e else {"frp_mw": None})})
        sm = series_meta(fid)["sats"][sat]
        if sm["fdc_first"]:
            tf = float(sm["fdc_first"][0])
            d = np.abs(ts - tf)
            c = {"fire_id": fid, "sat": sat, "fdc_first": _iso(tf)}
            if np.isfinite(d).any() and np.nanmin(d) < 60:
                e = frp_at(s, sat, int(np.nanargmin(d)), bg=bg, area=area)
                c["our_frp_mw"] = None if e is None else round(e["frp_mw"], 3)
                c["our_frp_lo"] = None if e is None else round(e["frp_lo"], 3)
                c["our_frp_hi"] = None if e is None else round(e["frp_hi"], 3)
            else:
                c["our_frp_mw"] = None
                c["note"] = "first detection outside the extracted day-0 window"
            fp, npx = fdc_frp(sm, tf, cfg_region)
            c["fdc_frp_mw"] = None if fp is None else round(fp, 3)
            c["fdc_fire_pixels"] = npx
            calib.append(c)
    return onset, calib


def s1_stats(calib, nboot=2000, seed=0):
    from scipy.stats import spearmanr
    ok = [c for c in calib if c.get("our_frp_mw") is not None and c.get("fdc_frp_mw") and c["fdc_frp_mw"] > 0]
    n = len(ok)
    if n < 20:
        return {"n": n, "verdict": "not enough data", "pass": None}
    ratio = np.array([c["our_frp_mw"] / c["fdc_frp_mw"] for c in ok])
    fids = np.array([c["fire_id"] for c in ok])
    uf = np.unique(fids)
    rng = np.random.default_rng(seed)
    meds = []
    for _ in range(nboot):
        pick = rng.choice(uf, size=len(uf), replace=True)
        x = np.concatenate([ratio[fids == f] for f in pick])
        meds.append(np.median(x))
    lo, hi = np.percentile(meds, [2.5, 97.5])
    rho = float(spearmanr([c["our_frp_mw"] for c in ok], [c["fdc_frp_mw"] for c in ok]).correlation)
    med = float(np.median(ratio))
    ps = bool(0.5 <= med <= 2 and lo >= 1 / 3 and hi <= 3 and rho >= 0.5)
    return {"n": n, "n_fires": int(len(uf)), "median_ratio": med, "ci": [float(lo), float(hi)], "spearman": rho,
            "pass": ps, "verdict": "PASS" if ps else "FAIL"}


def run_test(out=Path("results/live/v02"), procs=3):
    """The v0.2 test, once (protocol v0.2 §5). Needs the frozen config committed."""
    from multiprocessing import get_context
    from firewitness.core import load_region
    from . import pipeline as pl, traceback as tb
    from .extract import load_fires
    fz = load_frozen()
    out.mkdir(parents=True, exist_ok=True)
    fires = load_fires("protocol/live_fires_v02_test.csv")
    byid = {f["fire_id"]: f for f in fires}
    fids = [f["fire_id"] for f in fires]
    done, errs = pl.process_fires(fids, procs=procs, variant="A2")
    recs = tb.load_records(done, variant="A2")
    thr = {role: {"h": float(fz["thermal"]["h_A"][role])} for role in ("east", "west")}
    rows = pl.traceback_table(recs, thr)
    labels = pl.fire_labels(rows, byid)
    # E1 / E2 (v0.1 rules, h_A frozen from the 240 v0.1 fires)
    e1 = {}
    for role in ("east", "west"):
        h = thr[role]["h"]
        plc = [p["S_pre"] for r in recs if r["role"] == role for p in r["placebo"]]
        kf = sum(1 for v in plc if v >= h)
        fr = [tb.finalize(r, h)["onset"] for r in recs if r["role"] == role]
        fp, on = pl.wilson(kf, len(plc)), pl.wilson(sum(fr), len(fr))
        e1[role] = {"h_A": h, "placebo_false_onset": [kf, len(plc), *fp], "fire_onset": [sum(fr), len(fr), *on],
                    "pass": bool(len(plc) and fp[2] <= 0.02 and on[1] > fp[2])}
    e2 = pl.e2_stats(labels)
    # smoke witness
    pairs = [(r["fire_id"], r["sat"]) for r in recs]
    perr = plume_records(pairs, procs=procs)
    p = int(fz["smoke"]["p_star"])
    prec = {(f, s): plume_record(f, s) for f, s in pairs if (f, s) not in {e[0] for e in perr}}
    win = [x for pr in prec.values() for x in placebo_windows(pr["P"], pr["day"], pr["tscan"], float(pr["T0"]), p)]
    v1p = pl.wilson(sum(win), len(win))
    v1 = {"placebo_windows": [sum(win), len(win), *v1p], "pass": bool(len(win) and v1p[2] <= 0.05)}
    rows_by_key = {(r["fire_id"], r["sat"]): r for r in rows}
    sup_sat = []
    for (f, s), pr in prec.items():
        rr = rows_by_key[(f, s)]
        tD = rr["_t"]["t_D"]
        if tD is None:
            continue
        su = support(pr["P"], pr["day"], pr["tscan"], tD, p)
        sup_sat.append({"fire_id": f, "sat": s, "t_D": _iso(tD), "daytime": su is not None,
                        **({} if su is None else {k: (_iso(v) if k == "t_plume" else v) for k, v in su.items()})})
    ss = {(x["fire_id"], x["sat"]): x for x in sup_sat}
    sup_fire = []
    for lab in labels:
        if not lab.get("onset_sat"):
            continue
        x = ss.get((lab["fire_id"], lab["onset_sat"]))
        if x and x["daytime"]:
            sup_fire.append({"fire_id": lab["fire_id"], "onset_sat": lab["onset_sat"], "onset_utc": lab["onset_utc"],
                             "supported": x["supported"], "plume_lead_min": x.get("plume_lead_min"),
                             "t_plume": x.get("t_plume")})
    ks = sum(x["supported"] for x in sup_fire)
    v2p = pl.wilson(ks, len(sup_fire))
    leads = [x["plume_lead_min"] for x in sup_fire if x["supported"]]
    v2 = {"n_daytime_onsets": len(sup_fire), "n_supported": ks, "share": v2p,
          "n_plume_first": sum(1 for v in leads if v >= 0),
          "plume_lead_min_median_ci": pl.boot_median(leads) if leads else None,
          "pass": bool(len(sup_fire) and v2p[1] > v1p[2])}
    # size
    onset_size, calib = size_rows(recs, rows_by_key, load_region(Path(__file__).parent, "us"))
    s1 = s1_stats(calib)
    # write
    pl.write_csv(out / "traceback_v02_test_by_satellite.csv", rows)
    pl.write_csv(out / "onset_labels_v02_test.csv", labels)
    pl.write_csv(out / "smoke_support_by_satellite.csv", sup_sat)
    pl.write_csv(out / "smoke_support_by_fire.csv", sup_fire)
    pl.write_csv(out / "size_at_onset.csv", onset_size)
    pl.write_csv(out / "size_calibration_fdc.csv", calib)
    on_frp = [x["frp_mw"] for x in onset_size if x.get("frp_mw") is not None]
    summ = {"protocol": fz["protocol"], "config_code_commit": fz["code_commit"], "n_fires": len(fids),
            "n_fires_processed": len(done), "n_fire_satellites": len(recs), "errors": errs, "plume_errors": perr,
            "E1": e1, "E2": e2, "V1": v1, "V2": v2, "S1": s1,
            "n_fires_with_onset": sum(1 for l in labels if l.get("onset_sat")),
            "size_at_onset": {"n": len(on_frp), "frp_median_ci": pl.boot_median(on_frp) if on_frp else None,
                              "frp_q25_q75": [float(np.percentile(on_frp, 25)), float(np.percentile(on_frp, 75))] if on_frp else None},
            "made": _iso(__import__("time").time())}
    (out / "v02_test_summary.json").write_text(json.dumps(summ, indent=1, default=str) + "\n")
    return summ

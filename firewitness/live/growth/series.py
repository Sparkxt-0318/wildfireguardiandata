"""Fire-power series (protocol/GROWTH_PROTOCOL.md §3): the frozen v0.2 estimate (MIR radiance method over the frozen
BT7 background) applied frame by frame to the fire's pixels, and the same computation at placebo anchors.

Per frame, region = 7 x 7 pixels around the anchor pixel, core = its central 3 x 3.
  per pixel: excess radiance (L - L_bg)+, z = (BT7 - BT7_bg) / s (s = robust scale of the background, frozen),
  fire pixel = valid and z >= 4 and excess > 0.
  P = sum over the core (every valid pixel, unmasked: the frozen v0.2 S1 estimate) + sum over the ring pixels that
      are fire pixels; interval as v0.2 (+-1.96 sd of the background term, +-10 % for the T^4 approximation).
  N = number of fire pixels in the 7 x 7 region (core included, same rule).
  A frame is clear when all 9 core pixels and at least 30 of the 40 ring pixels are valid; otherwise P and N are
  missing (never zero, never filled).
"""
from __future__ import annotations

import numpy as np

from .. import signal as sg
from ..traceback_v02 import SIGMA, pixel_area_m2
from .common import CFG
from .extract import NDAYS, NSLOT, HALF

S = CFG["series"]
RH = S["region_px"] // 2
CH = S["core_px"] // 2


def planck(sat):
    c = CFG["planck_band7"][sat]
    if c is None:
        raise ValueError(f"no band-7 Planck constants for {sat}")
    return c


def planck_L(T, sat):
    fk1, fk2, bc1, bc2 = planck(sat)
    with np.errstate(all="ignore"):
        return fk1 / (np.exp(fk2 / (bc1 + bc2 * np.asarray(T, float))) - 1.0)


def band7_a(sat, t_lo=650.0, t_hi=1350.0):
    T = np.linspace(t_lo, t_hi, 141)
    L = planck_L(T, sat)
    return float(np.sum(L * T ** 4) / np.sum(T ** 8))


def backgrounds(series):
    """BT7 background for every day (frozen v0.2 §4 generalised from day 0 to day d: annulus median at the frame +
    median over day d's seven background days at +-5 min of (BT7 - annulus median)) and its robust scale."""
    f = sg.feature(series, "bt7")
    r = sg.residual(f)
    ann = series["BT7"] - r
    bg = np.full(r.shape, np.nan, np.float32)
    sc = np.full(r.shape, np.nan, np.float32)
    for d in range(r.shape[0]):
        med, s = sg.history_stats(r, sg.bg_days(d, r.shape[0]))
        bg[d] = ann[d] + med
        sc[d] = s
    return bg, sc


def frame_stats(series, bg, sc, area, sat, d, i, j, slots):
    """P, P_lo, P_hi, N, clear for day d, anchor pixel (i, j), slot indices `slots`."""
    a = band7_a(sat)
    win = (d, slots, slice(i - RH, i + RH + 1), slice(j - RH, j + RH + 1))
    T = series["BT7"][win].astype(float)
    Tb = bg[win].astype(float)
    s = sc[win].astype(float)
    A = area[i - RH:i + RH + 1, j - RH:j + RH + 1][None]
    ok = np.isfinite(T) & np.isfinite(Tb) & np.isfinite(s) & np.isfinite(A)
    L = planck_L(T, sat)
    Lb = planck_L(Tb, sat)
    dLdT = planck_L(Tb + 0.5, sat) - planck_L(Tb - 0.5, sat)
    with np.errstate(invalid="ignore"):
        ex = np.where(ok, np.maximum(L - Lb, 0.0), 0.0)
        z = np.where(ok, (T - Tb) / s, -np.inf)
    frp = A * SIGMA * ex / a / 1e6
    sd = np.where(ok, A * SIGMA * dLdT * s / a / 1e6, 0.0)
    n = 2 * RH + 1
    core = np.zeros((n, n), bool)
    core[RH - CH:RH + CH + 1, RH - CH:RH + CH + 1] = True
    firepix = ok & (z >= S["fire_pixel_z"]) & (ex > 0)
    inc = (ok & core[None]) | (firepix & ~core[None])
    P = (frp * inc).sum((1, 2))
    sdP = np.sqrt(((sd * inc) ** 2).sum((1, 2)))
    lo = np.maximum(0.0, P - 1.96 * sdP - 0.10 * P)
    hi = P + 1.96 * sdP + 0.10 * P
    N = firepix.sum((1, 2)).astype(float)
    clear = ok[:, core].all(1) & (ok[:, ~core].sum(1) >= S["min_ring_valid"])
    for x in (P, lo, hi, N):
        x[~clear] = np.nan
    return P, lo, hi, N, clear


def slot_times(tscan_day, ws_day):
    """Scan start per slot; nominal time (window start + 5 min * k) where the frame is missing."""
    nominal = ws_day + 300.0 * np.arange(len(tscan_day))
    return np.where(np.isfinite(tscan_day), tscan_day, nominal), np.isfinite(tscan_day)


def fire_series(series, meta, sat, t0, bg, sc, area):
    """Fire series at the site, day 0, frames from t0 - 2 h to t0 + 6 h, with the fire product's power."""
    ws = meta["T0"] - 12 * 3600
    t, have = slot_times(series["tscan"][0], ws)
    tau = (t - t0) / 60.0
    sel = np.where((tau >= -S["keep_before_t0_h"] * 60 - 2.5) & (tau <= S["keep_after_t0_h"] * 60 + 2.5))[0]
    P, lo, hi, N, clear = frame_stats(series, bg, sc, area, sat, 0, HALF, HALF, sel)
    pw = series["FDC_POW0"][sel]
    mk = series["FDC"][0, sel, HALF - RH:HALF + RH + 1, HALF - RH:HALF + RH + 1]
    fire = np.isin(mk, S["fire_codes"])
    fdc_ok = (mk >= 0).any((1, 2)) & have[sel]
    fdc_n = np.where(fdc_ok, fire.sum((1, 2)), -1)
    with np.errstate(invalid="ignore"):
        fpw = np.where(fire & np.isfinite(pw), pw, 0.0).sum((1, 2))
        fpn = (fire & np.isfinite(pw)).sum((1, 2))
    fdc_P = np.where(fdc_ok & (fpn > 0), fpw, np.where(fdc_ok, 0.0, np.nan))
    return {"slot": sel, "t_scan": t[sel], "have_frame": have[sel], "tau_min": tau[sel], "P": P, "P_lo": lo, "P_hi": hi,
            "N": N, "clear": clear, "fdc_n": fdc_n, "fdc_P": fdc_P, "fdc_npow": np.where(fdc_ok, fpn, -1)}


def placebo_anchors(series, meta, sat, t0, firms_idx):
    """Clean placebo anchors (protocol §5): (day, di, dj, kind). Temporal: the site on days 1..8. Spatial: the 8
    offsets on days 0..8. Clean = no fire-product code 10-15/30-35 in the anchor's 7 x 7 region at any frame of that
    day's window, and no polar detection within 10 km in [window start - 24 h, window end + 24 h]."""
    P = CFG["placebo"]
    out = []
    ws = meta["T0"] - 12 * 3600
    for d in range(NDAYS):
        offs = [tuple(o) for o in P["spatial_offsets_px"]] + ([(0, 0)] if d in P["temporal_days"] else [])
        a, b = ws - d * 86400, ws - d * 86400 + NSLOT * 300
        for di, dj in offs:
            i, j = HALF + di, HALF + dj
            w = series["FDC"][d, :, i - RH:i + RH + 1, j - RH:j + RH + 1]
            if np.isin(w, P["fdc_unclean_codes"]).any():
                continue
            lat, lon = float(series["lat"][i, j]), float(series["lon"][i, j])
            pad = P["firms_clean_pad_h"] * 3600
            if len(firms_idx.near(lat, lon, P["firms_clean_km"], a - pad, b + pad)):
                continue
            out.append((d, di, dj, "temporal" if (di, dj) == (0, 0) else "spatial"))
    return out


def placebo_series(series, meta, sat, t0, bg, sc, area, anchors):
    """For each anchor: P and N over the frames of [t0_d, t0_d + 6 h] on day d (t0_d = t0 - d days)."""
    ws = meta["T0"] - 12 * 3600
    out = []
    for d, di, dj, kind in anchors:
        t, have = slot_times(series["tscan"][d], ws - d * 86400)
        tau = (t - (t0 - d * 86400)) / 60.0
        sel = np.where((tau >= -2.5) & (tau <= S["keep_after_t0_h"] * 60 + 2.5))[0]
        P, lo, hi, N, clear = frame_stats(series, bg, sc, area, sat, d, HALF + di, HALF + dj, sel)
        out.append({"day": d, "di": di, "dj": dj, "kind": kind, "slot": sel, "tau_min": tau[sel], "P": P, "N": N,
                    "clear": clear})
    return out


def compute(series, meta, sat, t0, firms_idx):
    bg, sc = backgrounds(series)
    area = pixel_area_m2(series["lat"].astype(float), series["lon"].astype(float))
    fs = fire_series(series, meta, sat, t0, bg, sc, area)
    anchors = placebo_anchors(series, meta, sat, t0, firms_idx)
    ps = placebo_series(series, meta, sat, t0, bg, sc, area, anchors)
    return fs, ps

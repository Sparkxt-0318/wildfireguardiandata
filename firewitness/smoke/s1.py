"""S1: known truth. Composite plumes of known opacity over real smoke-free frames. Testing only, never for fitting.
Credit: HPWREN, http://hpwren.ucsd.edu/ (background frames)."""
from __future__ import annotations
import hashlib
import numpy as np
import cv2
from . import core, pipeline, seq
from .core import H, W, BAN
from .params import get as get_params

START = 28                      # plume first present at this pre-window frame index
PRE_END = 26                    # background frames: 0..PRE_END
ENDMEMBERS = {"grey030": (0.30, 0.30, 0.30), "grey055": (0.55, 0.55, 0.55), "grey085": (0.85, 0.85, 0.85),
              "warm": (0.55, 0.45, 0.35)}
AMAX = (0.3, 0.6, 0.9)


def _frozen_horizon(Bs):
    """Plume placement must not depend on the method under test: a frozen copy of the continuous-seam horizon
    (physically, smoke starts on terrain). It only decides where the planted source goes (8-50 px below it)."""
    return pipeline.horizon_line(Bs)


def rng_for(name, k):
    h = hashlib.sha256(f"s1|{name}|{k}".encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))


def make_plume(rng, B, horizon, amax, nframes):
    """alpha_true (nframes,H,W); source on terrain just below the horizon line. Returns alpha, source xy."""
    sx = int(rng.integers(int(0.2 * W), int(0.8 * W)))
    sy = int(np.clip(horizon[sx] + rng.integers(8, 50), BAN + 40, H - BAN - 5))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # smooth multiplicative texture (fixed per plume)
    tex = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 6)
    tex = 1.0 + 0.35 * tex / (tex.std() + 1e-6)
    wind = float(rng.uniform(-3, 3)); rise = float(rng.uniform(3, 6)); g = float(rng.uniform(3.5, 6.0))
    alpha = np.zeros((nframes, H, W), np.float32)
    puffs = [(float(rng.normal(0, 1)), float(rng.normal(0, 1))) for _ in range(8)]
    for k in range(nframes):
        a = np.zeros((H, W), np.float32)
        r0 = 7.0 + g * k
        for j, (px, py) in enumerate(puffs):
            age = max(k - 0.8 * j, 0) if j < k + 1 else None
            if age is None:
                continue
            cx = sx + wind * age * 2 + px * r0 * 0.4
            cy = sy - rise * age * 2 - 0.2 * r0 + py * r0 * 0.3
            rr = 5.0 + g * age
            w = (0.9 ** j)
            a = np.maximum(a, w * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * rr * rr))))
        a = np.clip(a * tex, 0, 1) * amax
        a[:BAN] = 0; a[H - BAN:] = 0
        alpha[k] = a
    return alpha, (sx, sy)


def make_case(sq, k, amax, endm, T=36):
    fr = sq["frames"][:T].astype(np.float32) / 255.0
    pre = list(range(0, PRE_END + 1))
    B = core.build_background(fr, np.array(pre))
    hor = _frozen_horizon(core.smooth(B, 2))
    rng = rng_for(sq["name"], k)
    nf = T - START
    a_true, src = make_plume(rng, B, hor, amax, nf)
    S = np.array(ENDMEMBERS[endm], np.float32)
    out = fr.copy()
    full = np.zeros((T, H, W), np.float32)
    for j in range(nf):
        a = a_true[j][..., None]
        out[START + j] = (1 - a) * fr[START + j] + a * S
        full[START + j] = a_true[j]
    out8 = np.clip(np.round(out * 255), 0, 255).astype(np.uint8)
    return out8, full, src


def boundary_dist(m1, m2):
    """Symmetric mean distance between boundaries of two boolean masks. nan if either empty."""
    if m1.sum() == 0 or m2.sum() == 0:
        return np.nan
    def bd(m):
        mm = m.astype(np.uint8)
        er = cv2.erode(mm, np.ones((3, 3), np.uint8))
        return (mm - er).astype(bool)
    b1, b2 = bd(m1), bd(m2)
    d2 = cv2.distanceTransform((~b2).astype(np.uint8), cv2.DIST_L2, 3)
    d1 = cv2.distanceTransform((~b1).astype(np.uint8), cv2.DIST_L2, 3)
    return float(0.5 * (d2[b1].mean() + d1[b2].mean()))


def evaluate_case(sq, k, amax, endm, params=None):
    p = params or get_params()
    p = dict(p); p["min_frames"] = 30
    frames, a_true, src = make_case(sq, k, amax, endm)
    s2 = dict(frames=frames, offsets=sq["offsets"][:len(frames)], epochs=sq["epochs"][:len(frames)], name=sq["name"])
    r = pipeline.label_sequence(s2, p, pre_idx=np.arange(0, PRE_END + 1))
    if r["excluded"]:
        return dict(name=sq["name"], k=k, amax=amax, endm=endm, excluded=r["excluded"])
    pr = r["prep"]
    al = pr["alpha"]
    levels = [("L0", pr["L0"])] + [(f"{l:.2f}", l) for l in p["levels"]]
    rows = dict(name=sq["name"], k=k, amax=amax, endm=endm, excluded=None, L0=pr["L0"], S_hat=[float(x) for x in pr["S"]],
                S_fitted=pr["S_fitted"])
    # opacity error where truth >= 0.10, frames START..end
    sel = (a_true >= 0.10)
    sel[:START] = False
    if sel.sum() == 0:
        rows["mae"] = np.nan; rows["bias"] = np.nan
    else:
        diff = al[sel] - a_true[sel]
        rows["mae"] = float(np.abs(diff).mean()); rows["bias"] = float(diff.mean())
        bins = [(0.1, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 1.01)]
        for lo, hi in bins:
            m = sel & (a_true >= lo) & (a_true < hi)
            rows[f"bias_{lo:.1f}"] = float((al[m] - a_true[m]).mean()) if m.sum() else np.nan
            rows[f"mae_{lo:.1f}"] = float(np.abs(al[m] - a_true[m]).mean()) if m.sum() else np.nan
    # edge position error per level, mean over frames where the truth has a region of >= 20 px
    for name, lv in levels:
        errs = []
        for t in range(START, len(al)):
            mt = a_true[t] >= lv
            if mt.sum() < 20:
                continue
            # compare only inside a window around the planted plume; false regions elsewhere are counted separately
            win = cv2.dilate((a_true[t] > 0.005).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (81, 81))).astype(bool)
            me = (al[t] >= np.maximum(lv, pr["T"])) & win
            errs.append(boundary_dist(mt, me))
        e = np.array(errs, float)
        rows[f"edge_{name}"] = float(np.nanmean(e)) if len(e) and np.isfinite(e).any() else np.nan
        rows[f"edge_miss_{name}"] = float(np.isnan(e).mean()) if len(e) else np.nan
    # detection of the planted plume
    main = r["main"]
    det = False; terr = np.nan
    if main is not None:
        sx, sy = main["seed_xy"]
        if np.hypot(sx - src[0], sy - src[1]) <= 40:
            det = True; terr = float(r["first_frame"] - START)
    rows["detected"] = det; rows["first_err_frames"] = terr
    rows["false_smoke_chains"] = int(sum(1 for c in r["chains"] if c["cls"] == "smoke" and c is not main))
    return rows


def lite_cases(names):
    """Cases used inside the improvement loop: one plume seed, endmember cycles over the four."""
    ends = list(ENDMEMBERS)
    out = []
    for i, n in enumerate(names):
        for j, am in enumerate(AMAX):
            out.append((n, 0, am, ends[(i + j) % 4]))
    return out


def full_cases(names):
    return [(n, k, am, e) for n in names for k in (0, 1) for am in AMAX for e in ENDMEMBERS]

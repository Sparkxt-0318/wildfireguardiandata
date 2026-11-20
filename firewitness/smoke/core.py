"""Opacity map: background, lighting correction, endmember, noise floor.
Credit: HPWREN, http://hpwren.ucsd.edu/ (image data)."""
from __future__ import annotations
import numpy as np
import cv2
from . import seq
from .params import get as get_params

cv2.setNumThreads(1)
H, W, BAN = seq.H, seq.W, seq.BANNER


def lum(x):
    return 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]


def valid_mask():
    m = np.zeros((H, W), bool)
    m[BAN:H - BAN, :] = True
    return m


VALID = valid_mask()


def _hp(gray):
    g = gray - cv2.GaussianBlur(gray, (0, 0), 8)
    return g * _WIN


_WIN = np.outer(np.hanning(H), np.hanning(W)).astype(np.float32)


def estimate_shift(ref_gray, gray):
    (dx, dy), resp = cv2.phaseCorrelate(_hp(ref_gray), _hp(gray))
    return float(dx), float(dy), float(resp)


def shift_image(img, dx, dy):
    M = np.float32([[1, 0, -dx], [0, 1, -dy]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


_SUB = (slice(BAN, H - BAN, 3), slice(None, None, 3))


def fit_gain_offset(frame, ref, iters=6):
    """Robust per-channel I ~ g*ref + o (Tukey biweight). Returns g(3), o(3)."""
    g = np.ones(3, np.float32); o = np.zeros(3, np.float32)
    for c in range(3):
        x = ref[_SUB][..., c].ravel().astype(np.float64)
        y = frame[_SUB][..., c].ravel().astype(np.float64)
        gc, oc = 1.0, 0.0
        w = np.ones_like(x)
        for _ in range(iters):
            sw = w.sum()
            if sw < 1e-6:
                break
            mx = (w * x).sum() / sw; my = (w * y).sum() / sw
            vx = (w * (x - mx) ** 2).sum()
            if vx < 1e-9:
                break
            gc = (w * (x - mx) * (y - my)).sum() / vx
            gc = float(np.clip(gc, 0.5, 2.0))
            oc = my - gc * mx
            r = y - (gc * x + oc)
            s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-4
            u = r / (4.685 * s)
            w = np.where(np.abs(u) < 1, (1 - u * u) ** 2, 0.0)
        g[c], o[c] = gc, oc
    return g, o


def normalise(frame, ref):
    g, o = fit_gain_offset(frame, ref)
    return np.clip((frame - o) / g, -0.2, 1.2).astype(np.float32), g, o


def smooth(x, sigma):
    return cv2.GaussianBlur(x, (0, 0), sigma) if sigma > 0 else x


def build_background(frames_f, idx):
    """frames_f float32 (T,H,W,3); idx = indices of background frames. Returns B and normalised copies."""
    ref0 = np.median(frames_f[idx], axis=0)
    norm = np.stack([normalise(frames_f[i], ref0)[0] for i in idx])
    B = np.median(norm, axis=0)
    norm = np.stack([normalise(frames_f[i], B)[0] for i in idx])
    B = np.median(norm, axis=0)
    return B.astype(np.float32)


def estimate_endmember(ds, Bs, params, tau):
    """Least-squares intersection of lines B_p + t*(S-B_p) over changed pixels (vanishing point of the colour changes).
    ds: list of (H,W,3) smoothed differences. Falls back to a neutral grey prior."""
    P = []; Q = []
    for d in ds:
        m = (np.linalg.norm(d, axis=2) >= tau) & VALID
        if m.sum() == 0:
            continue
        P.append(Bs[m]); Q.append(d[m])
    prior = np.full(3, params["endmember_prior"], np.float64)
    if not P:
        return prior, False
    B = np.concatenate(P).astype(np.float64); D = np.concatenate(Q).astype(np.float64)
    if len(B) < params["support_min_px"]:
        return prior, False
    if len(B) > 60000:
        sel = np.linspace(0, len(B) - 1, 60000).astype(int)
        B = B[sel]; D = D[sel]
    nrm = np.linalg.norm(D, axis=1, keepdims=True)
    n = D / np.maximum(nrm, 1e-9)
    w = nrm[:, 0]
    A = np.zeros((3, 3)); b = np.zeros(3)
    for i in range(3):
        for j in range(3):
            A[i, j] = (w * ((i == j) - n[:, i] * n[:, j])).sum()
    b = np.einsum("p,pij,pj->i", w, np.eye(3)[None] - n[:, :, None] * n[:, None, :], B)
    lam = params["endmember_prior_weight"] * w.sum()
    A = A + lam * np.eye(3); b = b + lam * prior
    S = np.clip(np.linalg.solve(A, b), 0.0, 1.0)
    sd = S[None, :] - B
    agree = ((sd * D).sum(1) > 0).mean()
    if agree < 0.8:
        return prior, False
    return S, True


def opacity(d, Bs, S, params):
    """alpha = projection of change onto (S - B), clipped to [0,1]. S: (3,) endmember."""
    sd = S[None, None, :].astype(np.float32) - Bs
    den = np.maximum((sd * sd).sum(-1), params["min_endmember_dist2"])
    a = (d * sd).sum(-1) / den
    return np.clip(a, 0.0, 1.0).astype(np.float32)


def default_endmember_alpha(d, Bs, params):
    """Before any endmember is known: neutral dark or light grey chosen by the sign of the luminance change."""
    dy = lum(d)
    s = np.where(dy >= 0, params["endmember_light"], params["endmember_dark"]).astype(np.float32)
    sd = s[..., None] - Bs
    den = np.maximum((sd * sd).sum(-1), params["min_endmember_dist2"])
    return np.clip((d * sd).sum(-1) / den, 0.0, 1.0).astype(np.float32)

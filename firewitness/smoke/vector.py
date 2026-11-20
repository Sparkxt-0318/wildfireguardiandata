"""Per-pixel vector of measured variables. Credit: HPWREN, http://hpwren.ucsd.edu/ (image data).
channels: opacity, colour_shift, texture_loss, speed (px/min), direction (deg, 0=right, 90=up),
attached (1 inside the lineage of the labelled plume), growth (opacity change per minute)."""
from __future__ import annotations
import numpy as np
import cv2
from . import core
from .core import H, W, lum, smooth

VARS = ["opacity", "colour_shift", "texture_loss", "speed", "direction", "attached", "growth"]


def _chroma(x):
    s = x.sum(-1, keepdims=True) + 1e-3
    return np.stack([(x[..., 0] - x[..., 1]), (x[..., 2] - x[..., 1])], -1) / s


def _grad_energy(y):
    gx = cv2.Sobel(y, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(y, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.GaussianBlur(np.sqrt(gx * gx + gy * gy), (0, 0), 4)


def flow(prev_a, a):
    p = (np.clip(prev_a, 0, 1) * 255).astype(np.uint8)
    c = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    return cv2.calcOpticalFlowFarneback(p, c, None, 0.5, 3, 21, 3, 5, 1.1, 0)


def vector_frame(prep, t, attached_mask=None, dt_min=1.0):
    """Returns float32 array (len(VARS), H, W). Deterministic function of the prepared sequence."""
    sg = prep["params"]["smooth_sigma"]
    fr = prep["frames"][t]; Bs = prep["Bs"]
    n, _, _ = core.normalise(fr, prep["B"])
    Is = smooth(n, sg)
    a = prep["alpha"][t]
    cs = np.linalg.norm(_chroma(Is) - _chroma(Bs), axis=-1)
    gb = _grad_energy(lum(Bs)); gi = _grad_energy(lum(Is))
    tl = np.where(gb > 0.01, 1.0 - gi / np.maximum(gb, 1e-4), np.nan).clip(-1, 1)
    if t > 0:
        fl = flow(prep["alpha"][t - 1], a)
        spd = np.hypot(fl[..., 0], fl[..., 1]) / dt_min
        ang = (np.degrees(np.arctan2(-fl[..., 1], fl[..., 0])) + 360.0) % 360.0
        da = (a - prep["alpha"][t - 1]) / dt_min
    else:
        spd = np.zeros((H, W), np.float32); ang = np.zeros((H, W), np.float32); da = np.zeros((H, W), np.float32)
    att = np.zeros((H, W), np.float32) if attached_mask is None else attached_mask.astype(np.float32)
    return np.stack([a, cs, tl, spd, ang, att, da]).astype(np.float32)

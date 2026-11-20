"""Vectorised raster operations (numpy only)."""
from __future__ import annotations

import numpy as np


def dilate_space(m: np.ndarray, r: int) -> np.ndarray:
    """Chebyshev dilation by r cells over the last two axes of a bool array."""
    if r <= 0:
        return m
    out = m.copy()
    H, W = m.shape[-2:]
    a = m.copy()
    for k in range(1, r + 1):
        out[..., k:, :] |= m[..., :H - k, :]
        out[..., :H - k, :] |= m[..., k:, :]
    b = out.copy()
    for k in range(1, r + 1):
        out[..., :, k:] |= b[..., :, :W - k]
        out[..., :, :W - k] |= b[..., :, k:]
    return out


def dilate_time(m: np.ndarray, tau: int) -> np.ndarray:
    """Dilation by +-tau steps along axis 0 (calendar-contiguous arrays)."""
    if tau <= 0:
        return m
    out = m.copy()
    T = m.shape[0]
    for k in range(1, tau + 1):
        if k < T:
            out[k:] |= m[:T - k]
            out[:T - k] |= m[k:]
    return out


def to_calendar(dates: np.ndarray, arr: np.ndarray, fill=False):
    """Place (T,...) onto a contiguous daily calendar; returns (cal_arr, index_of_each_date, first_day)."""
    d0, d1 = int(dates[0]), int(dates[-1])
    n = d1 - d0 + 1
    out = np.full((n,) + arr.shape[1:], fill, dtype=arr.dtype)
    idx = (dates - d0).astype(np.int64)
    out[idx] = arr
    return out, idx, d0


def box_count(m: np.ndarray, r: int) -> np.ndarray:
    """Number of True cells within Chebyshev radius r (including the cell), over the last two axes."""
    x = m.astype(np.float32)
    ii = np.zeros(x.shape[:-2] + (x.shape[-2] + 1, x.shape[-1] + 1), np.float32)
    ii[..., 1:, 1:] = x.cumsum(-2).cumsum(-1)
    H, W = m.shape[-2:]
    y0 = np.clip(np.arange(H) - r, 0, H); y1 = np.clip(np.arange(H) + r + 1, 0, H)
    x0 = np.clip(np.arange(W) - r, 0, W); x1 = np.clip(np.arange(W) + r + 1, 0, W)
    return ii[..., y1[:, None], x1[None, :]] - ii[..., y0[:, None], x1[None, :]] \
        - ii[..., y1[:, None], x0[None, :]] + ii[..., y0[:, None], x0[None, :]]


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann-Whitney AUC with ties handled by midranks."""
    n1, n0 = len(pos), len(neg)
    if n1 == 0 or n0 == 0:
        return float("nan")
    allv = np.concatenate([pos, neg])
    order = np.argsort(allv, kind="mergesort")
    sv = allv[order]
    ranks = np.empty(len(allv), np.float64)
    # midranks
    uniq, start, counts = np.unique(sv, return_index=True, return_counts=True)
    mid = start + (counts + 1) / 2.0
    ranks[order] = np.repeat(mid, counts)
    return float((ranks[:n1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))

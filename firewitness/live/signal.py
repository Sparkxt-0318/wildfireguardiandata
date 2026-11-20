"""Signal, background and site score (protocol §3). One definition for trace-back, replay and the live service.

Arrays are [day, slot, row, col]. Day 0 is the fire day, days 1..8 are the previous days (day index j = j days
earlier). Everything here is causal in time when the background days are earlier days: the neighbour reference is
taken from the same frame and the own-history reference from previous days.
"""
from __future__ import annotations

import numpy as np
from scipy.special import log_ndtr, ndtri

ANN_OUT, ANN_IN = 9, 5          # annulus: 9x9 window minus central 5x5
MIN_ANN = 10
MIN_HIST = 6
S_FLOOR = 0.5
UCAP = 8.0
CLOUD_BUF = 2                   # amendment 1: a pixel within 2 px of an ACM cloudy pixel is not clear
SCENE_Z, SCENE_FRAC, SCENE_WIN = 3.0, 0.05, 33   # amendment 1: frame unusable where >5% of the local window has z>3


def _offsets(outer=ANN_OUT, inner=ANN_IN):
    ho, hi = outer // 2, inner // 2
    return [(i, j) for i in range(-ho, ho + 1) for j in range(-ho, ho + 1) if not (abs(i) <= hi and abs(j) <= hi)]


def shift2(a, i, j, fill=np.nan):
    """out[..., y, x] = a[..., y+i, x+j] (NaN outside)."""
    out = np.full_like(a, fill)
    H, W = a.shape[-2:]
    ys, ye = max(0, -i), min(H, H - i)
    xs, xe = max(0, -j), min(W, W - j)
    out[..., ys:ye, xs:xe] = a[..., ys + i:ye + i, xs + j:xe + j]
    return out


def clear_mask(acm, cloudy_min=2, buf=None):
    """Clear = ACM below cloudy_min (255 missing counts as not clear) and no cloudy pixel within buf pixels."""
    buf = CLOUD_BUF if buf is None else buf
    cloudy = ~(acm < cloudy_min)
    if buf <= 0:
        return ~cloudy
    from scipy.ndimage import maximum_filter
    size = [1] * (cloudy.ndim - 2) + [2 * buf + 1, 2 * buf + 1]
    near = maximum_filter(cloudy, size=size, mode="constant", cval=False)
    return ~near


def scene_filter(z: np.ndarray, zthr: float = None, frac: float = None, win: int = None) -> np.ndarray:
    """Remove (NaN) z where more than `frac` of the clear pixels in the local win x win window exceed zthr.

    A fire is local; a large share of anomalous pixels at once means unmasked cloud, haze or a scene-wide effect."""
    from scipy.ndimage import uniform_filter
    zthr = SCENE_Z if zthr is None else zthr
    frac = SCENE_FRAC if frac is None else frac
    win = SCENE_WIN if win is None else win
    fin = np.isfinite(z)
    hi = fin & (z > zthr)
    size = [1] * (z.ndim - 2) + [win, win]
    a = uniform_filter(hi.astype(np.float32), size=size, mode="constant")
    b = uniform_filter(fin.astype(np.float32), size=size, mode="constant")
    with np.errstate(all="ignore"):
        f = a / b
    return np.where(f > frac, np.nan, z)


def feature(series: dict, name: str = "dT", cloudy_min: int = 2):
    """Per-pixel feature with clouds masked. dT = BT7 - BT14; bt7 = BT7."""
    if name == "dT":
        f = series["BT7"] - series["BT14"]
    elif name == "bt7":
        f = series["BT7"].copy()
    else:
        raise ValueError(name)
    f = np.where(clear_mask(series["ACM"], cloudy_min), f, np.nan)
    return f.astype(np.float32)


def residual(f: np.ndarray) -> np.ndarray:
    """r = f - median of the clear annulus at the same frame (needs >= MIN_ANN)."""
    lead = f.shape[:-2]
    out = np.full_like(f, np.nan)
    offs = _offsets()
    # loop over leading index blocks to bound memory
    flat = f.reshape((-1,) + f.shape[-2:])
    of = out.reshape((-1,) + f.shape[-2:])
    step = 64
    for s in range(0, flat.shape[0], step):
        blk = flat[s:s + step]
        st = np.stack([shift2(blk, i, j) for i, j in offs], 0)
        cnt = np.isfinite(st).sum(0)
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                med = np.nanmedian(st, 0)
        med[cnt < MIN_ANN] = np.nan
        of[s:s + step] = blk - med
    return out.reshape(lead + f.shape[-2:])


def history_stats(r: np.ndarray, days, slot_halfwidth: int = 1):
    """Median and robust scale of r over the given background days at slots k-1..k+1. r: [D, T, H, W]."""
    samples = []
    for d in days:
        for dk in range(-slot_halfwidth, slot_halfwidth + 1):
            x = np.full_like(r[d], np.nan)
            T = r.shape[1]
            if dk >= 0:
                x[:T - dk] = r[d, dk:]
            else:
                x[-dk:] = r[d, :T + dk]
            samples.append(x)
    st = np.stack(samples, 0)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        cnt = np.isfinite(st).sum(0)
        med = np.nanmedian(st, 0)
        mad = np.nanmedian(np.abs(st - med), 0)
    sc = np.maximum(S_FLOOR, 1.4826 * mad)
    med[cnt < MIN_HIST] = np.nan
    return med, sc


def bg_days(day: int, ndays: int = 9, k: int = 7):
    """Background days: day 0 -> 1..7; placebo day j -> the other seven of 1..8."""
    if day == 0:
        return list(range(1, k + 1))
    return [d for d in range(1, ndays) if d != day][:k]


def zscore_all(r: np.ndarray, ndays: int = 9) -> np.ndarray:
    z = np.full_like(r, np.nan)
    for d in range(r.shape[0]):
        med, sc = history_stats(r, bg_days(d, ndays))
        z[d] = (r[d] - med) / sc
    return z


def compact_filter(z: np.ndarray, nmax: int, zthr: float = 3.0) -> np.ndarray:
    """Discard z (NaN) where more than nmax pixels of the 9x9 window outside the central 3x3 exceed zthr:
    an early fire is a point source; an extended warm patch (harvest, surface change) is not."""
    from scipy.ndimage import uniform_filter
    hi = (np.isfinite(z) & (z > zthr)).astype(np.float32)
    size9 = [1] * (z.ndim - 2) + [9, 9]
    size3 = [1] * (z.ndim - 2) + [3, 3]
    n9 = np.rint(uniform_filter(hi, size=size9, mode="constant") * 81)
    n3 = np.rint(uniform_filter(hi, size=size3, mode="constant") * 9)
    return np.where(n9 - n3 > nmax, np.nan, z)


def site_u(z: np.ndarray, cap: float = UCAP) -> np.ndarray:
    """Site score for every pixel as a 3x3 site: u = Phi^-1(Phi(Zmax)^m), capped."""
    st = np.stack([shift2(z, i, j) for i in (-1, 0, 1) for j in (-1, 0, 1)], 0)
    m = np.isfinite(st).sum(0)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        Z = np.nanmax(st, 0)
    return u_from_max(Z, m, cap)


def u_from_max(Z, m, cap=UCAP):
    Z = np.asarray(Z, float)
    m = np.asarray(m)
    with np.errstate(all="ignore"):
        lp = m * log_ndtr(np.where(np.isfinite(Z), Z, 0.0))      # log P(max <= Z) under the null
        tail = -np.expm1(lp)                                       # P(max > Z)
        u = -ndtri(np.clip(tail, 1e-300, 1 - 1e-16))
    u = np.where((m > 0) & np.isfinite(Z), np.minimum(u, cap), np.nan)
    return u.astype(np.float32)


def cusum(u: np.ndarray, k: float, h: float | None = None, reset: bool = False):
    """One-sided CUSUM along axis 0 of u (frames x ...). NaN frames leave S unchanged.

    Returns S (same shape) and, if h is given, a boolean array of alarm frames (S >= h; with reset=True S restarts at 0
    after each alarm)."""
    S = np.zeros(u.shape, np.float32)
    A = np.zeros(u.shape, bool) if h is not None else None
    s = np.zeros(u.shape[1:], np.float32)
    for t in range(u.shape[0]):
        x = u[t]
        upd = np.isfinite(x)
        s = np.where(upd, np.maximum(0.0, s + np.where(upd, x, 0) - k), s)
        if h is not None:
            a = s >= h
            A[t] = a
            if reset:
                s = np.where(a, 0.0, s)
        S[t] = s
    return S, A


def site_series(series: dict, feat: str = "dT"):
    """Convenience: u for all pixel-sites, all days. Returns dict with r, z, u."""
    f = feature(series, feat)
    r = residual(f)
    z = scene_filter(zscore_all(r, f.shape[0]))
    u = site_u(z)
    return {"r": r, "z": z, "u": u}


def site_z_boot(r: np.ndarray, rc, days_sample, slot_halfwidth=1, drop=None):
    """z of the 3x3 window around rc on day 0 with a given list of background days (bootstrap)."""
    i, j = rc
    rr = r[:, :, i - 1:i + 2, j - 1:j + 2]
    med, sc = history_stats(rr, days_sample, slot_halfwidth)
    z = (rr[0] - med) / sc
    if drop is not None:
        z = np.where(drop, np.nan, z)
    st = z.reshape(z.shape[0], -1)
    m = np.isfinite(st).sum(1)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        Z = np.nanmax(st, 1)
    return u_from_max(Z, m)

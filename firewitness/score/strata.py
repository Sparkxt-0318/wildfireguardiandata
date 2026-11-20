"""Strata used to match negatives to positives: danger class, land cover, region, season (month)."""
from __future__ import annotations

import csv
import os

import numpy as np

from .dataset import Scene
from .geo import km_per_deg

DANGER_BINS = (30.0, 45.0, 60.0, 75.0)   # ERC edges -> classes 0..4; fixed in advance, not fitted
N_DANGER = len(DANGER_BINS) + 1


def danger_class(erc: np.ndarray, bins=DANGER_BINS) -> np.ndarray:
    e = np.nan_to_num(np.asarray(erc, dtype=np.float32), nan=0.0)
    return np.digitize(e, bins).astype(np.int8)


def lc_group(lc: np.ndarray) -> np.ndarray:
    """IGBP classes -> coarse groups: forest 1-5, shrub 6-7, savanna/grass 8-10, other 0."""
    lc = np.asarray(lc).astype(np.int16)
    g = np.zeros(lc.shape, np.int8)
    g[(lc >= 1) & (lc <= 5)] = 1
    g[(lc >= 6) & (lc <= 7)] = 2
    g[(lc >= 8) & (lc <= 10)] = 3
    g[(lc >= 11)] = 4
    return g


def region_code(region: str) -> int:
    return abs(hash_str(region)) % 100000


def hash_str(s: str) -> int:
    h = 1469598103934665603
    for ch in s.encode():
        h = ((h ^ ch) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h % 1000003


def catalogue(path: str | None = None) -> list[dict]:
    path = path or os.path.join(os.path.dirname(__file__), "data", "hard_negatives.csv")
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def near_site_mask(scene: Scene, hard_km: float = 10.0, cat=None) -> np.ndarray:
    """(H,W) bool: cell within hard_km (plus the site's stated precision) of a catalogued thermal site."""
    cat = [c for c in (cat if cat is not None else catalogue()) if c["lat"]]
    H, W = scene.state.shape[1:]
    out = np.zeros((H, W), bool)
    kmlat, kmlon = km_per_deg(scene.lat0)
    half = max(H, W) * scene.cell_km / 2
    cand = []
    for c in cat:
        dy = (float(c["lat"]) - scene.lat0) * kmlat
        dx = (float(c["lon"]) - scene.lon0) * kmlon
        if abs(dy) < half + hard_km + float(c["precision_km"]) and abs(dx) < half + hard_km + float(c["precision_km"]):
            cand.append(c)
    if not cand:
        return out
    lat, lon = scene.latlon_grid()
    for c in cand:
        d = np.hypot((lat - float(c["lat"])) * kmlat, (lon - float(c["lon"])) * kmlon)
        out |= d <= hard_km + float(c["precision_km"])
    return out


def hard_mask(scene: Scene, t: int, ref_tmax: float | None = None, hard_km: float = 10.0) -> np.ndarray:
    """Hard negative candidates on day t: top danger class and hotter than the scene's top-danger median
    (derived hot places), or near a catalogued thermal site."""
    dc = danger_class(scene.dyn["erc"][t - 1].astype(np.float32))
    tmax = scene.dyn["tmax"][t - 1].astype(np.float32)
    top = dc == N_DANGER - 1
    thr = ref_tmax if ref_tmax is not None else (float(np.nanmedian(tmax[top])) if top.any() else np.inf)
    hot = top & (tmax >= thr)
    return hot | near_site_mask(scene, hard_km)

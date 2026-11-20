"""Features known at the end of the issue day (day t-1) for predicting day t. No label from day t or later."""
from __future__ import annotations

import numpy as np

from .dataset import FIRE, Scene
from .ops import box_count
from .strata import danger_class, lc_group

WEATHER = ["erc", "tmax", "tmin", "humidity", "wind", "ndvi", "precip", "pdsi", "fc_tmax", "fc_wind", "fc_humidity", "fc_precip"]
STATIC = ["slope", "elevation"]
PROX = ["fire_self", "fire_r1", "fire_r2", "fire_r4", "fire_r8"]


def feature_names(prox: bool, weather: bool = True) -> list[str]:
    n = []
    if weather:
        n += WEATHER + STATIC + [f"lcg{g}" for g in range(5)]
    if prox:
        n += PROX
    return n


def scene_features(s: Scene, t: int, prox: bool, weather: bool = True) -> np.ndarray:
    """(H,W,F) float32 features for target day t (issue day t-1)."""
    cols = []
    H, W = s.state.shape[1:]
    if weather:
        for k in WEATHER:
            cols.append(np.nan_to_num(s.dyn[k][t - 1].astype(np.float32), nan=0.0))
        for k in STATIC:
            cols.append(np.nan_to_num(s.static[k], nan=0.0))
        g = lc_group(s.static["landcover"])
        for k in range(5):
            cols.append((g == k).astype(np.float32))
    if prox:
        f = s.state[t - 1] == FIRE
        cols.append(f.astype(np.float32))
        for r in (1, 2, 4, 8):
            cols.append(np.log1p(box_count(f, r)))
    return np.stack(cols, -1)


def danger_at(s: Scene, t: int) -> np.ndarray:
    if "erc" not in s.dyn:       # label-only scenes (caught, live): no weather, one danger class
        return np.zeros(s.state.shape[1:], np.int8)
    return danger_class(s.dyn["erc"][t - 1].astype(np.float32))

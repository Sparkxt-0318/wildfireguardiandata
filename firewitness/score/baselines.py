"""Persistence and climatology, scored on the same terms as the model."""
from __future__ import annotations

import numpy as np

from .dataset import FIRE, UNKNOWN
from .features import danger_at
from .predictions import Predictions
from .strata import lc_group


def persistence(ds, fires) -> Predictions:
    sc, info = {}, {}
    for fid in fires:
        s = ds.scenes[fid]
        a = np.full(s.state.shape, np.nan, np.float32)
        for t in s.valid_targets():
            a[t] = (s.state[t - 1] == FIRE)
        sc[fid] = a
        info[fid] = (s.dates - 1).astype(np.int32)
    return Predictions(sc, info, {"model": "persistence", "info_until_lag_days": 1})


def _key(s, t):
    d = danger_at(s, int(t)).astype(np.int64)
    g = lc_group(s.static["landcover"]).astype(np.int64)
    return (d * 5 + g) * 13 + s.month(int(t))


def climatology_fit(ds, train_fires) -> dict:
    n = np.zeros(5 * 5 * 13)
    f = np.zeros_like(n)
    for fid in train_fires:
        s = ds.scenes[fid]
        for t in s.valid_targets():
            k = _key(s, t).ravel()
            known = (s.state[t] != UNKNOWN).ravel()
            n += np.bincount(k[known], minlength=len(n))
            f += np.bincount(k[known & (s.state[t] == FIRE).ravel()], minlength=len(n))
    glob = f.sum() / max(n.sum(), 1)
    return (f + glob * 50) / (n + 50)     # shrink towards the global rate


def climatology(ds, fires, table) -> Predictions:
    sc, info = {}, {}
    for fid in fires:
        s = ds.scenes[fid]
        a = np.full(s.state.shape, np.nan, np.float32)
        for t in s.valid_targets():
            a[t] = table[_key(s, t)]
        sc[fid] = a
        info[fid] = (s.dates - 1).astype(np.int32)
    return Predictions(sc, info, {"model": "climatology", "info_until_lag_days": 1})


def make(ds, split) -> dict:
    fires = sorted(set(split["folds"]["val"]) | set(split["folds"]["test"]))
    tab = climatology_fit(ds, split["folds"]["train"])
    return {"persistence": persistence(ds, fires), "climatology": climatology(ds, fires, tab)}

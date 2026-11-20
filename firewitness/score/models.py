"""Models used by the gates (honest ones and planted cheats). All numpy, no external ML library."""
from __future__ import annotations

import numpy as np

from .dataset import FIRE
from .features import feature_names, scene_features
from .predictions import Predictions


def gather(ds, table, ids, prox: bool, weather: bool = True, max_rows: int = 600000, seed: int = 0):
    n = len(table["label"])
    sel = np.arange(n)
    if n > max_rows:
        sel = np.sort(np.random.default_rng(seed).choice(n, max_rows, replace=False))
    f, t, y, x = (table[k][sel] for k in ("fire", "t", "y", "x"))
    key = f.astype(np.int64) * 100000 + t
    order = np.argsort(key, kind="stable")
    X = None
    out_idx = np.zeros(len(sel), np.int64)
    pos = 0
    ks = key[order]
    bounds = np.flatnonzero(np.diff(ks)) + 1
    for grp in np.split(order, bounds):
        if len(grp) == 0:
            continue
        s = ds.scenes[ids[int(f[grp[0]])]]
        F = scene_features(s, int(t[grp[0]]), prox, weather)
        v = F[y[grp], x[grp]]
        if X is None:
            X = np.zeros((len(sel), v.shape[1]), np.float32)
        X[grp] = v
    return X, table["label"][sel].astype(np.float64)


class Logistic:
    def __init__(self, name="logistic", prox=False, weather=True, l2=1.0):
        self.name, self.prox, self.weather, self.l2 = name, prox, weather, l2

    def fit(self, ds, table, ids):
        X, y = gather(ds, table, ids, self.prox, self.weather)
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-6
        Z = np.hstack([(X - self.mu) / self.sd, np.ones((len(X), 1), np.float32)]).astype(np.float64)
        w = np.zeros(Z.shape[1])
        for _ in range(25):                      # IRLS with ridge
            p = 1 / (1 + np.exp(-np.clip(Z @ w, -30, 30)))
            g = Z.T @ (p - y) + self.l2 * np.r_[w[:-1], 0]
            Hm = (Z * (p * (1 - p))[:, None]).T @ Z + self.l2 * np.eye(len(w))
            step = np.linalg.solve(Hm, g)
            w -= step
            if np.abs(step).max() < 1e-6:
                break
        self.w = w
        return self

    def predict(self, ds, fires) -> Predictions:
        sc, info = {}, {}
        for fid in fires:
            s = ds.scenes[fid]
            a = np.full(s.state.shape, np.nan, np.float32)
            for t in s.valid_targets():
                F = scene_features(s, int(t), self.prox, self.weather)
                z = ((F - self.mu) / self.sd) @ self.w[:-1] + self.w[-1]
                a[t] = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
            sc[fid] = a
            info[fid] = (s.dates - 1).astype(np.int32)
        return Predictions(sc, info, {"model": self.name, "info_until_lag_days": 1})


def _loc_key(s):
    lat, lon = s.latlon_grid()
    return (np.round(lat / (s.cell_km / 111.32)).astype(np.int64) * 1000003 + np.round(lon / (s.cell_km / 85.0)).astype(np.int64))


class Memoriser:
    """Scores a cell by how often that exact location burned in the rows it was trained on."""

    def __init__(self, name="location-memoriser"):
        self.name = name

    def fit(self, ds, fires, row_mask=None):
        keys, fire = [], []
        for fid in fires:
            s = ds.scenes[fid]
            k = _loc_key(s)
            rm = row_mask(fid) if row_mask else np.ones(s.state.shape, bool)
            tg = np.zeros(len(s.dates), bool); tg[s.valid_targets()] = True
            rm = rm & tg[:, None, None]
            n_rows = rm.sum(0)
            n_fire = (rm & (s.state == FIRE)).sum(0)
            keys.append(k.ravel()); fire.append(np.stack([n_fire.ravel(), n_rows.ravel()], 1))
        K = np.concatenate(keys); V = np.concatenate(fire)
        uk, inv = np.unique(K, return_inverse=True)
        self.uk = uk
        self.f = np.bincount(inv, V[:, 0], minlength=len(uk)); self.n = np.bincount(inv, V[:, 1], minlength=len(uk))
        self.trained_on = sorted(fires)
        return self

    def predict(self, ds, fires) -> Predictions:
        sc, info = {}, {}
        for fid in fires:
            s = ds.scenes[fid]
            k = _loc_key(s).ravel()
            j = np.searchsorted(self.uk, k).clip(0, len(self.uk) - 1)
            hit = self.uk[j] == k
            v = np.where(hit, self.f[j] / np.maximum(self.n[j], 1), 0.0).reshape(s.state.shape[1:])
            a = np.full(s.state.shape, np.nan, np.float32)
            for t in s.valid_targets():
                a[t] = v
            sc[fid] = a
            info[fid] = (s.dates - 1).astype(np.int32)
        return Predictions(sc, info, {"model": self.name, "info_until_lag_days": 1, "trained_on_fires": getattr(self, "trained_on", [])})


def flag_everything(ds, fires) -> Predictions:
    sc, info = {}, {}
    for fid in fires:
        s = ds.scenes[fid]
        a = np.full(s.state.shape, np.nan, np.float32)
        a[s.valid_targets()] = 1.0
        sc[fid] = a
        info[fid] = (s.dates - 1).astype(np.int32)
    return Predictions(sc, info, {"model": "flag-everything", "info_until_lag_days": 1})


def leaky(ds, fires, kind="scar", honest_declaration=False) -> Predictions:
    """Planted cheat: uses the whole fire's burned area ('scar') or the next day's mask ('next'),
    and (unless honest_declaration) claims it only used information up to the issue day."""
    from .ops import box_count
    sc, info = {}, {}
    for fid in fires:
        s = ds.scenes[fid]
        a = np.full(s.state.shape, np.nan, np.float32)
        ever = (s.state == FIRE).any(0)
        scar = box_count(ever, 1).astype(np.float32)
        for t in s.valid_targets():
            if kind == "scar":
                a[t] = scar / 9.0
            else:
                nxt = (s.state[t] == FIRE).astype(np.float32)   # the label itself, one day early
                a[t] = nxt
        sc[fid] = a
        iu = (s.dates - 1).astype(np.int32) if not honest_declaration else (s.dates + 5).astype(np.int32)
        info[fid] = iu
    return Predictions(sc, info, {"model": f"leaky-{kind}", "info_until_lag_days": 1})


class Interpolator:
    """Planted cheat for random cell-day splits: fills a held-out cell-day from the labels of the same fire on the
    neighbouring days (t-1 and t+1) that happen to be in the training rows. Under a split by fire, no row of a test
    fire is ever in training, so it has nothing to interpolate from."""

    def __init__(self, name="neighbour-day-interpolator"):
        self.name = name

    def predict(self, ds, fires, row_mask) -> Predictions:
        from .ops import dilate_space
        sc, info = {}, {}
        for fid in fires:
            s = ds.scenes[fid]
            tr = row_mask(fid)
            F = (s.state == FIRE) & tr
            a = np.full(s.state.shape, np.nan, np.float32)
            T = len(s.dates)
            for t in s.valid_targets():
                m = np.zeros(s.state.shape[1:], bool)
                if t >= 1:
                    m |= F[t - 1]
                if t + 1 < T:
                    m |= F[t + 1]
                a[t] = dilate_space(m, 1).astype(np.float32) + 0.5 * dilate_space(m, 3)
            sc[fid] = a
            info[fid] = (s.dates - 1).astype(np.int32)   # it claims issue-day info; the screen cannot see t+1 training rows
        return Predictions(sc, info, {"model": self.name, "info_until_lag_days": 1})


def leaky_front(ds, fires) -> Predictions:
    """Round-2 cheat: peeks at today's label only where it is hard to notice (within 3 cells of yesterday's fire),
    falls back to persistence elsewhere, and declares info_until = issue day."""
    from .ops import dilate_space
    sc, info = {}, {}
    for fid in fires:
        s = ds.scenes[fid]
        a = np.full(s.state.shape, np.nan, np.float32)
        for t in s.valid_targets():
            prev = s.state[t - 1] == FIRE
            near = dilate_space(prev, 3)
            today = s.state[t] == FIRE
            a[t] = np.where(near, today, 0.0).astype(np.float32) + 0.1 * prev
        sc[fid] = a
        info[fid] = (s.dates - 1).astype(np.int32)
    return Predictions(sc, info, {"model": "leaky-front", "info_until_lag_days": 1})


def halo(ds, fires, radius=2) -> Predictions:
    """Round-3 cheat: persistence thickened by `radius` cells, to profit from tolerant matching."""
    from .ops import dilate_space
    sc, info = {}, {}
    for fid in fires:
        s = ds.scenes[fid]
        a = np.full(s.state.shape, np.nan, np.float32)
        for t in s.valid_targets():
            a[t] = dilate_space(s.state[t - 1] == FIRE, radius).astype(np.float32)
        sc[fid] = a
        info[fid] = (s.dates - 1).astype(np.int32)
    return Predictions(sc, info, {"model": "halo", "info_until_lag_days": 1})


def abstain_cheat(ds, fires) -> Predictions:
    """Round-5 cheat: persistence, but silent on days where (it secretly knows) no fire burns today."""
    sc, info = {}, {}
    for fid in fires:
        s = ds.scenes[fid]
        a = np.full(s.state.shape, np.nan, np.float32)
        for t in s.valid_targets():
            a[t] = (s.state[t - 1] == FIRE) if (s.state[t] == FIRE).any() else 0.0
        sc[fid] = a
        info[fid] = (s.dates - 1).astype(np.int32)
    return Predictions(sc, info, {"model": "abstain", "info_until_lag_days": 1})

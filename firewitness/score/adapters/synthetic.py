"""Synthetic benchmark with known truth, used by the gate tests. Fires grow from an ignition cell; spread
probability rises with ERC, wind and slope. Weather is shared across the scene (so it ranks days, not cells)."""
from __future__ import annotations

import datetime as dt

import numpy as np

from ..dataset import Dataset, FIRE, NO_FIRE, UNKNOWN, Scene
from ..ops import dilate_space


def build(n_fires: int = 60, size: int = 48, seed: int = 0, years=(2018, 2019, 2020, 2021)) -> Dataset:
    rng = np.random.default_rng(seed)
    scenes = {}
    for i in range(n_fires):
        T = int(rng.integers(12, 22))
        year = int(rng.choice(years))
        start = dt.date(year, int(rng.integers(5, 10)), int(rng.integers(1, 28)))
        lat0, lon0 = rng.uniform(34, 46), rng.uniform(-124, -108)
        dates = np.array([(start + dt.timedelta(days=k)).toordinal() for k in range(T)], np.int32)
        H = W = size
        slope = np.clip(rng.gamma(2, 3, (H, W)), 0, 45).astype(np.float32)
        lc = rng.choice([2, 4, 7, 8, 10, 12], size=(H // 8 + 1, W // 8 + 1))
        lc = np.kron(lc, np.ones((8, 8), int))[:H, :W].astype(np.float32)
        elev = (1000 + 800 * rng.standard_normal() + 50 * rng.standard_normal((H, W))).astype(np.float32)
        base = rng.uniform(25, 85)           # fire-specific dryness level
        erc = np.clip(base + np.cumsum(rng.normal(0, 3, T)), 5, 110)
        wind = np.clip(rng.normal(4, 2, T), 0.5, 15)
        tmax = 290 + 0.15 * erc + rng.normal(0, 1.5, T)
        hum = np.clip(0.012 - 0.00008 * erc + rng.normal(0, 0.0007, T), 0.001, 0.02)
        ndvi = np.clip((6000 - 40 * erc)[:, None, None] + rng.normal(0, 300, (T, H, W)), 500, 9000)
        precip = np.where(rng.random(T) < 0.08, rng.gamma(2, 2, T), 0.0)
        burning = np.zeros((H, W), bool)
        burning[int(rng.integers(H // 4, 3 * H // 4)), int(rng.integers(W // 4, 3 * W // 4))] = True
        age = np.zeros((H, W), int)
        state = np.zeros((T, H, W), np.int8)
        lcf = np.where(np.isin(lc, [8, 10, 12]), 1.3, np.where(np.isin(lc, [2, 4]), 0.9, 1.0))
        for t in range(T):
            if t > 0:
                grow = dilate_space(burning, 1) & ~burning
                p = 1 / (1 + np.exp(-(-3.2 + 0.035 * erc[t - 1] + 0.12 * wind[t - 1] + 0.03 * slope))) * lcf
                p = np.where(precip[t - 1] > 3, p * 0.3, p)
                newly = grow & (rng.random((H, W)) < np.clip(p, 0, 0.95))
                age = np.where(burning, age + 1, 0)
                burning = (burning & (age < 3)) | newly
                # spotting: ignitions 2-6 cells ahead of the front, more likely in wind and dry fuel
                if burning.any():
                    n_spot = rng.poisson(0.15 + 0.08 * wind[t - 1] + 0.01 * erc[t - 1])
                    by, bx = np.nonzero(burning)
                    for _ in range(n_spot):
                        j = int(rng.integers(len(by)))
                        ang, dist = rng.uniform(0, 2 * np.pi), rng.uniform(2.5, 6)
                        yy, xx = int(by[j] + dist * np.sin(ang)), int(bx[j] + dist * np.cos(ang))
                        if 0 <= yy < H and 0 <= xx < W:
                            burning[yy, xx] = True
            state[t] = np.where(burning, FIRE, NO_FIRE)
            cloud = dilate_space(rng.random((H, W)) < 0.002, 4)
            state[t][cloud & (state[t] != FIRE)] = UNKNOWN
        fid = f"syn_{i:04d}"
        dyn = {"erc": np.broadcast_to(erc[:, None, None], (T, H, W)).astype(np.float16),
               "tmax": np.broadcast_to(tmax[:, None, None], (T, H, W)).astype(np.float16),
               "tmin": np.broadcast_to((tmax - 12)[:, None, None], (T, H, W)).astype(np.float16),
               "humidity": np.broadcast_to(hum[:, None, None], (T, H, W)).astype(np.float16),
               "wind": np.broadcast_to(wind[:, None, None], (T, H, W)).astype(np.float16),
               "ndvi": ndvi.astype(np.float16),
               "precip": np.broadcast_to(precip[:, None, None], (T, H, W)).astype(np.float16)}
        for k in ("pdsi", "fc_tmax", "fc_wind", "fc_humidity", "fc_precip"):
            src = {"pdsi": -erc / 30, "fc_tmax": tmax, "fc_wind": wind, "fc_humidity": hum, "fc_precip": precip}[k]
            dyn[k] = np.broadcast_to(src[:, None, None], (T, H, W)).astype(np.float16)
        scenes[fid] = Scene(fid, dates, state, dyn, {"slope": slope, "elevation": elev, "landcover": lc}, lat0=float(lat0),
                            lon0=float(lon0), cell_km=0.75, region=f"R{int(lat0 // 4 * 4)}_{int(lon0 // 4 * 4)}", year=year,
                            interval_slack=1, meta={"source": "synthetic"})
    return Dataset("synthetic", scenes, 0.75, {"state_rule": "synthetic: clouds are unknown, the rest is known", "seed": seed})

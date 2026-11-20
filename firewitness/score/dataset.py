"""Scene dataset: the unit everything in firewitness.score works on.

A Scene is one fire's raster stack: for each day t, a state grid (0 unknown, 1 verified no fire, 2 fire),
and feature grids. Everything is vectorised with numpy. State semantics follow the three-state label format
(fire / verified no fire / unknown); adapters create it from a benchmark's own masks.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import numpy as np

UNKNOWN, NO_FIRE, FIRE = 0, 1, 2
STATE_NAMES = {UNKNOWN: "unknown", NO_FIRE: "no_fire", FIRE: "fire"}


@dataclass
class Scene:
    fire_id: str
    dates: np.ndarray                 # int32 ordinal days, strictly increasing, length T
    state: np.ndarray                 # int8 (T,H,W)
    dyn: dict                         # name -> float32 (T,H,W)   features known at the end of day t
    static: dict                      # name -> float32 (H,W)
    lat0: float = 0.0                 # latitude of scene centre
    lon0: float = 0.0
    cell_km: float = 0.375
    region: str = ""
    year: int = 0
    interval_slack: int = 1           # label interval = day +- slack (declared by the adapter)
    meta: dict = field(default_factory=dict)

    @property
    def shape(self):
        return self.state.shape

    def valid_targets(self) -> np.ndarray:
        """Indices t>=1 with dates[t] == dates[t-1]+1: days with a one-day-old issue state."""
        d = self.dates
        return np.nonzero(d[1:] - d[:-1] == 1)[0] + 1

    def latlon_grid(self):
        T, H, W = self.state.shape
        kmlat, kmlon = 111.32, 111.32 * np.cos(np.radians(self.lat0))
        ys = (np.arange(H) - (H - 1) / 2) * self.cell_km / kmlat
        xs = (np.arange(W) - (W - 1) / 2) * self.cell_km / kmlon
        return (self.lat0 - ys)[:, None] * np.ones((1, W)), self.lon0 + xs[None, :] * np.ones((H, 1))

    def month(self, t: int) -> int:
        import datetime as _d
        return _d.date.fromordinal(int(self.dates[t])).month


@dataclass
class Dataset:
    name: str
    scenes: dict
    cell_km: float = 0.375
    meta: dict = field(default_factory=dict)

    def ids(self):
        return sorted(self.scenes)

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        info = {"name": self.name, "cell_km": self.cell_km, "meta": self.meta, "scenes": {}}
        for fid in self.ids():
            s = self.scenes[fid]
            arrs = {"dates": s.dates, "state": s.state}
            arrs.update({f"dyn__{k}": v for k, v in s.dyn.items()})
            arrs.update({f"static__{k}": v for k, v in s.static.items()})
            np.savez_compressed(os.path.join(directory, f"{fid}.npz"), **arrs)
            info["scenes"][fid] = dict(lat0=s.lat0, lon0=s.lon0, cell_km=s.cell_km, region=s.region, year=s.year,
                                       interval_slack=s.interval_slack, meta=s.meta)
        with open(os.path.join(directory, "dataset.json"), "w") as f:
            json.dump(info, f, sort_keys=True, indent=1)

    @staticmethod
    def load(directory: str, ids=None) -> "Dataset":
        info = json.load(open(os.path.join(directory, "dataset.json")))
        scenes = {}
        for fid, m in info["scenes"].items():
            if ids is not None and fid not in ids:
                continue
            z = np.load(os.path.join(directory, f"{fid}.npz"))
            dyn = {k[5:]: z[k] for k in z.files if k.startswith("dyn__")}
            sta = {k[8:]: z[k] for k in z.files if k.startswith("static__")}
            scenes[fid] = Scene(fire_id=fid, dates=z["dates"], state=z["state"], dyn=dyn, static=sta, **m)
        return Dataset(info["name"], scenes, info.get("cell_km", 0.375), info.get("meta", {}))

    def summary(self) -> dict:
        n = np.zeros(3, dtype=np.int64)
        for s in self.scenes.values():
            for k in range(3):
                n[k] += int((s.state == k).sum())
        return {"fires": len(self.scenes), "cell_days": int(n.sum()), "unknown": int(n[0]), "no_fire": int(n[1]), "fire": int(n[2])}

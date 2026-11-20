"""Adapter for WildfireSpreadTS (Gerard et al. 2023, Zenodo 8006177, CC-BY-4.0).

Band order (23): 0 M11, 1 I2, 2 I1, 3 NDVI, 4 EVI2, 5 precip, 6 wind speed, 7 wind direction, 8 Tmin, 9 Tmax,
10 ERC, 11 specific humidity, 12 slope, 13 aspect, 14 elevation, 15 PDSI, 16 land cover (IGBP), 17 forecast precip,
18 forecast wind speed, 19 forecast wind dir, 20 forecast temperature, 21 forecast humidity, 22 active fire
(VIIRS 375 m detection time HHMM; NaN where nothing was detected).

State rule (the benchmark ships no cloud or validity mask, so this is the weakest link and is stated in the docs):
  fire     = active-fire band > 0
  no_fire  = no detection AND reflectance bands M11, I2, I1 all > 0 (composite present)
  unknown  = no detection AND any of those reflectance bands <= 0 or NaN
Cells are coarsened 2x2 (0.75 km): fire if any sub-cell is fire; no_fire only if all four sub-cells are no_fire.
"""
from __future__ import annotations

import datetime as dt
import glob
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from ..dataset import Dataset, FIRE, NO_FIRE, UNKNOWN, Scene
from ..geo import utm_to_latlon

DYN = {"erc": 10, "tmax": 9, "tmin": 8, "humidity": 11, "wind": 6, "ndvi": 3, "precip": 5, "pdsi": 15,
       "fc_tmax": 20, "fc_wind": 18, "fc_humidity": 21, "fc_precip": 17}
STATIC = {"slope": 12, "elevation": 14, "landcover": 16}
REGION_DEG = 4.0


def _coarsen_mean(a):  # (H,W) -> (H//2,W//2)
    H, W = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    b = a[:H, :W].reshape(H // 2, 2, W // 2, 2)
    with np.errstate(all="ignore"):
        return np.nanmean(b, axis=(1, 3)) if np.isnan(b).any() else b.mean(axis=(1, 3))


def build_scene(fire_dir: str) -> Scene | None:
    import tifffile
    files = sorted(glob.glob(os.path.join(fire_dir, "*.tif")))
    if len(files) < 3:
        return None
    fid = os.path.basename(fire_dir)
    dates, states, dyn, static = [], [], {k: [] for k in DYN}, {}
    origin = None
    for f in files:
        d = dt.date.fromisoformat(os.path.basename(f)[:-4])
        tf = tifffile.TiffFile(f)
        a = tf.asarray()
        if origin is None:
            tp = tf.pages[0].tags["ModelTiepointTag"].value
            gk = tf.pages[0].tags["GeoKeyDirectoryTag"].value
            epsg = next((gk[i + 3] for i in range(4, len(gk), 4) if gk[i] == 3072), 32610)
            origin = (tp[3], tp[4], epsg, a.shape[0], a.shape[1])
        af = a[..., 22]
        fire = np.nan_to_num(af, nan=0.0) > 0
        refl_ok = (a[..., 0] > 0) & (a[..., 1] > 0) & (a[..., 2] > 0) & ~np.isnan(a[..., 0:3]).any(axis=-1)
        H, W = fire.shape[0] // 2 * 2, fire.shape[1] // 2 * 2
        fb = fire[:H, :W].reshape(H // 2, 2, W // 2, 2).any(axis=(1, 3))
        ob = (refl_ok & ~fire)[:H, :W].reshape(H // 2, 2, W // 2, 2).all(axis=(1, 3))
        st = np.full(fb.shape, UNKNOWN, np.int8)
        st[ob] = NO_FIRE
        st[fb] = FIRE
        dates.append(d.toordinal())
        states.append(st)
        for k, b in DYN.items():
            dyn[k].append(_coarsen_mean(a[..., b]).astype(np.float16))
        if not static:
            for k, b in STATIC.items():
                if k == "landcover":
                    x = a[:H, :W, b].reshape(H // 2, 2, W // 2, 2)[:, 0, :, 0]  # top-left sub-cell (categorical)
                else:
                    x = _coarsen_mean(a[..., b])
                static[k] = np.nan_to_num(x, nan=0).astype(np.float32)
    ex, ny, epsg, H0, W0 = origin
    zone = epsg - 32600 if epsg < 32700 else epsg - 32700
    cx, cy = ex + 375.0 * W0 / 2, ny - 375.0 * H0 / 2
    lat0, lon0 = utm_to_latlon(cx, cy, zone, epsg < 32700)
    region = f"R{int(np.floor(lat0 / REGION_DEG) * REGION_DEG)}_{int(np.floor(lon0 / REGION_DEG) * REGION_DEG)}"
    order = np.argsort(dates)
    return Scene(fire_id=fid, dates=np.array(dates, np.int32)[order], state=np.stack(states)[order],
                 dyn={k: np.stack(v)[order] for k, v in dyn.items()}, static=static, lat0=lat0, lon0=lon0,
                 cell_km=0.75, region=region, year=dt.date.fromordinal(min(dates)).year, interval_slack=1,
                 meta={"source": "WildfireSpreadTS", "epsg": int(epsg)})


def _build(fd):
    try:
        s = build_scene(fd)
        return s
    except Exception as e:  # noqa: BLE001
        print("skip", fd, type(e).__name__, e, file=sys.stderr)
        return None


def build_dataset(raw_root: str, workers: int = 3, limit: int | None = None) -> Dataset:
    dirs = sorted(glob.glob(os.path.join(raw_root, "*", "fire_*")))
    if limit:
        dirs = dirs[:limit]
    with ProcessPoolExecutor(workers) as ex:
        scenes = [s for s in ex.map(_build, dirs) if s is not None]
    return Dataset("wildfirespreadts-750m", {s.fire_id: s for s in scenes}, 0.75,
                   {"source": "WildfireSpreadTS, Zenodo 8006177, CC-BY-4.0", "coarsen": 2,
                    "state_rule": "fire=active>0; no_fire=no detection & M11,I2,I1>0 for all sub-cells; else unknown"})

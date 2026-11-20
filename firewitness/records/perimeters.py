"""Gate R6: perimeters made from before-and-after imagery against the "assumed circle", on fires with known (MTBS) perimeters.

Imagery work is done by the scar module of track 50 (firewitness.caught.scar.make_perimeter).
"""
from __future__ import annotations

import json
import math
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform

from . import geo, paths

_to_m = Transformer.from_crs(4326, 5070, always_xy=True).transform


def circle_area(lon, lat, area_m2):
    r = math.sqrt(area_m2 / math.pi)
    x, y = _to_m(lon, lat)
    return Point(x, y).buffer(r, 64)


def to_m(g):
    return transform(_to_m, g)


def iou(a, b) -> float:
    if a is None or b is None or a.is_empty or b.is_empty:
        return 0.0
    a, b = a.buffer(0), b.buffer(0)
    u = a.union(b).area
    return float(a.intersection(b).area / u) if u > 0 else 0.0


def pick_fires(n=40, seed=0, years=(2017, 2018, 2020, 2021, 2022, 2023), acres=(2500, 30000)) -> pd.DataFrame:
    """MTBS events in dev years with a linked FPA FOD record (the recorded point). Dev years only (protocol section 2)."""
    from . import link_tasks as LT
    T, pairs, X, dec, _ = LT.decide_all("fod_mtbs")
    l = dec[dec.outcome == "link"]
    fod, mt = T["left"], T["right"]
    df = pd.DataFrame({"mid": mt.mid.to_numpy()[l.ri.to_numpy()], "fid": fod.fid.to_numpy()[l.li.to_numpy()], "f_lat": fod.lat.to_numpy()[l.li.to_numpy()],
                       "f_lon": fod.lon.to_numpy()[l.li.to_numpy()], "f_acres": fod.acres.to_numpy()[l.li.to_numpy()]})
    df = df.sort_values("f_acres", ascending=False).drop_duplicates("mid")
    df = df.merge(mt[["mid", "day", "acres", "state", "year", "lat", "lon"]], on="mid", suffixes=("", "_m"))
    df = df[df.year.isin(years) & df.acres.between(*acres)]
    return df.sample(min(n, len(df)), random_state=seed).reset_index(drop=True)


def mtbs_geoms(mids: set) -> dict:
    r = geo._read_shp(paths.RAW / "mtbs" / "mtbs_perimeter_data.zip", "m")
    out = {}
    for sr in r.iterShapeRecords():
        mid = sr.record[0]
        if mid in mids:
            out[mid] = shape(sr.shape.__geo_interface__)
    return out


def run(n=40, out: Path | None = None, seed=0, sensors=("s2", "landsat")):
    from ..caught.scar import make_perimeter
    fires = pick_fires(n, seed)
    G = mtbs_geoms(set(fires.mid))
    rows = []
    for k, f in fires.iterrows():
        t0 = time.time()
        d0 = (pd.Timestamp("1970-01-01") + pd.Timedelta(days=float(f.day))).date()
        end = d0 + timedelta(days=30)
        area_ha = f.f_acres / 2.47105
        truth = to_m(G[f.mid])
        circ = circle_area(f.f_lon, f.f_lat, f.f_acres * 4046.8564224)
        try:
            r = make_perimeter(f.f_lon, f.f_lat, d0, end, area_ha, sensors=sensors)
            geom, status = r.geometry, r.status
            ours = to_m(geom) if geom is not None and not geom.is_empty else None
        except Exception as e:  # keep going: a failure is a result
            ours, status = None, f"error:{type(e).__name__}"
        rows.append({"mid": f.mid, "state": f.state, "year": int(f.year), "acres": f.f_acres, "status": status,
                     "iou_ours": iou(ours, truth) if ours is not None else np.nan, "iou_circle": iou(circ, truth), "seconds": round(time.time() - t0, 1)})
        print(rows[-1], flush=True)
        if out:
            pd.DataFrame(rows).to_csv(out, index=False)
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame, n_boot=2000, seed=0) -> dict:
    ok = df[df.iou_ours.notna()]
    d = (ok.iou_ours - ok.iou_circle).to_numpy()
    cl = (ok.state + "|" + ok.year.astype(str)).to_numpy()
    keys = np.unique(cl)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        s = rng.choice(keys, len(keys))
        boots.append(np.mean(np.concatenate([d[cl == k] for k in s])))
    return {"attempted": int(len(df)), "created": int(len(ok)), "status": df.status.value_counts().to_dict(),
            "iou_ours_mean": float(ok.iou_ours.mean()), "iou_circle_mean_same_fires": float(ok.iou_circle.mean()),
            "iou_circle_mean_all": float(df.iou_circle.mean()), "diff_mean": float(d.mean()),
            "diff_ci": (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))), "n_clusters": int(len(keys))}

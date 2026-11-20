"""Build one fire (or all catalog fires): LANDFIRE rasters, perimeters, arrival raster, weather, meta.

    cd /home/user/wildfireguardiandata && python3 -m firewitness.fuel.fires29.build [id ...]   # default: all in catalog.json
Restartable: existing output files are skipped.
"""
from __future__ import annotations
import datetime as _dt
import json
import shutil
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import mapping
from shapely.ops import unary_union

from ..fetch import lfps
from ..fetch.rawindex import register
from ..grid import Grid, write_tif, read_tif
from . import perimeters as P
from .arrival import arrival_hours, NODATA
from .weather import fetch_weather

LF_NOTE = ("LANDFIRE LF2016 (service Landfire_LF2016/LF2016_{FBFM40,CC,CH}_CONUS, USGS LFPS ImageServer; pre-fire for 2017-2019); "
           "topography (SlpD, Asp) from service Landfire_Topo/LF2020_*_CONUS (LF2020 DEM-derived; topography ignores year)")
LAYERS_LF = {"fbfm40.tif": "FBFM40", "cc.tif": "CC", "ch.tif": "CH", "slope_deg.tif": "SlpD", "aspect.tif": "Asp"}


def rasterize(geom5070, grid: Grid) -> np.ndarray:
    from rasterio import features
    return features.rasterize([(geom5070, 1)], out_shape=grid.shape, transform=grid.transform, fill=0,
                              dtype="uint8").astype(bool)


def build_fire(entry: dict) -> dict:
    fid = entry["id"]
    d = P.RAW / fid
    d.mkdir(parents=True, exist_ok=True)
    fc = P.fetch_perimeters(entry["uid"], entry["layer"])
    per = P.dissolve_by_time(fc)                       # one polygon per distinct perimeter datetime
    times = [t for t, _ in per]
    final4326 = unary_union([g for _, g in per])
    grid = P.aoi_grid(final4326)

    # perimeters.geojson (EPSG:4326, UTC datetime attribute t)
    pj = d / "perimeters.geojson"
    if not pj.exists():
        feats = [{"type": "Feature", "properties": {"t": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "idx": i},
                  "geometry": mapping(g)} for i, (t, g) in enumerate(per)]
        pj.write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
        register(pj, f"{P.BASE}{entry['layer']}/FeatureServer/0/query?where=uniquefireidentifier='{entry['uid']}'",
                 "dissolved per-datetime GeoMAC perimeters, EPSG:4326")

    # LANDFIRE rasters
    for fn, prod in LAYERS_LF.items():
        out = d / fn
        if out.exists():
            continue
        cand = P.RAW / "_candidates" / entry["uid"] / fn
        if prod == "FBFM40" and cand.exists():
            shutil.copy2(cand, out)
            register(out, lfps.service_url("FBFM40", 2016), f"LANDFIRE FBFM40 2016, native 30 m window {grid.bounds()}")
        else:
            lfps.fetch(prod, 2016, grid, out)
        read_tif(out, grid)  # asserts the grid

    # arrival raster
    arr = d / "arrival_hours.tif"
    if not arr.exists():
        masks = [rasterize(P.to_5070(g), grid) for _, g in per]
        hrs = [(t - times[0]).total_seconds() / 3600 for t in times]
        a = arrival_hours(masks, hrs, res=30.0)
        write_tif(arr, a, grid, nodata=NODATA, dtype="float32")

    # weather at final-perimeter centroid
    from pyproj import Transformer
    c5070 = P.to_5070(final4326).centroid
    lon, lat = Transformer.from_crs("EPSG:5070", "EPSG:4326", always_xy=True).transform(c5070.x, c5070.y)
    w = d / "weather.csv"
    d0 = (times[0] - pd.Timedelta(days=1)).date().isoformat()
    d1 = (times[-1] + pd.Timedelta(days=1)).date().isoformat()
    fetch_weather(lat, lon, d0, d1, w)

    meta = dict(id=fid, name=entry["name"], state=entry["state"], year=entry["year"],
                incident_uid=entry["uid"], first_perimeter_utc=times[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
                last_perimeter_utc=times[-1].strftime("%Y-%m-%dT%H:%M:%SZ"), n_perimeters=len(per),
                final_area_km2=round(P.to_5070(final4326).area / 1e6, 3), grid=grid.to_dict(),
                dominant_fuel_group=entry["dominant"], centroid_lonlat=[round(lon, 5), round(lat, 5)],
                weather={"source": "Open-Meteo archive API", "start_date": d0, "end_date": d1},
                sources={"perimeters": f"{P.BASE}{entry['layer']}/FeatureServer/0",
                         "landfire_fbfm40_cc_ch": [lfps.service_url(p, 2016) for p in ("FBFM40", "CC", "CH")],
                         "landfire_topo": [lfps.service_url(p, 2016) for p in ("SlpD", "Asp")],
                         "weather": "https://archive-api.open-meteo.com/v1/archive"},
                landfire_version=LF_NOTE)
    (d / "meta.json").write_text(json.dumps(meta, indent=1))
    return meta


def verify(entry: dict) -> dict:
    """Checks: every raster on the grid, none all-nodata; arrival percentiles and burned share."""
    import rasterio
    d = P.RAW / entry["id"]
    meta = json.loads((d / "meta.json").read_text())
    grid = Grid.from_dict(meta["grid"])
    res = {"id": entry["id"]}
    for fn in list(LAYERS_LF) + ["arrival_hours.tif"]:
        a, nd = read_tif(d / fn, grid)
        valid = (a != nd) if nd is not None else np.ones(a.shape, bool)
        if fn == "arrival_hours.tif":
            v = a[valid]
            res["arr_p5_50_95"] = [round(float(x), 1) for x in np.percentile(v, [5, 50, 95])]
            res["burned_share"] = round(float(valid.mean()), 3)
            res["arr_max_h"] = round(float(v.max()), 1)
            # monotone-looking: arrival should increase with distance from the first-perimeter cells
            from scipy import ndimage
            first0 = (a == 0)
            if first0.any():
                dist = ndimage.distance_transform_edt(~first0)[valid & ~first0]
                res["corr_dist_arrival"] = round(float(np.corrcoef(dist, a[valid & ~first0])[0, 1]), 2)
        else:
            res[fn.split(".")[0] + "_valid"] = round(float(valid.mean()), 3)
            if not valid.any():
                res.setdefault("problems", []).append(f"{fn} all nodata")
    wc = pd.read_csv(d / "weather.csv")
    res["weather_rows"] = len(wc)
    res["weather_nan"] = int(wc.isna().sum().sum())
    return res


def main(argv):
    cat = json.loads((Path(__file__).resolve().parent / "catalog.json").read_text())
    ids = set(argv)
    todo = [e for e in cat if not ids or e["id"] in ids]
    failed = {}

    def run(e):
        for attempt in range(3):
            try:
                build_fire(e)
                print("built", e["id"], flush=True)
                return
            except Exception as ex:  # noqa: BLE001
                failed[e["id"]] = repr(ex)[:300]
                print("FAILED", e["id"], attempt, repr(ex)[:300], flush=True)
        traceback.print_exc()

    with ThreadPoolExecutor(4) as pool:
        list(pool.map(run, todo))
    ok = [e for e in todo if (P.RAW / e["id"] / "meta.json").exists()]
    print(f"{len(ok)}/{len(todo)} built")
    for e in ok:
        print(json.dumps(verify(e)), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])

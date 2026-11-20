"""GeoMAC daily incident perimeters (NIFC ArcGIS, 2017-2019) and shared geometry helpers."""
from __future__ import annotations
import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from ..fetch.rawindex import RAW_ROOT, register
from ..grid import Grid, CRS

HERE = Path(__file__).resolve().parent
RAW = RAW_ROOT / "fires29"
SRC = RAW / "_src"
BASE = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
LAYERS = {2017: "Historic_Geomac_Perimeters_2017", 2018: "Historic_Geomac_Perimeters_2018",
          2019: "Historic_GeoMAC_Perimeters_2019"}
ACRES_PER_KM2 = 247.1053815
CONUS = {"AL", "AR", "AZ", "CA", "CO", "CT", "DE", "FL", "GA", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD",
         "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA",
         "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY"}
UID_RE = re.compile(r"^\d{4}-[A-Za-z0-9]{3,8}-[A-Za-z0-9]+$")


def _get(url, params, retries=5, timeout=180):
    last = None
    for k in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            js = r.json()
            if "error" in js:
                raise RuntimeError(str(js["error"])[:200])
            return js
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (k + 1))
    raise RuntimeError(f"GET {url} failed: {last}")


def _oid_field(year):
    return "objectid" if year == 2019 else "OBJECTID"


def fetch_attribute_table() -> pd.DataFrame:
    """All GeoMAC 2017-2019 perimeter records, attributes only (no geometry). Cached as CSV."""
    path = SRC / "geomac_2017_2019_attributes.csv"
    if path.exists():
        return pd.read_csv(path, keep_default_na=False, na_values=[""], dtype={"state": str, "uniquefireidentifier": str})
    SRC.mkdir(parents=True, exist_ok=True)
    rows = []
    for year, name in LAYERS.items():
        off = 0
        while True:
            js = _get(f"{BASE}{name}/FeatureServer/0/query",
                      {"where": "1=1", "outFields": "*", "returnGeometry": "false", "f": "json",
                       "resultOffset": off, "resultRecordCount": 2000, "orderByFields": _oid_field(year)})
            fs = js["features"]
            for f in fs:
                a = f["attributes"]
                a["layer"] = name
                a["oid"] = a.get("OBJECTID", a.get("objectid"))
                rows.append(a)
            if not fs or not js.get("exceededTransferLimit"):
                break
            off += len(fs)
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    register(path, BASE + "<Historic_Geomac_Perimeters_2017|2018|Historic_GeoMAC_Perimeters_2019>/FeatureServer/0/query",
             "attribute table of all GeoMAC perimeter records, no geometry")
    return df


def fetch_perimeters(uid: str, layer: str) -> dict:
    """All perimeter polygons (EPSG:4326 GeoJSON FeatureCollection) of one incident; cached in RAW/_src/perims."""
    if not UID_RE.match(uid):
        raise ValueError(uid)
    path = SRC / "perims" / f"{uid}.geojson"
    if path.exists():
        return json.loads(path.read_text())
    path.parent.mkdir(parents=True, exist_ok=True)
    feats, off, page = [], 0, 100
    year = int(uid[:4])
    while True:
        js = _get(f"{BASE}{layer}/FeatureServer/0/query",
                  {"where": f"uniquefireidentifier='{uid}'", "outFields": "perimeterdatetime,incidentname,gisacres,state,"
                   "uniquefireidentifier,irwinid,mapmethod,agency", "outSR": 4326, "f": "geojson",
                   "resultOffset": off, "resultRecordCount": page, "orderByFields": _oid_field(year)})
        fs = js.get("features", [])
        feats += fs
        if len(fs) < page:
            break
        off += len(fs)
    fc = {"type": "FeatureCollection", "features": feats}
    path.write_text(json.dumps(fc))
    register(path, f"{BASE}{layer}/FeatureServer/0/query?where=uniquefireidentifier='{uid}'&outSR=4326&f=geojson",
             "GeoMAC perimeters of one incident")
    return fc


def dissolve_by_time(fc: dict):
    """-> list of (UTC pandas Timestamp, shapely geometry EPSG:4326), one per distinct perimeterdatetime, sorted."""
    from shapely.geometry import shape
    from shapely.validation import make_valid
    from shapely.ops import unary_union
    by_t: dict = {}
    for f in fc["features"]:
        ms = f["properties"].get("perimeterdatetime")
        if ms is None or not f.get("geometry"):
            continue
        g = shape(f["geometry"])
        if not g.is_valid:
            g = make_valid(g)
        by_t.setdefault(int(ms), []).append(g)
    out = []
    for ms in sorted(by_t):
        g = unary_union(by_t[ms])
        g = _polys_only(g)
        if g is not None and not g.is_empty:
            out.append((pd.Timestamp(ms, unit="ms", tz="UTC"), g))
    return out


def _polys_only(g):
    from shapely.geometry import MultiPolygon, Polygon
    from shapely.ops import unary_union
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    if g.geom_type == "GeometryCollection":
        ps = [p for p in g.geoms if p.geom_type in ("Polygon", "MultiPolygon")]
        return unary_union(ps) if ps else None
    return None


def to_5070(g):
    from pyproj import Transformer
    from shapely.ops import transform
    t = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    return transform(t.transform, g)


def aoi_grid(final_geom_4326, buffer_m: float = 2000.0) -> Grid:
    """Bounding box of the final perimeter, buffered by 2 km, in EPSG:5070, snapped outward to the LANDFIRE grid."""
    xmin, ymin, xmax, ymax = to_5070(final_geom_4326).bounds
    return Grid.from_bounds(xmin - buffer_m, ymin - buffer_m, xmax + buffer_m, ymax + buffer_m)


def checks_gap(times, max_gap_days=5.0) -> bool:
    t = sorted(set(times))
    return all((b - a).total_seconds() <= max_gap_days * 86400 for a, b in zip(t, t[1:]))

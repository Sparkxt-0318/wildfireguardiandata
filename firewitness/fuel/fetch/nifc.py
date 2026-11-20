"""Fire perimeters (NIFC interagency history, all years) clipped to an area, saved as GeoJSON in EPSG:5070."""
from __future__ import annotations
from pathlib import Path
import json
import time

import requests

from ..grid import Grid
from .rawindex import register

BASE = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
SOURCES = {
    # name: (layer, year expression, kind field, name field, where)
    "hist": ("InterAgencyFirePerimeterHistory_All_Years_View", "FIRE_YEAR_INT", "FEATURE_CA", "INCIDENT",
             "FIRE_YEAR_INT >= {min_year} AND FIRE_YEAR_INT < 2100"),
    "2020s": ("InterAgencyFirePerimeterHistory_2020s_Read_Only", "FIRE_YEAR_INT", "FEATURE_CA", "INCIDENT", "1=1"),
    "wfigs": ("WFIGS_Interagency_Perimeters", None, "attr_IncidentTypeCategory", "poly_IncidentName", "1=1"),
}


def _query(layer: str, where: str, grid: Grid, fields: str):
    xmin, ymin, xmax, ymax = grid.bounds()
    feats, off = [], 0
    while True:
        params = {"where": where, "geometry": f"{xmin},{ymin},{xmax},{ymax}", "geometryType": "esriGeometryEnvelope",
                  "inSR": 5070, "spatialRel": "esriSpatialRelIntersects", "outFields": fields, "outSR": 4326,
                  "f": "geojson", "resultOffset": off, "resultRecordCount": 1000}
        for k in range(5):
            try:
                r = requests.get(BASE + layer + "/FeatureServer/0/query", params=params, timeout=120)
                r.raise_for_status()
                js = r.json()
                if "error" in js:
                    raise RuntimeError(str(js)[:200])
                break
            except Exception:  # noqa: BLE001
                time.sleep(3 * (k + 1))
        else:
            raise RuntimeError("NIFC perimeter fetch failed: " + layer)
        fs = js.get("features", [])
        feats += fs
        if len(fs) < 1 or (len(fs) < 1000 and not js.get("exceededTransferLimit")):
            break
        off += len(fs)
    return feats


def fetch(grid: Grid, out: Path, min_year: int = 1995) -> Path:
    """GeoJSON (EPSG:5070) with YEAR (int), KIND ('WF' wildfire, 'RX' prescribed, 'OT' other), INCIDENT, SRC.
    A fire present in several services is kept once per service; users take the union by year."""
    import geopandas as gpd
    import pandas as pd
    out = Path(out)
    if out.exists():
        return out
    frames = []
    for src, (layer, yexpr, kfield, nfield, where) in SOURCES.items():
        fields = f"{kfield},{nfield}," + (yexpr if yexpr else "attr_FireDiscoveryDateTime,poly_PolygonDateTime")
        feats = _query(layer, where.format(min_year=min_year), grid, fields)
        if not feats:
            continue
        g = gpd.GeoDataFrame.from_features(feats, crs="EPSG:4326").to_crs(5070)
        if yexpr:
            year = pd.to_numeric(g[yexpr], errors="coerce")
        else:
            ms = pd.to_numeric(g["attr_FireDiscoveryDateTime"], errors="coerce").fillna(
                pd.to_numeric(g["poly_PolygonDateTime"], errors="coerce"))
            year = pd.to_datetime(ms, unit="ms", errors="coerce").dt.year
        k = g[kfield].fillna("").str.lower()
        kind = pd.Series("OT", index=g.index)
        kind[k.str.contains("wildfire|^wf")] = "WF"
        kind[k.str.contains("prescribed|^rx")] = "RX"
        frames.append(gpd.GeoDataFrame({"YEAR": year, "KIND": kind, "INCIDENT": g[nfield], "SRC": src},
                                       geometry=g.geometry, crs=5070))
    out.parent.mkdir(parents=True, exist_ok=True)
    if frames:
        gdf = pd.concat(frames, ignore_index=True)
        gdf = gdf[gdf.YEAR.notna() & (gdf.YEAR >= min_year) & (gdf.YEAR < 2100)]
        gdf["YEAR"] = gdf.YEAR.astype(int)
        gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs=5070)
    else:
        gdf = gpd.GeoDataFrame({"YEAR": [], "KIND": [], "INCIDENT": [], "SRC": []}, geometry=[], crs="EPSG:5070")
    gdf.to_file(out, driver="GeoJSON")
    register(out, BASE + " (NIFC history, 2020s, WFIGS)", f"fire perimeters, {len(gdf)} polygons in window")
    return out

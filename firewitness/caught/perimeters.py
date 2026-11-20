"""Agency perimeters (PERIMETER evidence and the C2 truth set) and state boundaries, from public ArcGIS services.

Every page of every query is saved raw under firewitness_raw/perimeters/ and indexed.
"""
from __future__ import annotations

import json
import urllib.parse

import numpy as np
import pandas as pd

from .fetch import RAW_ROOT, fetch

SOURCES = {
    "nifc_hist": {
        "url": "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
               "InterAgencyFirePerimeterHistory_All_Years_View/FeatureServer/0/query",
        "where": "FIRE_YEAR_INT >= {y0} AND FIRE_YEAR_INT <= {y1}",
        "fields": "OBJECTID,IRWINID,INCIDENT,GIS_ACRES,UNQE_FIRE_ID,DATE_CUR,FIRE_YEAR_INT,UNIT_ID,MAP_METHOD,FEATURE_CA,SOURCE,AGENCY,COMMENTS",
    },
    "wfigs": {
        "url": "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/WFIGS_Interagency_Perimeters/FeatureServer/0/query",
        "where": "attr_FireDiscoveryDateTime >= DATE '{y0}-01-01' AND attr_FireDiscoveryDateTime < DATE '{y1p}-01-01'",
        "fields": "OBJECTID,poly_IncidentName,poly_GISAcres,poly_PolygonDateTime,attr_FireDiscoveryDateTime,attr_FireOutDateTime,attr_ContainmentDateTime,attr_IncidentName,attr_IncidentTypeCategory,attr_FinalAcres,attr_IrwinID,attr_POOState",
    },
    "frap_rx": {
        "url": "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/ArcGIS/rest/services/California_Prescribed_Fire_Perimeters_Public/FeatureServer/0/query",
        "where": "YEAR_ >= {y0} AND YEAR_ <= {y1}",
        "fields": "OBJECTID,YEAR_,STATE,AGENCY,UNIT_ID,TREATMENT_ID,TREATMENT_NAME,TREATMENT_TYPE,START_DATE,END_DATE,TREATED_AC,GIS_ACRES",
    },
    "facts_bb": {
        "url": "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_HazardousFuelsTreatments_01/MapServer/15/query",
        "where": "UPPER(activity) LIKE '%BROADCAST%' AND date_completed >= DATE '{y0}-01-01' AND date_completed < DATE '{y1p}-01-01'",
        "fields": "facts_id,activity,activity_code,date_completed,gis_acres,state_abbr,treatment_name",
    },
}
FRAP_YEAR = ("https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/ArcGIS/rest/services/{y}_California_Fire_Perimeters_View/"
             "FeatureServer/0/query")
FRAP_FIELDS = "OBJECTID,YEAR_,STATE,AGENCY,UNIT_ID,FIRE_NAME,INC_NUM,ALARM_DATE,CONT_DATE,CAUSE,OBJECTIVE,GIS_ACRES"
STATES_URL = "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_state_20m.zip"


def _query(name: str, url: str, where: str, fields: str, page: int = 1000):
    import geopandas as gpd

    frames = []
    off = 0
    while True:
        q = {"where": where, "outFields": fields, "outSR": "4326", "f": "geojson", "resultOffset": off,
             "resultRecordCount": page, "returnGeometry": "true", "orderByFields": fields.split(",")[0]}
        full = url + "?" + urllib.parse.urlencode(q)
        p = fetch(full, f"perimeters/{name}/page_{off:07d}.geojson")
        js = json.loads(p.read_text())
        feats = js.get("features", [])
        if "error" in js:
            p.unlink()
            raise RuntimeError(f"{name}: {js['error']}")
        if feats:
            frames.append(gpd.GeoDataFrame.from_features(feats, crs="EPSG:4326"))
        if len(feats) < page and not js.get("exceededTransferLimit") and not js.get("properties", {}).get("exceededTransferLimit"):
            break
        if not feats:
            break
        off += len(feats)
    return pd.concat(frames, ignore_index=True) if frames else None


def _ms(col):
    return pd.to_datetime(col, unit="ms", errors="coerce").dt.date


def load_all(y0: int = 2018, y1: int = 2020):
    """One table of agency polygons: source, src_id, name, area_ac, d0 (start), d1 (end), kind (wildfire/rx)."""
    import geopandas as gpd

    out = RAW_ROOT / "derived_caught" / f"perimeters_{y0}_{y1}.parquet"
    if out.exists():
        return gpd.read_parquet(out)
    parts = []
    for name, s in SOURCES.items():
        g = _query(name, s["url"], s["where"].format(y0=y0, y1=y1, y1p=y1 + 1), s["fields"])
        if g is None:
            continue
        if name == "nifc_hist":
            dc = pd.to_datetime(g["DATE_CUR"].astype(str).str[:8], format="%Y%m%d", errors="coerce").dt.date
            t = pd.DataFrame({"source": name, "src_id": g["OBJECTID"].astype(str), "name": g["INCIDENT"],
                              "area_ac": g["GIS_ACRES"], "d0": [None] * len(g), "d1": dc,
                              "year": g["FIRE_YEAR_INT"], "kind": np.where(g["FEATURE_CA"].astype(str).str.contains(
                                  "Prescribed", case=False, na=False), "rx", "wildfire"),
                              "agency_id": g["IRWINID"]})
        elif name == "wfigs":
            t = pd.DataFrame({"source": name, "src_id": g["OBJECTID"].astype(str), "name": g["attr_IncidentName"],
                              "area_ac": g["poly_GISAcres"], "d0": _ms(g["attr_FireDiscoveryDateTime"]),
                              "d1": _ms(g["attr_ContainmentDateTime"]).fillna(_ms(g["attr_FireOutDateTime"])),
                              "year": pd.to_datetime(g["attr_FireDiscoveryDateTime"], unit="ms").dt.year,
                              "kind": np.where(g["attr_IncidentTypeCategory"].astype(str) == "RX", "rx", "wildfire"),
                              "agency_id": g["attr_IrwinID"]})
        elif name == "frap_rx":
            t = pd.DataFrame({"source": name, "src_id": g["OBJECTID"].astype(str), "name": g["TREATMENT_NAME"],
                              "area_ac": g["GIS_ACRES"], "d0": _ms(g["START_DATE"]), "d1": _ms(g["END_DATE"]),
                              "year": g["YEAR_"], "kind": "rx", "agency_id": g["TREATMENT_ID"]})
        else:  # facts broadcast burns
            t = pd.DataFrame({"source": name, "src_id": g["facts_id"].astype(str), "name": g["treatment_name"],
                              "area_ac": g["gis_acres"], "d0": [None] * len(g), "d1": _ms(g["date_completed"]),
                              "year": pd.to_datetime(g["date_completed"], unit="ms").dt.year, "kind": "rx",
                              "agency_id": g["facts_id"]})
        parts.append(gpd.GeoDataFrame(t, geometry=g.geometry.values, crs="EPSG:4326"))
    for y in range(y0, y1 + 1):
        g = _query(f"frap_{y}", FRAP_YEAR.format(y=y), "1=1", FRAP_FIELDS)
        if g is None:
            continue
        t = pd.DataFrame({"source": "frap", "src_id": f"{y}_" + g["OBJECTID"].astype(str), "name": g["FIRE_NAME"],
                          "area_ac": g["GIS_ACRES"], "d0": _ms(g["ALARM_DATE"]), "d1": _ms(g["CONT_DATE"]),
                          "year": g["YEAR_"], "kind": "wildfire", "agency_id": g["INC_NUM"]})
        parts.append(gpd.GeoDataFrame(t, geometry=g.geometry.values, crs="EPSG:4326"))
    allp = pd.concat(parts, ignore_index=True)
    allp = allp[allp.geometry.notna() & ~allp.geometry.is_empty].reset_index(drop=True)
    allp["geometry"] = allp.geometry.make_valid()
    for c in ("d0", "d1"):
        allp[c] = pd.to_datetime(allp[c], errors="coerce")
    allp["pid"] = allp["source"] + ":" + allp["src_id"].astype(str)
    allp.to_parquet(out)
    return allp


def states():
    import geopandas as gpd
    import zipfile

    z = fetch(STATES_URL, "boundaries/cb_2020_us_state_20m.zip")
    ex = z.parent / "cb_2020_us_state_20m"
    if not ex.exists():
        with zipfile.ZipFile(z) as zf:
            zf.extractall(ex)
    return gpd.read_file(next(ex.glob("*.shp"))).to_crs("EPSG:4326")[["STUSPS", "NAME", "geometry"]]

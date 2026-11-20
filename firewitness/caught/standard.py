"""Standard satellite labels: MODIS and VIIRS active fire (FIRMS archive), MCD64A1 burned area, MTBS.

A record is "standard-labelled" if any of these products has a detection inside its space-time window
(protocol section 4). Footprints are taken as circles of the pixel's half-diagonal, the lenient reading of
"intersects": being lenient here makes the count of fires with no standard label smaller, never larger.
"""
from __future__ import annotations

import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .fetch import RAW_ROOT, fetch, raw_path
from .geo import PointIndex

DERIVED = RAW_ROOT / "derived_caught"


def _derived(name: str) -> Path:
    DERIVED.mkdir(parents=True, exist_ok=True)
    return DERIVED / name


# ---------------------------------------------------------------- FIRMS
FIRMS_WITNESS = {"modis": "MODIS", "viirs-snpp": "VIIRS_SNPP", "viirs-jpss1": "VIIRS_NOAA20"}


def load_firms(years, cfg) -> pd.DataFrame:
    out = _derived(f"firms_{min(years)}_{max(years)}.parquet")
    if out.exists():
        return pd.read_parquet(out)
    fc = cfg["firms"]
    frames = []
    for y in years:
        for prod in fc["products"]:
            for country in fc["countries"]:
                url = fc["url"].format(product=prod, year=y, country=country)
                try:
                    p = fetch(url, f"firms/{prod}_{y}_{country}.csv")
                except FileNotFoundError:
                    continue
                d = pd.read_csv(p)
                d["product"] = prod
                frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    bt = "brightness" if "brightness" in d else "bright_ti4"
    if "bright_ti4" in d:
        d["bt4"] = d["brightness"].fillna(d["bright_ti4"]) if "brightness" in d else d["bright_ti4"]
    else:
        d["bt4"] = d[bt]
    d["acq_dt"] = pd.to_datetime(d["acq_date"] + " " + d["acq_time"].astype(str).str.zfill(4), format="%Y-%m-%d %H%M",
                                 utc=True)
    d["date"] = pd.to_datetime(d["acq_date"]).dt.date
    d["half_m"] = 0.5 * np.hypot(d["scan"], d["track"]) * 1000.0
    d["witness"] = d["product"].map(FIRMS_WITNESS)
    keep = ["latitude", "longitude", "acq_dt", "date", "scan", "track", "half_m", "witness", "confidence", "frp",
            "daynight", "bt4", "type"]
    d = d[[c for c in keep if c in d]].rename(columns={"latitude": "lat", "longitude": "lon"})
    d["confidence"] = d["confidence"].astype(str)
    d.to_parquet(out)
    return d


# ---------------------------------------------------------------- MCD64A1
def _months(years):
    y0, y1 = min(years), max(years)
    d = date(y0 - 1, 12, 1)
    while d <= date(y1 + 1, 1, 1):
        yield d
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def load_mcd64a1(years, cfg) -> pd.DataFrame:
    """Burned pixels (centre lat/lon, burn date, uncertainty days). Tiles are saved raw, then reduced."""
    out = _derived(f"mcd64a1_{min(years)}_{max(years)}.parquet")
    if out.exists():
        return pd.read_parquet(out)
    import planetary_computer as pc
    import pystac_client
    import rasterio
    from pyproj import Transformer

    c = cfg["mcd64a1"]
    cat = pystac_client.Client.open(c["stac"], modifier=pc.sign_inplace)
    items = []
    for m in _months(years):
        nxt = date(m.year + (m.month == 12), m.month % 12 + 1, 1) - timedelta(days=1)
        items += list(cat.search(collections=[c["collection"]], bbox=c["bbox"], datetime=f"{m}/{nxt}").items())

    def one(it):
        rows = []
        bd_p = fetch(it.assets["Burn_Date"].href, f"mcd64a1/{it.id}.Burn_Date.tif")
        un_p = fetch(it.assets["Burn_Date_Uncertainty"].href, f"mcd64a1/{it.id}.Burn_Date_Uncertainty.tif")
        with rasterio.open(bd_p) as s:
            bd = s.read(1)
            tr = s.transform
            crs = s.crs
        with rasterio.open(un_p) as s:
            un = s.read(1)
        r, cc = np.nonzero(bd > 0)
        if not len(r):
            return None
        x, y = rasterio.transform.xy(tr, r, cc)
        lon, lat = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform(np.asarray(x), np.asarray(y))
        year = int(it.id.split(".")[1][1:5])
        dates = pd.to_datetime([f"{year}-01-01"] * len(r)) + pd.to_timedelta(bd[r, cc].astype(int) - 1, unit="D")
        return pd.DataFrame({"lat": lat, "lon": lon, "date": dates.date, "unc_days": un[r, cc].astype(int),
                             "tile": it.id})

    with ThreadPoolExecutor(8) as ex:
        parts = [p for p in ex.map(one, items) if p is not None]
    d = pd.concat(parts, ignore_index=True).drop_duplicates(["lat", "lon", "date"])
    d["half_m"] = 0.5 * 463.3127 * np.sqrt(2)
    d["witness"] = "MCD64A1"
    d.to_parquet(out)
    return d


# ---------------------------------------------------------------- MTBS
def load_mtbs(cfg):
    import geopandas as gpd

    out = _derived("mtbs_perims.parquet")
    if out.exists():
        return gpd.read_parquet(out)
    z = fetch(cfg["mtbs"]["url"], cfg["mtbs"]["raw_rel"])
    ex = z.parent / "extracted"
    if not ex.exists():
        with zipfile.ZipFile(z) as zf:
            zf.extractall(ex)
    shp = sorted(ex.rglob("*.shp"))[0]
    g = gpd.read_file(shp).to_crs("EPSG:4326")
    g.columns = [c.lower() if c != "geometry" else c for c in g.columns]
    g["ig_date"] = pd.to_datetime(g["ig_date"]).dt.date
    g = g.rename(columns={"event_id": "Event_ID", "incid_name": "Incid_Name", "incid_type": "Incid_Type",
                          "burnbndac": "BurnBndAc"})
    g = g[["Event_ID", "Incid_Name", "Incid_Type", "BurnBndAc", "ig_date", "geometry"]]
    g.to_parquet(out)
    return g


# ---------------------------------------------------------------- polygons vs discs
def local_crs(lat: float, lon: float) -> str:
    return f"+proj=aeqd +lat_0={lat:.5f} +lon_0={lon:.5f} +datum=WGS84 +units=m"


class PolygonIndex:
    """Polygons with a date interval; query: does a polygon meet the disc (lat, lon, r) within [t0, t1]?"""

    def __init__(self, gdf, d0_col, d1_col, id_col):
        from shapely.strtree import STRtree

        self.g = gdf.reset_index(drop=True)
        self.d0 = np.asarray(pd.to_datetime(self.g[d0_col]).values, dtype="datetime64[D]")
        self.d1 = np.asarray(pd.to_datetime(self.g[d1_col]).values, dtype="datetime64[D]")
        self.ids = self.g[id_col].astype(str).values
        self.tree = STRtree(self.g.geometry.values)

    def query(self, lat, lon, r_m, t0, t1):
        from pyproj import Transformer
        from shapely.geometry import Point
        from shapely.ops import transform

        deg = r_m / 111_000.0 * 2 + 0.01
        cand = self.tree.query(Point(lon, lat).buffer(deg))
        if not len(cand):
            return []
        t0 = np.datetime64(t0, "D")
        t1 = np.datetime64(t1, "D")
        cand = [i for i in cand if self.d0[i] <= t1 and self.d1[i] >= t0]
        if not cand:
            return []
        tr = Transformer.from_crs("EPSG:4326", local_crs(lat, lon), always_xy=True).transform
        disc = Point(0, 0).buffer(r_m, 32)
        return [self.ids[i] for i in cand if transform(tr, self.g.geometry.values[i]).intersects(disc)]


# ---------------------------------------------------------------- the join
def standard_join(rec: pd.DataFrame, cfg, years) -> pd.DataFrame:
    """Per record: count of agreeing detections per standard product, and std_any."""
    firms = load_firms(years, cfg)
    mcd = load_mcd64a1(years, cfg)
    mtbs = load_mtbs(cfg)
    out = pd.DataFrame(index=rec.index)
    for w in ["MODIS", "VIIRS_SNPP", "VIIRS_NOAA20"]:
        f = firms[firms.witness == w]
        idx = PointIndex(f.lat, f.lon, f.half_m, f.date, f.date)
        out[f"std_{w}"] = [len(idx.query(a, b, r, t0, t1)) for a, b, r, t0, t1 in
                           zip(rec.LATITUDE, rec.LONGITUDE, rec.r_m, rec.t0, rec.t1)]
    unc = np.maximum(mcd.unc_days.values, 1)
    d = pd.to_datetime(mcd.date)
    idx = PointIndex(mcd.lat, mcd.lon, mcd.half_m, (d - pd.to_timedelta(unc, "D")).values,
                     (d + pd.to_timedelta(unc, "D")).values)
    out["std_MCD64A1"] = [len(idx.query(a, b, r, t0, t1)) for a, b, r, t0, t1 in
                          zip(rec.LATITUDE, rec.LONGITUDE, rec.r_m, rec.t0, rec.t1)]
    m = mtbs.copy()
    m["d1"] = pd.to_datetime(m.ig_date) + pd.to_timedelta(1, "D")
    m["d0"] = pd.to_datetime(m.ig_date) - pd.to_timedelta(1, "D")
    pidx = PolygonIndex(m, "d0", "d1", "Event_ID")
    out["std_MTBS"] = [len(pidx.query(a, b, r, t0, t1)) for a, b, r, t0, t1 in
                       zip(rec.LATITUDE, rec.LONGITUDE, rec.r_m, rec.t0, rec.t1)]
    cols = [c for c in out if c.startswith("std_")]
    out["std_any"] = (out[cols] > 0).any(axis=1)
    return out

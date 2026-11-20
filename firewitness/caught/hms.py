"""NOAA Hazard Mapping System: GOES (FDC, ABBA), AVHRR (FIMMA) and analyst fire points; analyst smoke polygons.

MODIS and VIIRS points in HMS duplicate the FIRMS standard products and are not used from here.
"""
from __future__ import annotations

import gzip
import zipfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .fetch import RAW_ROOT, fetch, index_note
from .floor import pixel_area_m2

BASE = "https://satepsanone.nesdis.noaa.gov/pub/FIRE/web/HMS"


def _days(y0, y1):
    d = date(y0, 1, 1) - timedelta(days=1)
    while d <= date(y1, 12, 31) + timedelta(days=1):
        yield d
        d += timedelta(days=1)


def _read_txt(p: Path) -> str:
    b = p.read_bytes()
    if b[:2] == b"\x1f\x8b":
        b = gzip.decompress(b)
    return b.decode("latin1")


def goes_vza(lat, lon, sub_lon):
    """View zenith angle of a geostationary satellite at sub_lon (deg)."""
    la = np.radians(lat)
    dl = np.radians(np.asarray(lon) - sub_lon)
    cosg = np.cos(la) * np.cos(dl)
    r, R = 42164.0, 6378.0
    d = np.sqrt(r * r + R * R - 2 * r * R * cosg)
    sing = np.sqrt(1 - cosg ** 2)
    return np.degrees(np.arcsin(np.clip(r * sing / d, 0, 1)))


def load_fire(y0: int, y1: int, bbox=(-180, 17.5, -64.0, 72.0)) -> pd.DataFrame:
    out = RAW_ROOT / "derived_caught" / f"hms_fire_{y0}_{y1}.parquet"
    if out.exists():
        return pd.read_parquet(out)
    rows = []
    for d in _days(y0, y1):
        try:
            p = fetch(f"{BASE}/Fire_Points/Text/{d:%Y}/{d:%m}/hms_fire{d:%Y%m%d}.txt", f"hms/fire/hms_fire{d:%Y%m%d}.txt")
        except FileNotFoundError:
            continue
        for line in _read_txt(p).splitlines()[1:]:
            q = [x.strip() for x in line.split(",")]
            if len(q) < 6:
                continue
            try:
                lon, lat = float(q[0]), float(q[1])
            except ValueError:
                continue
            if not (bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]):
                continue
            rows.append((lon, lat, q[2], q[3], q[4].upper(), q[5].upper()))
    d = pd.DataFrame(rows, columns=["lon", "lat", "yday", "hhmm", "sat", "method"])
    d = d[~d.method.isin(["MODIS", "VIIRS"])].copy()
    d["date"] = pd.to_datetime(d.yday, format="%Y%j", errors="coerce").dt.date
    d = d.dropna(subset=["date"])

    def wit(r):
        if r.method == "ANALYSIS":
            return "HMS_ANALYST"
        if r.sat.startswith("GOES"):
            return "GOES"
        if r.sat.startswith("AVHRR") or r.method == "FIMMA":
            return "AVHRR"
        return "HMS_OTHER"

    d["witness"] = [wit(r) for r in d.itertuples()]
    east = d.sat.str.startswith("GOES-EAST")
    sub = np.where(east, -75.2, np.where(pd.to_datetime(d.date) < pd.Timestamp("2019-02-12"), -135.0, -137.2))
    vza = goes_vza(d.lat.values, d.lon.values, sub)
    area = np.array([pixel_area_m2("GOES", min(v, 80.0)) for v in vza])
    half = np.where(d.witness == "GOES", 0.75 * np.sqrt(area),
                    np.where(d.witness == "AVHRR", 1500.0, 1000.0))
    d["half_m"] = half
    d.to_parquet(out)
    return d


def load_smoke(y0: int, y1: int):
    """Daily analyst smoke polygons with area (km2)."""
    import geopandas as gpd

    out = RAW_ROOT / "derived_caught" / f"hms_smoke_{y0}_{y1}.parquet"
    if out.exists():
        return gpd.read_parquet(out)
    parts = []
    for d in _days(y0, y1):
        try:
            z = fetch(f"{BASE}/Smoke_Polygons/Shapefile/{d:%Y}/{d:%m}/hms_smoke{d:%Y%m%d}.zip",
                      f"hms/smoke/hms_smoke{d:%Y%m%d}.zip")
        except FileNotFoundError:
            continue
        try:
            g = gpd.read_file(f"zip://{z}")
        except Exception:
            continue
        if g.empty:
            continue
        if g.crs is None:
            g = g.set_crs("EPSG:4326")
        g = g.to_crs("EPSG:4326")
        g["date"] = d
        g["density"] = g["Density"] if "Density" in g else None
        parts.append(g[["date", "density", "geometry"]])
    g = pd.concat(parts, ignore_index=True)
    g = gpd.GeoDataFrame(g, crs="EPSG:4326")
    g["geometry"] = g.geometry.make_valid()
    g["area_km2"] = g.to_crs("EPSG:6933").area / 1e6
    g.to_parquet(out)
    return g

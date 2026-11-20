"""Independent spatial evidence: administrative areas, satellite detections, burn scars.

Everything here is a lookup against data that the repair rules did not write: Census county and state
polygons, NASA FIRMS (MODIS, VIIRS) detections, MTBS burned-area perimeters.
"""
from __future__ import annotations

import re
from functools import lru_cache

import numpy as np
import pandas as pd
import shapefile  # pyshp
import shapely
from scipy.spatial import cKDTree
from shapely.geometry import shape
from shapely.strtree import STRtree

from . import paths
from ..core import load_region

EARTH_KM = 6371.0088


def xyz(lat, lon):
    la, lo = np.radians(np.asarray(lat, float)), np.radians(np.asarray(lon, float))
    return np.column_stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])


def km_to_chord(km):
    return 2 * np.sin(np.asarray(km) / (2 * EARTH_KM))


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(a))


def _read_shp(zip_path, name):
    import zipfile, io
    z = zipfile.ZipFile(zip_path)
    base = [n for n in z.namelist() if n.endswith(".shp")][0][:-4]
    r = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), shx=io.BytesIO(z.read(base + ".shx")),
                         dbf=io.BytesIO(z.read(base + ".dbf")))
    return r


class Admin:
    """Counties and states with vectorised point lookup."""

    def __init__(self, cfg=None):
        cfg = cfg or load_region(paths.REPO / "firewitness" / "records", "us")
        self.fips_to_abbr = {v: k for k, v in cfg["state_fips"].items()}
        self.abbr_to_fips = cfg["state_fips"]
        r = _read_shp(paths.RAW / "census" / "cb_2020_us_county_500k.zip", "county")
        fields = [f[0] for f in r.fields[1:]]
        geoms, recs = [], []
        for sr in r.iterShapeRecords():
            geoms.append(shape(sr.shape.__geo_interface__))
            recs.append(dict(zip(fields, sr.record)))
        self.county = pd.DataFrame(recs)
        self.county["geom"] = geoms
        self.county["state_abbr"] = self.county["STATEFP"].map(self.fips_to_abbr)
        self.county["norm"] = self.county["NAME"].map(norm_county)
        self.tree = STRtree(geoms)
        self.geoms = np.array(geoms, dtype=object)
        self.by_state_name = {}
        for i, row in self.county.iterrows():
            self.by_state_name.setdefault((row["state_abbr"], row["norm"]), []).append(i)
        self.by_fips = {row["GEOID"]: i for i, row in self.county.iterrows()}

    def locate(self, lat, lon):
        """County row index for each point, -1 where outside every county (water, abroad)."""
        pts = shapely.points(np.asarray(lon, float), np.asarray(lat, float))
        ok = np.isfinite(lat) & np.isfinite(lon)
        idx = np.full(len(pts), -1, dtype=int)
        if ok.any():
            q, t = self.tree.query(pts[ok], predicate="intersects")
            sel = np.flatnonzero(ok)
            idx[sel[q]] = t
        return idx

    def locate_near(self, lat, lon, tol_km=5.0):
        """Like locate but a point within tol_km of a county counts (coastal points, rounding)."""
        idx = self.locate(lat, lon)
        miss = np.flatnonzero((idx < 0) & np.isfinite(lat) & np.isfinite(lon))
        if len(miss):
            deg = tol_km / 111.0
            pts = shapely.points(np.asarray(lon, float)[miss], np.asarray(lat, float)[miss])
            q, t = self.tree.query(pts, predicate="dwithin", distance=deg)
            # first hit per point
            seen = set()
            for a, b in zip(q, t):
                if a not in seen:
                    idx[miss[a]] = b
                    seen.add(a)
        return idx


_SPLIT = re.compile(r"\s*(?:,|;|/|&|\band\b|\+)\s*", re.I)


def norm_county(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\b(county|parish|borough|census area|city and borough|municipality)\b", "", s)
    s = s.replace("saint ", "st ").replace("st. ", "st ").replace(".", "").replace("'", "")
    return re.sub(r"[^a-z ]", "", s).strip()


def county_names(raw) -> list[str]:
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return []
    return [n for n in (norm_county(x) for x in _SPLIT.split(str(raw))) if n]


class Detections:
    """FIRMS detections (MODIS 2000-, VIIRS 2012-) as a KD-tree with day numbers."""

    def __init__(self, years=None):
        frames = []
        for f in sorted((paths.RAW / "firms").glob("*_United_States.csv")):
            y = int(f.name.split("_")[1])
            if years and y not in years:
                continue
            d = pd.read_csv(f, usecols=["latitude", "longitude", "acq_date"], dtype={"latitude": "float32", "longitude": "float32"})
            d["day"] = (pd.to_datetime(d["acq_date"]).astype("datetime64[D]").astype("int64")).astype("int32") if False else \
                (pd.to_datetime(d["acq_date"]) - pd.Timestamp("1970-01-01")).dt.days.astype("int32")
            frames.append(d[["latitude", "longitude", "day"]])
        d = pd.concat(frames, ignore_index=True)
        self.lat = d["latitude"].to_numpy(np.float32)
        self.lon = d["longitude"].to_numpy(np.float32)
        self.day = d["day"].to_numpy(np.int32)
        self.tree = cKDTree(xyz(self.lat, self.lon))
        self.n = len(d)

    @classmethod
    def from_arrays(cls, lat, lon, day):
        o = cls.__new__(cls)
        o.lat, o.lon, o.day = np.asarray(lat, np.float32), np.asarray(lon, np.float32), np.asarray(day, np.int32)
        ok = np.isfinite(o.lat) & np.isfinite(o.lon)
        o.lat, o.lon, o.day = o.lat[ok], o.lon[ok], o.day[ok]
        o.tree = cKDTree(xyz(o.lat, o.lon))
        o.n = len(o.lat)
        return o

    def window_stats(self, lat, lon, day0, day1, radius_km=5.0):
        """For each point: number of detections within radius and days [day0, day1], and first detection day (or -1)."""
        lat, lon = np.asarray(lat, float), np.asarray(lon, float)
        n = len(lat)
        cnt = np.zeros(n, int)
        first = np.full(n, -1, int)
        ok = np.flatnonzero(np.isfinite(lat) & np.isfinite(lon) & (day0 > -10**8))
        if not len(ok):
            return cnt, first
        lists = self.tree.query_ball_point(xyz(lat[ok], lon[ok]), km_to_chord(radius_km), workers=4)
        for k, hits in zip(ok, lists):
            if not hits:
                continue
            h = np.asarray(hits)
            dd = self.day[h]
            m = (dd >= day0[k]) & (dd <= day1[k])
            c = int(m.sum())
            if c:
                cnt[k] = c
                first[k] = int(dd[m].min())
        return cnt, first


class Scars:
    """MTBS burned-area perimeters with ignition date; contains/near test restricted to a date window."""

    def __init__(self):
        r = _read_shp(paths.RAW / "mtbs" / "mtbs_perimeter_data.zip", "mtbs")
        fields = [f[0] for f in r.fields[1:]]
        geoms, recs = [], []
        for sr in r.iterShapeRecords():
            try:
                g = shape(sr.shape.__geo_interface__)
            except Exception:
                continue
            geoms.append(g)
            recs.append(dict(zip(fields, sr.record)))
        self.df = pd.DataFrame(recs)
        self.geoms = np.array(geoms, dtype=object)
        self.tree = STRtree(self.geoms)
        ig = pd.to_datetime(self.df["ig_date"], errors="coerce")
        self.ig_day = ((ig - pd.Timestamp("1970-01-01")).dt.days).fillna(-10**9).to_numpy()

    def near(self, lat, lon, day, tol_km=1.0, win=30):
        """True where some scar with ignition within +-win days of `day` lies within tol_km of the point."""
        lat, lon, day = np.asarray(lat, float), np.asarray(lon, float), np.asarray(day, float)
        out = np.zeros(len(lat), bool)
        ok = np.flatnonzero(np.isfinite(lat) & np.isfinite(lon) & np.isfinite(day))
        if not len(ok):
            return out
        pts = shapely.points(lon[ok], lat[ok])
        q, t = self.tree.query(pts, predicate="dwithin", distance=tol_km / 111.0)
        good = np.abs(self.ig_day[t] - day[ok][q]) <= win
        out[ok[q[good]]] = True
        return out

"""Tool 5: coverage. Which large fires have no mapped perimeter, which fires are seen only by satellites.

* A fire of at least `perimeter_min_acres` is "covered" if it is linked to an MTBS event or lies inside an
  interagency (WFIGS) perimeter of the same fire year.
* coverage flags are published per state, year and agency.
* satellite-only candidates: groups of FIRMS detections (several days, many hits, not a persistent heat source)
  with no recorded fire within 10 km and 10 days. They are candidates, never confirmed fires.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import shapely
from scipy.spatial import cKDTree
from shapely.geometry import shape
from shapely.strtree import STRtree

from . import geo, paths


def load_wfigs_perimeters():
    geoms, rows = [], []
    with open(paths.RAW / "wfigs" / "WFIGS_Interagency_Perimeters_ge500ac.ndjson", encoding="utf-8") as fh:
        for line in fh:
            ft = json.loads(line)
            if not ft.get("geometry"):
                continue
            try:
                g = shape(ft["geometry"])
            except Exception:
                continue
            if g.is_empty:
                continue
            geoms.append(g)
            pr = ft["properties"]
            rows.append({"name": pr.get("poly_IncidentName"), "acres": pr.get("poly_GISAcres"), "t": pr.get("poly_PolygonDateTime"), "irwin": pr.get("attr_IrwinID") or pr.get("poly_IRWINID")})
    df = pd.DataFrame(rows)
    df["year"] = pd.to_datetime(df["t"], unit="ms", errors="coerce").dt.year
    return df, np.array(geoms, dtype=object)


def in_perimeter(lat, lon, year, wf_df, wf_geoms, tree=None) -> np.ndarray:
    """True where the point lies inside a WFIGS perimeter whose polygon year is within +-1 of the fire year."""
    tree = tree or STRtree(wf_geoms)
    pts = shapely.points(np.asarray(lon, float), np.asarray(lat, float))
    q, t = tree.query(pts, predicate="intersects")
    py = wf_df["year"].to_numpy()[t]
    ok = np.abs(py - np.asarray(year)[q]) <= 1
    out = np.zeros(len(pts), bool)
    out[q[ok]] = True
    return out


def coverage_flags(fod: pd.DataFrame, covered: np.ndarray, min_acres: float = 1000.0) -> pd.DataFrame:
    big = fod.acres >= min_acres
    d = fod[big].assign(covered=covered[big.to_numpy()])
    g = d.groupby(["state", "year", "agency"]).agg(n_large=("fid", "size"), n_covered=("covered", "sum")).reset_index()
    g["share_covered"] = g.n_covered / g.n_large
    g["flag"] = np.where(g.n_covered == 0, "no_perimeters", np.where(g.share_covered < 0.5, "low", "ok"))
    return g


def satellite_only(records: pd.DataFrame, years, min_det=8, min_days=2, cell_deg=0.02, near_km=10.0, near_days=10) -> pd.DataFrame:
    """Candidate fires seen only by satellites. records: lat, lon, day of every recorded fire (any source)."""
    from .geo import Detections
    out = []
    rec_tree = cKDTree(geo.xyz(records.lat.to_numpy(), records.lon.to_numpy()))
    rday = records.day.to_numpy()
    for y in years:
        det = Detections(years=[y])
        d = pd.DataFrame({"lat": det.lat, "lon": det.lon, "day": det.day})
        d["cy"] = np.floor(d.lat / cell_deg).astype(int); d["cx"] = np.floor(d.lon / cell_deg).astype(int)
        g = d.groupby(["cy", "cx"]).agg(n=("day", "size"), d0=("day", "min"), d1=("day", "max"), lat=("lat", "mean"), lon=("lon", "mean")).reset_index()
        g = g[(g.n >= min_det) & ((g.d1 - g.d0) >= min_days) & ((g.d1 - g.d0) <= 60)]
        # persistent heat sources: the same cell burning in other years is not a fire
        g["year"] = y
        out.append(g)
    cand = pd.concat(out, ignore_index=True)
    persist = cand.groupby(["cy", "cx"])["year"].transform("nunique")
    cand = cand[persist <= 1].reset_index(drop=True)
    hits = rec_tree.query_ball_point(geo.xyz(cand.lat.to_numpy(), cand.lon.to_numpy()), geo.km_to_chord(near_km))
    near = np.array([bool(h) and bool((np.abs(rday[h] - cand.d0.iloc[i]) <= near_days + (cand.d1.iloc[i] - cand.d0.iloc[i])).any()) for i, h in enumerate(hits)])
    return cand[~near].reset_index(drop=True)

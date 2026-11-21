"""v0.3 gazetteer radii by place type (protocol v0.3 section 3).

The v0.2 matcher is unchanged; the radius of a match is looked up from a table fitted on dev incidents only
(90th percentile of the matched-point-to-known-point distance per place type x offset cell) and frozen before the sealed incidents are scored.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from . import eval_published as E, gazetteer as G, geo, locate, paths

RADII_JSON = paths.RESULTS / "data" / "v03_gazetteer_radii.json"
MIN_CELL = 30


def bucket(number, year) -> int:
    return int(hashlib.sha256(f"v03|{number}|{year}".encode()).hexdigest(), 16) % 10


def pool() -> pd.DataFrame:
    """All incidents with a place description and a published point (outside the v0.1 sealed test years), with their split."""
    raw = pd.read_parquet(paths.CANON / "ics_raw_all.parquet").reset_index(drop=True)
    lat, lon, _ = locate.parse_latlon(raw)
    raw["lat0"], raw["lon0"] = lat, lon
    raw["year"] = pd.to_datetime(raw.start_raw, errors="coerce", format="mixed").dt.year.astype("Int64").astype(str)
    pub = E.load_published()
    pub = pub[~pub.year.isin(E.TEST)]
    leg = raw[(raw.src != "ics209_2014") & ~raw.year.isin(E.TEST)]
    g = leg.sort_values("rid").groupby(["number", "year"]).agg(lat0=("lat0", "first"), lon0=("lon0", "first"), state=("state", "first"),
                                                              county=("county", "first"), desc=("location_desc", "first")).reset_index()
    m = pub.merge(g, on=["number", "year"], how="inner")
    m = m[(m.lat_c != 0) & m.lat_c.notna() & m.desc.notna()].copy()
    m["raw_missing"] = ~((m.lat0.abs() > 1) & (m.lon0.abs() > 1))
    m["bucket"] = [bucket(a, b) for a, b in zip(m.number, m.year)]
    m["split"] = np.where(m.raw_missing | (m.bucket >= 3), "dev", "sealed")
    return m.reset_index(drop=True)


def match_all(Gz, df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        cn = [c.strip() for c in str(r.county).split(",")] if isinstance(r.county, str) and r.county.strip() else []
        st = r.state if isinstance(r.state, str) and len(r.state) == 2 else None
        x = Gz.match(r.desc, st, cn)
        x["number"], x["year"], x["lat_c"], x["long_c"] = r.number, r.year, r.lat_c, r.long_c
        if x["match_class"] == "matched":
            x["dist_to_known_km"] = float(geo.haversine_km(x["lat_gaz"], x["lon_gaz"], r.lat_c, r.long_c))
        rows.append(x)
    return pd.DataFrame(rows)


def fit_radii(dev_matched: pd.DataFrame) -> dict:
    d = dev_matched[dev_matched.match_class == "matched"].copy()
    d["cell"] = d.place_type + "|" + np.where(d.offset_applied, "offset", "no offset")

    def q90(x):
        return float(np.ceil(np.quantile(x, 0.9) * 2.0) / 2.0)

    cells = {}
    for c, g in d.groupby("cell"):
        if len(g) >= MIN_CELL:
            cells[c] = {"n_dev": int(len(g)), "radius_km": q90(g.dist_to_known_km), "pooled": False}
    pooled = q90(d.dist_to_known_km)
    return {"quantile": 0.9, "min_cell": MIN_CELL, "pooled_radius_km": pooled, "n_dev_matched": int(len(d)), "cells": cells,
            "cells_below_min_use_pooled": sorted(set(d.cell) - set(cells))}


def radius_for(radii: dict, place_type: str, offset_applied: bool) -> float:
    c = f"{place_type}|{'offset' if offset_applied else 'no offset'}"
    return radii["cells"].get(c, {}).get("radius_km", radii["pooled_radius_km"])


def coverage(matched: pd.DataFrame, radii: dict) -> dict:
    from .gates import wilson
    m = matched[matched.match_class == "matched"].copy()
    m["r"] = [radius_for(radii, a, b) for a, b in zip(m.place_type, m.offset_applied)]
    m["inside"] = m.dist_to_known_km <= m.r
    m["cell"] = m.place_type + "|" + np.where(m.offset_applied, "offset", "no offset")
    k, n = int(m.inside.sum()), int(len(m))
    out = {"matched": n, "inside": k, "coverage": k / max(n, 1), "ci": wilson(k, max(n, 1)), "median_radius_km": float(m.r.median()) if n else None,
           "by_cell": {c: {"n": int(len(g)), "inside": int(g.inside.sum()), "ci": wilson(int(g.inside.sum()), len(g))} for c, g in m.groupby("cell")}}
    return out

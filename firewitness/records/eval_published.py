"""Score tool 2 (location) against the hand cleaning published with ICS-209-PLUS, on dev years only.

The published files are read here, by the scorer, never by the rules.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import geo, locate, paths

TEST = {"1995", "2001", "2007", "2013", "2019"}


def load_published() -> pd.DataFrame:
    B = paths.ICS_SRC.parent / "latlong_clean"
    pub = pd.concat([pd.read_csv(B / f, dtype=str, encoding="latin-1") for f in ["legacy_cleaned_ll-fod.csv", "historical_cleaned_ll-fod.csv"]]).rename(columns={"FIRE_EVENT_ID": "eid"})
    pub[["number", "year", "ord"]] = pub.eid.str.split("|", n=2, expand=True)
    for c in ["lat_c", "long_c"]:
        pub[c] = pd.to_numeric(pub[c], errors="coerce")
    return pub


def score(raw: pd.DataFrame, dec: pd.DataFrame, split_years_excluded=TEST) -> dict:
    """raw: canonical raw frame (aligned to dec); dec: location decisions."""
    pub = load_published()
    pub = pub[~pub.year.isin(split_years_excluded)]
    r = raw.reset_index(drop=True).join(dec[["action", "alt_kind", "alt_lat", "alt_lon"]])
    lat, lon, _ = locate.parse_latlon(r)
    r["lat0"], r["lon0"] = lat, lon
    r["lat1"] = np.where(r.action == "repair", r.alt_lat, r.lat0)
    r["lon1"] = np.where(r.action == "repair", r.alt_lon, r.lon0)
    r["year"] = pd.to_datetime(r.start_raw, errors="coerce", format="mixed").dt.year.astype("Int64").astype(str)
    leg = r[(r.src != "ics209_2014") & ~r.year.isin(split_years_excluded)]
    g = leg.sort_values("rid").groupby(["number", "year"]).agg(lat0=("lat0", "first"), lon0=("lon0", "first"), lat1=("lat1", "first"), lon1=("lon1", "first"), action=("action", "first"), kind=("alt_kind", "first")).reset_index()
    m = pub.merge(g, on=["number", "year"], how="inner")
    res = m[(m.lat_c != 0) & m.lat_c.notna()].copy()
    res["raw_missing"] = ~((res.lat0.abs() > 1) & (res.lon0.abs() > 1))
    res["d_raw"] = geo.haversine_km(res.lat0, -res.lon0.abs(), res.lat_c, res.long_c)
    res["d_our"] = geo.haversine_km(res.lat1, res.lon1, res.lat_c, res.long_c)
    err = res[(res.d_raw >= 5) & ~res.raw_missing]
    rep = err[err.action == "repair"]
    good = rep[rep.d_our < 5]
    return {"documented_wrong_present": int(len(err)), "flagged": int(err.action.isin(["repair", "undecided"]).sum()),
            "repaired": int(len(rep)), "repaired_within_5km": int(len(good)),
            "precision_of_repairs": float(len(good) / max(len(rep), 1)),
            "by_kind": {k: f"{int((v.d_our < 5).sum())}/{len(v)}" for k, v in rep.groupby("kind")},
            "undecided": int((err.action == "undecided").sum()), "kept": int((err.action == "keep").sum())}

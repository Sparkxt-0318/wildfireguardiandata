"""v0.2 tool: place-name gazetteer for incidents with missing coordinates (protocol v0.2 section 3).

Source: USGS GNIS Domestic Names. A description like "5 miles NE of Sumatra, FL" gives a place and an offset. A match
gets an uncertainty radius; nothing is written when the place is ambiguous or unknown, and never over an existing coordinate.
"""
from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd

from . import geo, paths

DIRS = {"N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5, "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5, "S": 180, "SSW": 202.5,
        "SW": 225, "WSW": 247.5, "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5,
        "NORTH": 0, "NORTHEAST": 45, "EAST": 90, "SOUTHEAST": 135, "SOUTH": 180, "SOUTHWEST": 225, "WEST": 270, "NORTHWEST": 315,
        "NORTH-EAST": 45, "NORTH-WEST": 315, "SOUTH-EAST": 135, "SOUTH-WEST": 225}
NUMW = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15, "twenty": 20}
STATE_RE = r"(?:,?\s*(?:[A-Z]{2}|[A-Za-z]+))?"
OFFSET = re.compile(r"(?P<d>\d+(?:\.\d+)?|a|one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty)\s*(?P<u>mi(?:les?)?\.?|km|kilometers?)?\s*(?P<dir>[NSEW]{1,3}|north-?east|north-?west|south-?east|south-?west|north|south|east|west)\s+(?:of|from)\s+(?P<place>[^,;()]+)", re.I)
DIRONLY = re.compile(r"(?P<dir>[NSEW]{1,3}|northeast|northwest|southeast|southwest|north|south|east|west)\s+(?:of|from)\s+(?P<place>[^,;()]+)", re.I)


def norm(s: str) -> str:
    s = (s if isinstance(s, str) else "").lower()
    s = re.sub(r"\b(mt\.?|mount)\b", "mount", s)
    s = re.sub(r"\b(st\.?|saint)\b", "saint", s)
    s = re.sub(r"\b(ft\.?|fort)\b", "fort", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse(desc: str):
    """-> (place, distance_km or None, bearing or None)."""
    if not isinstance(desc, str) or not desc.strip():
        return None, None, None
    m = OFFSET.search(desc)
    if m:
        d = m.group("d").lower()
        dist = float(NUMW.get(d, d)) if not d.replace(".", "").isdigit() else float(d)
        unit = (m.group("u") or "mi").lower()
        km = dist * (1.0 if unit.startswith(("km", "kilo")) else 1.609344)
        return m.group("place").strip(), km, DIRS.get(m.group("dir").upper().replace(" ", ""), None)
    m = DIRONLY.search(desc)
    if m:
        return m.group("place").strip(), None, DIRS.get(m.group("dir").upper())
    first = re.split(r"[,;(]", desc)[0].strip()
    return (first or None), None, None


class Gazetteer:
    def __init__(self, cfg):
        t = pd.read_csv(paths.WORK / "gnis" / "Text" / "DomesticNames_National.txt", sep="|", dtype=str, encoding="utf-8-sig",
                        usecols=["feature_name", "feature_class", "state_numeric", "county_name", "prim_lat_dec", "prim_long_dec"])
        t["lat"], t["lon"] = pd.to_numeric(t.prim_lat_dec, errors="coerce"), pd.to_numeric(t.prim_long_dec, errors="coerce")
        t = t.dropna(subset=["lat", "lon"])
        t["key"] = t.feature_name.map(norm)
        self.fips_to_abbr = {v: k for k, v in cfg["state_fips"].items()}
        t["st"] = t.state_numeric.map(self.fips_to_abbr)
        self.t = t[["key", "st", "county_name", "feature_class", "lat", "lon"]]
        self.idx = {k: g for k, g in self.t.groupby(["st", "key"])}

    def match(self, desc, state, counties=()):
        place, dist_km, bearing = parse(desc)
        out = {"match_class": "unmatched", "place": place, "dist_km": dist_km, "bearing": bearing}
        if not place or not state:
            return out
        key = norm(place)
        cand = self.idx.get((state, key))
        if cand is None and " " in key:      # try the words before common suffixes ("Rd", "area", "fire")
            k2 = re.sub(r"\b(area|fire|road|rd|creek|ranger district)\b", "", key).strip()
            cand = self.idx.get((state, k2)) if k2 else None
        if cand is None or not len(cand):
            return out
        if counties:
            cc = cand[cand.county_name.str.lower().isin([c.lower() for c in counties])]
            if len(cc):
                cand = cc
        if desc and re.search(r"\b(of|from)\b", str(desc), re.I):
            # a place that others are measured from is a settlement when one exists ("11 miles SE of Jackson")
            pp = cand[cand.feature_class.isin(["Populated Place", "Civil", "Census"])]
            if len(pp):
                cand = pp
        pts = cand[["lat", "lon"]].drop_duplicates().to_numpy()
        la0, lo0 = pts[:, 0].mean(), pts[:, 1].mean()
        spread = float(np.max(geo.haversine_km(pts[:, 0], pts[:, 1], la0, lo0))) if len(pts) > 1 else 0.0
        if spread > 15.0:
            out.update({"match_class": "ambiguous", "n_candidates": int(len(pts)), "spread_km": spread})
            return out
        la, lo = la0, lo0
        radius = 2.0 + spread
        if bearing is not None:
            if dist_km is not None:
                b = math.radians(bearing)
                la += dist_km * math.cos(b) / 111.0
                lo += dist_km * math.sin(b) / (111.0 * math.cos(math.radians(la0)))
                radius += 0.25 * dist_km + 2.0
            else:
                radius += 5.0
        classes = set(cand.feature_class)
        if re.search(r"\b(county|parish|borough)$", key):
            ptype = "county"
        elif classes & {"Populated Place", "Census"}:
            ptype = "populated place"
        else:
            ptype = "named feature"
        out.update({"match_class": "matched", "lat_gaz": la, "lon_gaz": lo, "radius_km": radius, "n_candidates": int(len(pts)), "spread_km": spread,
                    "place_type": ptype, "offset_applied": bool(bearing is not None and dist_km is not None)})
        return out

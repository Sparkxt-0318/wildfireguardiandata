"""Loaders for the state lists and the national incident-location feed (canonical: rid, source, ident, name, day, lat, lon, acres, state)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import paths

COLS = ["rid", "source", "ident", "name", "day", "lat", "lon", "acres", "state", "year"]


def _ms_to_day(s):
    return pd.to_numeric(s, errors="coerce") / 86_400_000.0


def _read(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            ft = json.loads(line)
            g = ft.get("geometry") or {}
            pr = ft["properties"]
            c = g.get("coordinates")
            if g.get("type") == "Point" and c:
                pr["_lon"], pr["_lat"] = c[0], c[1]
            elif g.get("type") in ("Polygon", "MultiPolygon") and c:
                ring = c[0] if g["type"] == "Polygon" else c[0][0]
                xs, ys = zip(*[(p[0], p[1]) for p in ring])
                pr["_lon"], pr["_lat"] = float(np.mean(xs)), float(np.mean(ys))
            rows.append(pr)
    return pd.DataFrame(rows)


def _out(src, d, ident, name, day, lat, lon, acres, state):
    o = pd.DataFrame({"ident": ident, "name": name, "day": day, "lat": pd.to_numeric(lat, errors="coerce"),
                      "lon": pd.to_numeric(lon, errors="coerce"), "acres": pd.to_numeric(acres, errors="coerce"), "state": state})
    o["source"] = src
    o["rid"] = src + ":" + d["OBJECTID"].astype(str)
    o["year"] = pd.to_datetime(o["day"], unit="D", errors="coerce").dt.year
    return o[COLS]


def load(name: str) -> pd.DataFrame:
    R = paths.RAW
    if name == "wa":
        a = _read(R / "state_lists/wa_dnr_fire_statistics_2008_present.ndjson")
        b = _read(R / "state_lists/wa_dnr_fire_statistics_1970_2007.ndjson")
        oa = _out("wa_dnr_2008", a, a["INCIDENT_NO"], a["INCIDENT_NM"], _ms_to_day(a["DSCVR_DT"]), a["LAT_COORD"].fillna(a["_lat"]), a["LON_COORD"].fillna(a["_lon"]), a["ACRES_BURNED"], "WA")
        ob = _out("wa_dnr_1970", b, None, b["FIREEVNT_NM"], _ms_to_day(b["START_DT"]), b["_lat"], b["_lon"], b["ACRES_BURNED"], "WA")
        return pd.concat([oa, ob], ignore_index=True)
    if name == "ok":
        d = _read(R / "state_lists/ok_historical_fire_occurrence.ndjson")
        return _out("ok_forestry", d, d["LocallncidentID"], d["FireName"].fillna(d["IncidentName"]), _ms_to_day(d["FireDiscoveryDate"]), d["Latitude"].fillna(d["_lat"]), d["Longitude"].fillna(d["_lon"]), d["FinalFireAcreQuantity"], "OK")
    if name == "ak":
        d = _read(R / "state_lists/ak_fire_history_to_2024.ndjson")
        return _out("ak_fire_history", d, d["FIREID"].astype(str), d["NAME"], pd.to_datetime(d["FIREYEAR"].astype(str) + "-07-01", errors="coerce").astype("int64") / 86_400e9 if False else (pd.to_datetime(d["FIREYEAR"].astype(str) + "-07-01", errors="coerce") - pd.Timestamp("1970-01-01")).dt.days, d["_lat"], d["_lon"], d["ACRES"], "AK")
    if name == "wfigs":
        d = _read(R / "wfigs/WFIGS_Incident_Locations.ndjson")
        lat = d["InitialLatitude"].fillna(d["_lat"]); lon = d["InitialLongitude"].fillna(d["_lon"])
        acres = d["FinalAcres"].fillna(d["IncidentSize"]).fillna(d["DiscoveryAcres"])
        st = d["POOState"] if "POOState" in d else None
        return _out("wfigs", d, d["IrwinID"].str.lower(), d["IncidentName"], _ms_to_day(d["FireDiscoveryDateTime"]), lat, lon, acres, st)
    raise KeyError(name)

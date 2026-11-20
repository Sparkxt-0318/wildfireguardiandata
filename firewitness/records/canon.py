"""Canonical tables for linking: FPA FOD, MTBS events, ICS-209-PLUS incidents, FIRED attributes carried in ICS-209-PLUS.

Published link columns are kept in separate `pub_*` columns: they are used only to score links, never as features.
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from . import geo, paths

EPOCH = pd.Timestamp("1970-01-01")


def _day(ts):
    return ((pd.to_datetime(ts, errors="coerce", utc=True, format="mixed").dt.tz_localize(None) - EPOCH) / pd.Timedelta(days=1)).to_numpy(float)


def build_fod(out=None) -> pd.DataFrame:
    c = sqlite3.connect(paths.WORK / "fpafod" / "Data" / "FPA_FOD_20260615.gpkg")
    d = pd.read_sql("select FOD_ID, FPA_ID, SOURCE_SYSTEM, NWCG_REPORTING_AGENCY, FIRE_NAME, COMPLEX_NAME, FIRE_YEAR, "
                    "DISCOVERY_DATE, CONT_DATE, FIRE_SIZE, LATITUDE, LONGITUDE, STATE, COUNTY, FIPS_CODE, "
                    "ICS_209_PLUS_INCIDENT_JOIN_ID, ICS_209_PLUS_COMPLEX_JOIN_ID, MTBS_ID from Fires", c)
    o = pd.DataFrame({"fid": d.FOD_ID.astype(int), "name": d.FIRE_NAME, "year": d.FIRE_YEAR.astype(int),
                      "day": _day(d.DISCOVERY_DATE), "cont_day": _day(d.CONT_DATE), "acres": d.FIRE_SIZE.astype(float),
                      "lat": d.LATITUDE.astype(float), "lon": d.LONGITUDE.astype(float), "state": d.STATE,
                      "fips": d.FIPS_CODE, "agency": d.NWCG_REPORTING_AGENCY, "source": d.SOURCE_SYSTEM,
                      "pub_ics": d.ICS_209_PLUS_INCIDENT_JOIN_ID, "pub_ics_cplx": d.ICS_209_PLUS_COMPLEX_JOIN_ID,
                      "pub_mtbs": d.MTBS_ID})
    if out is not False:
        paths.CANON.mkdir(parents=True, exist_ok=True)
        o.to_parquet(paths.CANON / "fod.parquet")
    return o


def build_mtbs() -> pd.DataFrame:
    r = geo._read_shp(paths.RAW / "mtbs" / "mtbs_perimeter_data.zip", "mtbs")
    fields = [f[0] for f in r.fields[1:]]
    rows = [dict(zip(fields, rec)) for rec in r.iterRecords()]
    d = pd.DataFrame(rows)
    o = pd.DataFrame({"mid": d.event_id, "name": d.incid_name, "kind": d.incid_type, "irwin": d.irwinid,
                      "day": _day(d.ig_date), "acres": pd.to_numeric(d.burnbndac, errors="coerce"),
                      "lat": pd.to_numeric(d.burnbndlat, errors="coerce"), "lon": pd.to_numeric(d.burnbndlon, errors="coerce")})
    o["state"] = o.mid.str[:2]
    o["year"] = pd.to_datetime(d.ig_date, errors="coerce").dt.year
    o.to_parquet(paths.CANON / "mtbs.parquet")
    return o


def build_ics() -> pd.DataFrame:
    d = pd.read_csv(paths.WORK / "ics209plus/ics209plus-wildfire/ics209-plus-wf_incidents_1999to2020.csv", low_memory=False, encoding="latin-1")
    o = pd.DataFrame({"iid": d.INCIDENT_ID.astype(str), "name": d.INCIDENT_NAME, "number": d.INCIDENT_NUMBER,
                      "day": _day(d.DISCOVERY_DATE), "acres": pd.to_numeric(d.FINAL_ACRES, errors="coerce"),
                      "lat": pd.to_numeric(d.POO_LATITUDE, errors="coerce"), "lon": pd.to_numeric(d.POO_LONGITUDE, errors="coerce"),
                      "state": d.POO_STATE, "county": d.POO_COUNTY, "year": pd.to_numeric(d.START_YEAR, errors="coerce"),
                      "complex": d.COMPLEX,
                      "pub_fod_list": d.FOD_ID_LIST, "pub_fod_largest": d.LRGST_FOD_ID, "pub_mtbs_list": d.MTBS_FIRE_LIST,
                      "pub_fired": d.FIRED_ID, "fired_acres": pd.to_numeric(d.FIRED_ACRES, errors="coerce"),
                      "fired_lat": pd.to_numeric(d.FIRED_IG_LAT, errors="coerce"), "fired_lon": pd.to_numeric(d.FIRED_IG_LON, errors="coerce")})
    o.to_parquet(paths.CANON / "ics_inc.parquet")
    return o


if __name__ == "__main__":
    for f in (build_fod, build_mtbs, build_ics):
        x = f()
        print(f.__name__, x.shape)

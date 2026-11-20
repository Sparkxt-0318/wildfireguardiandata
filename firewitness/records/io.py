"""Loaders: raw source tables to one canonical, still-raw record frame (strings kept as reported)."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import paths

CANON_COLS = ["rid", "src", "file_year", "inc_key", "name", "number", "state", "county", "lat_raw", "lon_raw",
              "latdeg", "latmin", "londeg", "lonmin", "start_raw", "report_raw", "area_raw", "uom_raw", "tz_raw",
              "twp", "rng", "sec", "utm_zone", "utm_e", "utm_n", "irwin", "location_desc"]


def read_csv_raw(path, **kw) -> pd.DataFrame:
    """Read a CSV as strings without losing any byte: latin-1 is a lossless byte-to-char mapping."""
    return pd.read_csv(path, dtype=str, encoding="latin-1", keep_default_na=False, na_values=[""], low_memory=False, **kw)


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=CANON_COLS, dtype=object)


def ics_raw_2014(path: Path | None = None) -> pd.DataFrame:
    p = path or (paths.ICS_SRC / "2020" / "SIT209_HISTORY_INCIDENTS.csv")
    d = read_csv_raw(p)
    o = _empty()
    o["inc_key"] = d["INCIDENT_IDENTIFIER"]
    o["name"] = d["INCIDENT_NAME"]
    o["number"] = d["INCIDENT_NUMBER"]
    o["state"] = d["POO_STATE_CODE"]            # FIPS
    o["county"] = d["POO_COUNTY_CODE"]          # FIPS 3-digit
    o["lat_raw"] = d["POO_LATITUDE"]
    o["lon_raw"] = d["POO_LONGITUDE"]
    o["start_raw"] = d["DISCOVERY_DATE"]
    o["report_raw"] = d["CREATED_DATE"]
    o["area_raw"] = d["INCIDENT_AREA"]
    o["uom_raw"] = d["INC_AREA_UOM_IDENTIFIER"]
    o["tz_raw"] = d["LOCAL_TIMEZONE_IDENTIFIER"]
    o["twp"], o["rng"], o["sec"] = d["POO_LD_TWP"], d["POO_LD_RGE"], d["POO_LD_SEC"]
    o["utm_zone"], o["utm_e"], o["utm_n"] = d["POO_UTM_ZONE"], d["POO_UTM_EASTING"], d["POO_UTM_NORTHING"]
    o["irwin"] = d["IRWIN_IDENTIFIER"]
    o["location_desc"] = d["POO_SHORT_LOCATION_DESC"]
    o["src"] = "ics209_2014"
    o["file_year"] = "2020"
    o["rid"] = "ics14:" + d["ID"].astype(str)
    return o


def ics_raw_2001_2013() -> pd.DataFrame:
    parts = []
    for f in sorted(paths.RAW_PQ.glob("*_IMSR_IMSR_209_INCIDENTS*.parquet")):
        y = f.name[:4]
        d = pd.read_parquet(f).reset_index(drop=True)
        o = _empty()
        o["number"] = d["INCIDENT_NUMBER"]
        o["name"] = d["INCIDENT_NAME"]
        o["state"] = d["UN_USTATE"] if "UN_USTATE" in d else d.get("OWNERSHIP_STATE")
        o["county"] = d["COUNTY"]
        o["lat_raw"], o["lon_raw"] = d["LATITUDE"], d["LONGITUDE"]
        o["start_raw"], o["report_raw"] = d["START_DATE"], d["REPORT_DATE"]
        o["area_raw"], o["uom_raw"] = d["AREA"], d["AREA_MEASUREMENT"]
        o["location_desc"] = d["LOCATION"]
        o["inc_key"] = d["INCIDENT_NUMBER"].fillna("") + "|" + d["INCIDENT_NAME"].fillna("")
        o["src"] = "ics209_imsr"
        o["file_year"] = y
        o["rid"] = f"imsr{y}:" + d.index.astype(str)
        parts.append(o)
    return pd.concat(parts, ignore_index=True)


def ics_raw_1999_2002() -> pd.DataFrame:
    parts = []
    for f in sorted(paths.RAW_PQ.glob("*_IMSR_INCIDENT_INFORMATIONS.parquet")):
        y = f.name[:4]
        d = pd.read_parquet(f).reset_index(drop=True)
        o = _empty()
        o["number"] = d["EVENT_ID"]
        o["name"] = d["ENAME"]
        o["state"] = d["UN_USTATE"]
        o["latdeg"], o["latmin"], o["londeg"], o["lonmin"] = d["LATDEG"], d["LATMIN"], d["LONGDEG"], d["LONGMIN"]
        o["start_raw"], o["report_raw"] = d["STARTDATE"], d["REPDATE"]
        o["area_raw"] = d["ACRES"]
        o["uom_raw"] = "ACRES"
        o["location_desc"] = d["LOCATE"]
        o["inc_key"] = d["EVENT_ID"].fillna("") + "|" + d["ENAME"].fillna("")
        o["src"] = "ics209_info"
        o["file_year"] = y
        o["rid"] = f"info{y}:" + d.index.astype(str)
        parts.append(o)
    return pd.concat(parts, ignore_index=True)


def ics_raw_all() -> pd.DataFrame:
    return pd.concat([ics_raw_1999_2002(), ics_raw_2001_2013(), ics_raw_2014()], ignore_index=True)


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


_DT_FORMATS = ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d")


def parse_dt(s: pd.Series) -> pd.Series:
    """Parse mixed raw date strings; unparseable stay NaT (never guessed)."""
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    rest = s.notna()
    for fmt in _DT_FORMATS:
        if not rest.any():
            break
        t = pd.to_datetime(s[rest], format=fmt, errors="coerce")
        ok = t.notna()
        out.loc[t.index[ok]] = t[ok]
        rest = rest & out.isna()
    return out

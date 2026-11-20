"""Agency records: load a slice of FPA FOD, compute each record's honest radius and time window.

Nothing here changes a record. Derived columns (r_loc_m, r_fire_m, r_m, t0, t1, split) sit beside the raw fields.
"""
from __future__ import annotations

import hashlib
import math
import sqlite3
import zipfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from firewitness.core.config import load_region

from .fetch import fetch, raw_path

TRACK_DIR = Path(__file__).parent
ACRE_M2 = 4046.8564224
JD_UNIX = 2440587.5  # Julian day of 1970-01-01


def region(name: str = "us") -> dict:
    return load_region(TRACK_DIR, name)


def sqlite_path(cfg: dict) -> Path:
    rc = cfg["records"]
    z = fetch(rc["url"], rc["raw_rel"])
    out = z.parent / "sqlite" / rc["sqlite_member"]
    if not out.exists():
        with zipfile.ZipFile(z) as zf:
            zf.extractall(z.parent / "sqlite")
    return out


def jd_to_date(jd: pd.Series) -> pd.Series:
    days = np.floor(jd.astype(float) - JD_UNIX + 1e-9)
    return pd.to_datetime(days, unit="D", errors="coerce").dt.date


def decimals(x: float) -> int:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 0
    s = repr(round(float(x), 8))
    return len(s.split(".")[1].rstrip("0")) if "." in s else 0


def r_loc_m(lat: float, lon: float, r_min: float = 250.0) -> float:
    """Half the diagonal of the rounding cell implied by the coordinates' decimal places, at least r_min."""
    dl = 0.5 * 10.0 ** (-min(decimals(lat), 8))
    dn = 0.5 * 10.0 ** (-min(decimals(lon), 8))
    dy = dl * 111_320.0
    dx = dn * 111_320.0 * math.cos(math.radians(lat))
    return max(r_min, math.hypot(dx, dy))


def size_class(acres: float, cfg: dict) -> str:
    for name, lo, hi in cfg["size_classes"]:
        if acres <= hi:
            return name
    return cfg["size_classes"][-1][0]


def split_of(key: str) -> str:
    """dev (0-2) or sealed (3-9) by sha256 of the source id, as fixed in the protocol."""
    h = int(hashlib.sha256(str(key).encode()).hexdigest(), 16) % 10
    return "dev" if h <= 2 else "sealed"


def load_slice(slice_name: str, cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or region()
    sl = cfg["slices"][slice_name]
    db = sqlite_path(cfg)
    q = ("select FOD_ID, FIRE_YEAR, LATITUDE, LONGITUDE, DISCOVERY_DATE, DISCOVERY_TIME, CONT_DATE, CONT_TIME, "
         "FIRE_SIZE, FIRE_SIZE_CLASS, STATE, MTBS_ID, FIRE_NAME, NWCG_REPORTING_AGENCY, SOURCE_SYSTEM, "
         "NWCG_GENERAL_CAUSE from Fires where FIRE_YEAR in (%s)" % ",".join(str(int(y)) for y in sl["years"]))
    if sl.get("states"):
        q += " and STATE in (%s)" % ",".join("'%s'" % s for s in sl["states"])
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as c:
        df = pd.read_sql(q, c)
    return add_windows(df, cfg)


def add_windows(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    w = cfg["window"]
    loc = cfg["location"]
    df = df.copy()
    df["disc_date"] = jd_to_date(df["DISCOVERY_DATE"])
    df["cont_date"] = jd_to_date(df["CONT_DATE"]) if "CONT_DATE" in df else None
    df["r_loc_m"] = [r_loc_m(a, b, loc["r_loc_min_m"]) for a, b in zip(df.LATITUDE, df.LONGITUDE)]
    df["area_m2"] = df["FIRE_SIZE"].astype(float) * ACRE_M2
    df["r_fire_m"] = np.sqrt(df["area_m2"] / math.pi)
    df["r_m"] = df["r_loc_m"] + df["r_fire_m"]
    dflt = cfg["default_duration_days"]
    t0, t1, end_src = [], [], []
    for d, c, k in zip(df.disc_date, df.cont_date, df.FIRE_SIZE_CLASS):
        t0.append(d - timedelta(days=w["pre_days"]))
        ok = c is not None and not pd.isna(c) and c >= d and (c - d).days <= w["max_cont_days"]
        end = c if ok else d + timedelta(days=dflt.get(k, 1))
        end_src.append("CONT_DATE" if ok else "default_by_class")
        t1.append(end + timedelta(days=w["post_days"]))
    df["t0"], df["t1"], df["t1_source"] = t0, t1, end_src
    df["rid"] = "FOD" + df["FOD_ID"].astype(str)
    df["split"] = df["FOD_ID"].astype(str).map(split_of)
    return df

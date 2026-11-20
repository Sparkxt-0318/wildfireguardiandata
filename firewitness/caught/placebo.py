"""Matched placebo windows (C1): same state, date window, radius, recorded size and land cover; 10-50 km away;
no recorded fire (FPA FOD within 5 km and 30 days, agency or MTBS perimeter in the window)."""
from __future__ import annotations

import hashlib
import math
import random

import numpy as np
import pandas as pd

from .geo import PointIndex, R_EARTH
from .landcover import lc_class


def _dest(lat, lon, bearing, dist_m):
    la, lo, b = map(math.radians, (lat, lon, bearing))
    d = dist_m / R_EARTH
    la2 = math.asin(math.sin(la) * math.cos(d) + math.cos(la) * math.sin(d) * math.cos(b))
    lo2 = lo + math.atan2(math.sin(b) * math.sin(d) * math.cos(la), math.cos(d) - math.sin(la) * math.sin(la2))
    return math.degrees(la2), (math.degrees(lo2) + 540) % 360 - 180


def make_placebos(rec: pd.DataFrame, all_fod: pd.DataFrame, perim_index, mtbs_index, states, cfg) -> pd.DataFrame:
    """One placebo per record. all_fod: FPA FOD records of the slice years +-1 (lat, lon, disc_date)."""
    from shapely.geometry import Point
    from shapely.strtree import STRtree

    pc = cfg["placebo"]
    st_geom = dict(zip(states.STUSPS, states.geometry))
    fod_idx = PointIndex(all_fod.LATITUDE, all_fod.LONGITUDE, np.zeros(len(all_fod)),
                         all_fod.disc_date, all_fod.disc_date)
    rows = []
    for r in rec.itertuples():
        rng = random.Random(int(hashlib.sha256(f"placebo:{r.rid}".encode()).hexdigest(), 16) % (2 ** 32))
        want = lc_class(r.LATITUDE, r.LONGITUDE)
        sg = st_geom.get(r.STATE)
        got = None
        tries = 0
        for tries in range(1, pc["tries"] + 1):
            la, lo = _dest(r.LATITUDE, r.LONGITUDE, rng.uniform(0, 360), rng.uniform(pc["min_km"], pc["max_km"]) * 1000)
            if sg is not None and not sg.contains(Point(lo, la)):
                continue
            c = lc_class(la, lo)
            if c in (0, 80) or c != want:
                continue
            t0 = pd.Timestamp(r.t0) - pd.Timedelta(days=pc["excl_days"])
            t1 = pd.Timestamp(r.t1) + pd.Timedelta(days=pc["excl_days"])
            if len(fod_idx.query(la, lo, pc["excl_record_km"] * 1000 + r.r_m, t0.date(), t1.date())):
                continue
            if perim_index is not None and perim_index.query(la, lo, r.r_m, r.t0, r.t1):
                continue
            if mtbs_index is not None and mtbs_index.query(la, lo, r.r_m, r.t0, r.t1):
                continue
            got = (la, lo, c)
            break
        rows.append({"rid": "PLC_" + r.rid, "of_rid": r.rid, "LATITUDE": got[0] if got else np.nan,
                     "LONGITUDE": got[1] if got else np.nan, "landcover": want, "tries": tries,
                     "matched": got is not None})
    p = pd.DataFrame(rows)
    keep = ["t0", "t1", "r_m", "r_loc_m", "r_fire_m", "area_m2", "FIRE_SIZE", "FIRE_SIZE_CLASS", "STATE", "FIRE_YEAR",
            "split", "disc_date", "t1_source"]
    p = p.merge(rec[["rid"] + keep], left_on="of_rid", right_on="rid", suffixes=("", "_rec")).drop(columns="rid_rec")
    return p

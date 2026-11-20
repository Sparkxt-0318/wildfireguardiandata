"""Tool 4: one permanent ID per real fire, deterministic, with a crosswalk to every source ID.

ID = FW-<yyyymmdd of the cleaned start date>-<location cell>-<ordinal>
  cell    = 0.1 degree cell of the cleaned location, 4+4 digits (row from 90S, column from 180W)
  ordinal = rank among the fires with the same date and cell, by acres (descending) then source key
Nothing in the ID depends on other years or on run order, so a re-run, or adding a year, cannot change it.

Complexes: a source record (ICS-209 incident, MTBS event) linked to two or more fires becomes a parent
`FWC-...` with the fires as children. A source ID whose linked fires lie far apart in space or time covers
several fires: it is SPLIT (each fire keeps its own ID, the source ID points to all of them). Records of
different sources recognised as one fire by the duplicate step are MERGED under one ID.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import geo


def cell_of(lat, lon):
    r = np.floor((np.asarray(lat, float) + 90.0) * 10).astype("int64")
    c = np.floor((np.asarray(lon, float) + 180.0) * 10).astype("int64")
    return r, c


def date_str(day):
    d = pd.to_datetime(np.asarray(day, float), unit="D", errors="coerce")
    return pd.Series(d).dt.strftime("%Y%m%d").fillna("00000000").to_numpy()


def assign_ids(fires: pd.DataFrame) -> pd.DataFrame:
    """fires: one row per real fire with key (stable source key string), day, lat, lon, acres. Adds perm_id."""
    f = fires.copy()
    r, c = cell_of(f.lat.to_numpy(), f.lon.to_numpy())
    ok = np.isfinite(f.lat.to_numpy()) & np.isfinite(f.lon.to_numpy())
    f["cell"] = np.where(ok, [f"{a:04d}{b:04d}" for a, b in zip(r, c)], "XXXXXXXX")
    f["dstr"] = date_str(f.day.to_numpy())
    f = f.sort_values(["dstr", "cell", "acres", "key"], ascending=[True, True, False, True], na_position="last", kind="mergesort")
    f["ord"] = f.groupby(["dstr", "cell"]).cumcount() + 1
    f["perm_id"] = "FW-" + f.dstr + "-" + f.cell + "-" + f.ord.map(lambda x: f"{x:02d}")
    return f.sort_index()


def spread(g: pd.DataFrame) -> pd.Series:
    """Max pairwise-ish extent of a group of fires: km across its bounding box diagonal, and days apart."""
    dk = geo.haversine_km(g.lat.min(), g.lon.min(), g.lat.max(), g.lon.max()) if len(g) else 0.0
    return pd.Series({"km": dk, "days": g.day.max() - g.day.min()})


def parent_groups(links: pd.DataFrame, fires: pd.DataFrame, source: str, split_km=25.0, split_days=45.0):
    """links: (fire_key, src_id) pairs, fires: key, day, lat, lon. Returns (parents, splits).

    parents: src_ids linked to >= 2 fires (complex parents, with children); splits: the subset whose children are
    farther than split_km or split_days apart (the source ID covers several fires)."""
    m = links.merge(fires[["key", "day", "lat", "lon"]], left_on="fire_key", right_on="key")
    g = m.groupby("src_id")
    cnt = g.size()
    multi = cnt[cnt >= 2].index
    ext = m[m.src_id.isin(multi)].groupby("src_id").apply(spread, include_groups=False)
    parents = pd.DataFrame({"src_id": multi, "n_children": cnt[multi].to_numpy()}).merge(ext, left_on="src_id", right_index=True)
    parents["split"] = (parents.km > split_km) | (parents.days > split_days)
    parents["source"] = source
    parents["parent_id"] = "FWC-" + source + "-" + parents.src_id.astype(str)
    return parents


def build(fod: pd.DataFrame, dup_keeper: np.ndarray, link_mtbs: pd.DataFrame, link_ics: pd.DataFrame, mtbs: pd.DataFrame, ics: pd.DataFrame):
    """fod: canonical FOD (positional), dup_keeper: for each FOD row the positional index of its duplicate cluster keeper,
    link_mtbs / link_ics: DataFrames fid, src_id (linked outcomes only).
    Returns fires (one row per real fire), crosswalk (perm_id, source, source_id), parents (complexes), summary."""
    n = len(fod)
    is_keeper = dup_keeper == np.arange(n)
    fires = fod[is_keeper][["fid", "day", "lat", "lon", "acres", "state", "year"]].copy()
    fires["key"] = "fod:" + fires.fid.astype(str)
    # a merged cluster takes the earliest start day of its members
    day_min = pd.Series(fod.day.to_numpy()).groupby(dup_keeper).min()
    fires["day"] = day_min.reindex(np.flatnonzero(is_keeper)).to_numpy()
    fires = assign_ids(fires)
    key_of_fid = pd.Series(np.where(is_keeper, np.arange(n), dup_keeper), index=fod.fid.to_numpy())
    keeper_fid = pd.Series(fod.fid.to_numpy()[key_of_fid.to_numpy()], index=fod.fid.to_numpy())
    pid = fires.set_index("fid").perm_id
    fod_perm = pid.reindex(keeper_fid.to_numpy()).to_numpy()
    rows = [pd.DataFrame({"perm_id": fod_perm, "source": "fpa_fod", "source_id": fod.fid.astype(str).to_numpy()})]
    for lk, src in ((link_mtbs, "mtbs"), (link_ics, "ics209plus")):
        if len(lk):
            kf = keeper_fid.reindex(lk.fid.to_numpy()).to_numpy()
            rows.append(pd.DataFrame({"perm_id": pid.reindex(kf).to_numpy(), "source": src, "source_id": lk.src_id.astype(str).to_numpy()}).drop_duplicates())
    xw = pd.concat(rows, ignore_index=True).dropna(subset=["perm_id"])
    parents = []
    for lk, src in ((link_mtbs, "mtbs"), (link_ics, "ics209plus")):
        if len(lk):
            l2 = pd.DataFrame({"fire_key": "fod:" + keeper_fid.reindex(lk.fid.to_numpy()).astype(str).to_numpy(), "src_id": lk.src_id.to_numpy()}).drop_duplicates()
            parents.append(parent_groups(l2, fires, src))
    parents = pd.concat(parents, ignore_index=True) if parents else pd.DataFrame()
    summary = {"fod_records": int(n), "fires": int(len(fires)), "merged_records": int((~is_keeper).sum()),
               "complex_parents": int(len(parents)), "split_source_ids": int(parents.split.sum()) if len(parents) else 0}
    return fires, xw, parents, summary

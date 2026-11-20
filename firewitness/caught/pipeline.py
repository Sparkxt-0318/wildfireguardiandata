"""One slice end to end: records + placebos -> labels; truth fires -> recall. Small results go to results/caught/."""
from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import records
from .geo import PointIndex
from .placebo import make_placebos
from .run import Sources, evaluate, prepare_windows, run_dir

_SRC = {}


def sources(cfg) -> Sources:
    if "s" not in _SRC:
        _SRC["s"] = Sources(cfg)
    return _SRC["s"]


def fod_years(cfg, years) -> pd.DataFrame:
    db = records.sqlite_path(cfg)
    q = ("select FOD_ID, LATITUDE, LONGITUDE, DISCOVERY_DATE, CONT_DATE, FIRE_SIZE, FIRE_SIZE_CLASS, STATE, FIRE_YEAR "
         "from Fires where FIRE_YEAR in (%s)" % ",".join(str(y) for y in years))
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as c:
        d = pd.read_sql(q, c)
    return records.add_windows(d, cfg)


def fod_big_index(all_fod: pd.DataFrame) -> PointIndex:
    b = all_fod[all_fod.FIRE_SIZE_CLASS.isin(["C", "D", "E", "F", "G"])]
    return PointIndex(b.LATITUDE, b.LONGITUDE, np.zeros(len(b)), b.disc_date,
                      [t - timedelta(days=1) for t in b.t1])


def run_slice(slice_name: str, threads: int = 40, params=None, tag: str = "v1", only_dev=False, limit=None):
    from . import perimeters

    cfg = records.region()
    rec = records.load_slice(slice_name, cfg)
    if only_dev:
        rec = rec[rec.split == "dev"]
    if limit:
        rec = rec.sample(n=min(limit, len(rec)), random_state=0)
    rec = prepare_windows(rec, cfg)
    years = sorted(set(cfg["slices"][slice_name]["years"]))
    all_fod = fod_years(cfg, list(range(years[0] - 1, years[-1] + 2)))
    src = sources(cfg)
    big = fod_big_index(all_fod)
    name = f"{slice_name}_{tag}" + ("_dev" if only_dev else "") + (f"_n{limit}" if limit else "")
    rd = run_dir(name)
    pp = rd / "placebo_windows.parquet"
    if pp.exists():
        plc = pd.read_parquet(pp)
    else:
        plc = make_placebos(rec, all_fod, src.perim_idx, src.mtbs_idx, perimeters.states(), cfg)
        plc.to_parquet(pp)
    plc = prepare_windows(plc, cfg)
    lab_r = evaluate(name + "/records", rec, src, big, True, threads, params)
    lab_p = evaluate(name + "/placebo", plc, src, big, True, threads, params)
    return rec, plc, lab_r, lab_p


def run_truth(split: str, tag: str = "v1", threads: int = 40, params=None, strata=None) -> pd.DataFrame:
    from .fetch import RAW_ROOT
    from . import truth as T

    cfg = records.region()
    tp = RAW_ROOT / "derived_caught" / "truth_2018_2020.parquet"
    tr = pd.read_parquet(tp) if tp.exists() else T.build(cfg)
    if not tp.exists():
        tr.to_parquet(tp)
    tr = tr[tr.split == split]
    if strata:
        tr = tr[tr.stratum.isin(strata)]
    for c in ("t0", "t1", "disc_date"):
        tr[c] = pd.to_datetime(tr[c]).dt.date
    w = prepare_windows(tr, cfg)
    src = sources(cfg)
    all_fod = fod_years(cfg, [2017, 2018, 2019, 2020, 2021])
    lab = evaluate(f"truth_{split}_{tag}", w, src, fod_big_index(all_fod), perimeter_on=False, threads=threads,
                   params=params)
    return caught_truth(lab, tr)


def caught_truth(lab: pd.DataFrame, tr: pd.DataFrame) -> pd.DataFrame:
    """caught_ours: a verified/probable pixel label meets the polygon (+30 m); caught_std: a standard footprint does."""
    from shapely import wkt
    from pyproj import Transformer
    from shapely.ops import transform
    from .standard import local_crs

    g = dict(zip(tr.rid, tr.geometry_wkt))
    ours, std, ver = [], [], []
    for r in lab.itertuples():
        poly = wkt.loads(g[r.rid])
        c = poly.representative_point()
        t = Transformer.from_crs("EPSG:4326", local_crs(c.y, c.x), always_xy=True).transform
        pb = transform(t, poly).buffer(30)
        lab_ok = r.tier in ("verified", "probable") and bool(r.pixel_label) and isinstance(r.geometry_wkt, str)
        o = lab_ok and transform(t, wkt.loads(r.geometry_wkt)).intersects(pb)
        s = isinstance(r.std_geometry_wkt, str) and transform(t, wkt.loads(r.std_geometry_wkt)).intersects(pb)
        ours.append(bool(o or s))
        std.append(bool(s))
        ver.append(bool(o and r.tier == "verified"))
    lab = lab.copy()
    lab["caught_ours"], lab["caught_std"], lab["caught_verified"] = ours, std, ver
    lab = lab.merge(tr[["rid", "stratum", "geometry_wkt"]].rename(columns={"geometry_wkt": "truth_wkt"}), on="rid")
    return lab


def summarize(lab_r: pd.DataFrame | None, lab_p: pd.DataFrame | None, lab_t: pd.DataFrame | None) -> dict:
    out = {}
    if lab_r is not None:
        r = lab_r
        out["records_n"] = len(r)
        out["tiers"] = r.tier.value_counts().to_dict()
        out["headline_no_std_verified"] = int(((~r.std_label.astype(bool)) & (r.tier == "verified")).sum())
        out["no_std_probable"] = int(((~r.std_label.astype(bool)) & (r.tier == "probable")).sum())
        out["std_label_n"] = int(r.std_label.astype(bool).sum())
        out["by_class"] = r.assign(h=(~r.std_label.astype(bool)) & (r.tier == "verified"),
                                   p=(~r.std_label.astype(bool)) & (r.tier == "probable"),
                                   s=r.std_label.astype(bool)).groupby("FIRE_SIZE_CLASS")[["h", "p", "s"]].sum().astype(int).to_dict()
        out["reasons"] = r.reason.value_counts().to_dict()
    if lab_p is not None:
        p = lab_p
        sp = p[p.searched.astype(bool)] if "searched" in p else p
        out["placebo_n"] = len(p)
        out["placebo_searched_n"] = len(sp)
        out["placebo_verified"] = int((p.tier == "verified").sum())
        out["placebo_probable"] = int((p.tier == "probable").sum())
        out["placebo_probable_searched"] = int((sp.tier == "probable").sum())
        out["placebo_verified_rate_searched"] = float((sp.tier == "verified").mean()) if len(sp) else None
        out["placebo_probable_rate_searched"] = float((sp.tier == "probable").mean()) if len(sp) else None
        out["placebo_witnesses"] = p[p.tier != "record-only"].witnesses.value_counts().to_dict()
    if lab_t is not None:
        t = lab_t[lab_t.stratum == "primary_small"]
        out["truth_by_class"] = t.groupby("FIRE_SIZE_CLASS")[["caught_ours", "caught_std", "caught_verified"]].agg(
            ["mean", "sum", "count"]).round(3).to_dict()
        out["truth_n"] = len(t)
        out["truth_recall_ours"] = float(t.caught_ours.mean()) if len(t) else None
        out["truth_recall_std"] = float(t.caught_std.mean()) if len(t) else None
    return out

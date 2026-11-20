"""C2 truth: mapped small fires and prescribed burns of known place, date and area (protocol section 8).

Primary: CAL FIRE FRAP wildfire and prescribed-burn perimeters, NIFC interagency perimeter history; 2018-2020.
Secondary (reported, not gated): FACTS broadcast-burn polygons. The pipeline sees only a record-like input:
the polygon's representative point, r_loc = 250 m, start/end dates and mapped area. PERIMETER evidence is off.
"""
from __future__ import annotations

import math
from datetime import timedelta

import numpy as np
import pandas as pd

from . import records
from .records import ACRE_M2, size_class, split_of


def _link_fod(t, fod, pidx_fn):
    """For polygons without a start date: the FPA FOD record of the same year inside the polygon (+500 m)."""
    from pyproj import Transformer
    from shapely.geometry import Point
    from shapely.ops import transform
    from .geo import PointIndex
    from .standard import local_crs

    idx = PointIndex(fod.LATITUDE, fod.LONGITUDE, np.zeros(len(fod)), fod.disc_date, fod.disc_date)
    out = []
    for r in t.itertuples():
        c = r.geometry.representative_point()
        y = int(r.year) if pd.notna(r.year) else None
        if y is None:
            out.append((None, None, None))
            continue
        rad = math.sqrt(max(r.area_ac, 0.01) * ACRE_M2 / math.pi) * 3 + 2000
        d_hi = (r.d1.date() if pd.notna(r.d1) else pd.Timestamp(f"{y}-12-31").date())
        cand = idx.query(c.y, c.x, rad, pd.Timestamp(f"{y}-01-01").date(), d_hi)
        best = None
        if len(cand):
            tr = Transformer.from_crs("EPSG:4326", local_crs(c.y, c.x), always_xy=True).transform
            g = transform(tr, r.geometry).buffer(500)
            for i in cand:
                f = fod.iloc[int(i)]
                if g.contains(Point(*tr(f.LONGITUDE, f.LATITUDE))):
                    sc = abs(math.log((f.FIRE_SIZE + 0.1) / (r.area_ac + 0.1)))
                    if best is None or sc < best[0]:
                        best = (sc, f.disc_date, f.t1 - timedelta(days=1), f.FOD_ID)
        out.append(best[1:] if best else (None, None, None))
    return out


def build(cfg=None, y0=2018, y1=2020) -> pd.DataFrame:
    from . import perimeters
    from .pipeline import fod_years

    cfg = cfg or records.region()
    p = perimeters.load_all(y0, y1)
    p = p[p.year.between(y0, y1) & p.area_ac.notna() & (p.area_ac > 0)].copy()
    p["stratum"] = np.where(p.source == "facts_bb", "secondary_facts",
                            np.where(p.area_ac < 300, "primary_small", "reference_large"))
    # de-duplicate NIFC history against FRAP (same year, overlapping): FRAP is kept
    frap = p[p.source.isin(["frap", "frap_rx"])]
    nh = p[p.source == "nifc_hist"]
    if len(frap) and len(nh):
        from shapely.strtree import STRtree
        tree = STRtree(frap.geometry.values)
        drop = []
        fy = frap.year.values
        for i, r in zip(nh.index, nh.itertuples()):
            for k in tree.query(r.geometry):
                if fy[k] == r.year:
                    a = r.geometry.intersection(frap.geometry.values[k]).area
                    if a > 0.3 * min(r.geometry.area, frap.geometry.values[k].area):
                        drop.append(i)
                        break
        p = p.drop(index=drop)
    p = p[p.source != "wfigs"]
    fod = fod_years(cfg, list(range(y0, y1 + 1)))
    need = p.d0.isna() & (p.source != "facts_bb")
    links = _link_fod(p[need], fod, None)
    p["start_src"] = np.where(p.d0.notna(), "polygon", None)
    p["linked_fod"] = None
    for i, (d0, d1, fid) in zip(p[need].index, links):
        if d0 is not None:
            p.loc[i, "d0"] = pd.Timestamp(d0)
            if pd.isna(p.loc[i, "d1"]) or p.loc[i, "source"] == "nifc_hist":
                p.loc[i, "d1"] = pd.Timestamp(d1)
            p.loc[i, "start_src"] = "linked FPA FOD"
            p.loc[i, "linked_fod"] = str(fid)
    facts = p.source == "facts_bb"
    p.loc[facts, "d0"] = p.loc[facts, "d1"] - pd.Timedelta(days=3)
    p.loc[facts, "start_src"] = "date_completed - 3 days"
    p = p[p.d0.notna()].copy()
    rows = []
    dflt = cfg["default_duration_days"]
    for r in p.itertuples():
        c = r.geometry.representative_point()
        k = size_class(r.area_ac, cfg)
        d0 = r.d0.date()
        d1 = r.d1.date() if pd.notna(r.d1) and r.d1 >= r.d0 and (r.d1 - r.d0).days <= 180 else d0 + timedelta(days=dflt[k])
        a = r.area_ac * ACRE_M2
        rows.append({"rid": "TRU_" + r.pid, "truth_id": r.pid, "truth_source": r.source, "truth_kind": r.kind,
                     "stratum": r.stratum, "LATITUDE": c.y, "LONGITUDE": c.x, "r_loc_m": 250.0,
                     "r_fire_m": math.sqrt(a / math.pi), "r_m": 250.0 + math.sqrt(a / math.pi), "area_m2": a,
                     "FIRE_SIZE": r.area_ac, "FIRE_SIZE_CLASS": k, "FIRE_YEAR": int(r.year), "STATE": None,
                     "disc_date": d0, "t0": d0 - timedelta(days=1), "t1": d1 + timedelta(days=1),
                     "t1_source": "polygon" if d1 != d0 + timedelta(days=dflt[k]) else "default_by_class",
                     "split": split_of(r.pid), "start_src": r.start_src, "geometry_wkt": r.geometry.wkt})
    return pd.DataFrame(rows)

"""Slice runner: records and matched placebos (and truth fires) -> evidence -> tiers -> labels.

Stages (each cached under firewitness_raw/derived_caught/runs/<name>/ so a run resumes):
  windows   records (or truth) with radius and time window; placebos
  points    FIRMS, MCD64A1, HMS heat matches
  polys     MTBS, agency perimeters, attributed smoke
  scar      scar finder + short-wave hot spots (threads; JSON lines checkpoint)
  labels    evidence items, tier, geometry, floor, reason
"""
from __future__ import annotations

import json
import math
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import evidence as E
from . import hms, perimeters, records, standard
from .fetch import RAW_ROOT
from .floor import heat_floor_m2, scar_floor_m2
from .geo import PointIndex
from .scar import PARAMS, find_scar

RUNS = RAW_ROOT / "derived_caught" / "runs"
HEAT_HALF = {"S2_AF": 15.0, "LANDSAT_AF": 22.0}
MAX_PER_WITNESS = 50


def run_dir(name: str) -> Path:
    p = RUNS / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def _years_of(w: pd.DataFrame):
    ys = sorted({d.year for d in w.t0} | {d.year for d in w.t1})
    return [y for y in ys if 2018 <= y <= 2020] or ys


# ------------------------------------------------------------------ point and polygon matches
class Sources:
    """All non-imagery evidence sources for a set of years, loaded once."""

    def __init__(self, cfg, years=(2018, 2019, 2020)):
        y = list(years)
        self.cfg = cfg
        self.firms = standard.load_firms(y, cfg)
        self.mcd = standard.load_mcd64a1(y, cfg)
        self.mtbs = standard.load_mtbs(cfg)
        self.hms = hms.load_fire(min(y), max(y))
        self.smoke = hms.load_smoke(min(y), max(y))
        self.perims = perimeters.load_all(min(y), max(y))
        self.idx = {}
        for w in ["MODIS", "VIIRS_SNPP", "VIIRS_NOAA20"]:
            f = self.firms[self.firms.witness == w].reset_index(drop=True)
            self.idx[w] = (f, PointIndex(f.lat, f.lon, f.half_m, f.date, f.date))
        for w in ["GOES", "AVHRR", "HMS_ANALYST"]:
            f = self.hms[self.hms.witness == w].reset_index(drop=True)
            self.idx[w] = (f, PointIndex(f.lat, f.lon, f.half_m, f.date, f.date))
        m = self.mcd.reset_index(drop=True)
        unc = pd.to_timedelta(np.maximum(m.unc_days.values, 1), "D")
        d = pd.to_datetime(m.date)
        m["d0"], m["d1"] = (d - unc).dt.date, (d + unc).dt.date
        self.idx["MCD64A1"] = (m, PointIndex(m.lat, m.lon, m.half_m, m.d0, m.d1))
        mt = self.mtbs.copy()
        mt["d0"] = pd.to_datetime(mt.ig_date) - pd.Timedelta(days=1)
        mt["d1"] = pd.to_datetime(mt.ig_date) + pd.Timedelta(days=1)
        self.mtbs_idx = standard.PolygonIndex(mt.reset_index(drop=True), "d0", "d1", "Event_ID")
        self.mtbs_geom = dict(zip(mt.Event_ID, zip(mt.geometry, mt.d0, mt.d1)))
        pr = self.perims[self.perims.source != "facts_bb"].copy()
        yr0 = pd.to_datetime(pr["year"].astype("Int64").astype(str) + "-01-01", errors="coerce")
        pr["e0"] = pr.d0.fillna(np.maximum(pr.d1 - pd.Timedelta(days=120), yr0)).fillna(yr0)
        pr["e1"] = pr.d1.fillna(pr.d0 + pd.Timedelta(days=60)).fillna(yr0 + pd.Timedelta(days=365))
        pr = pr.dropna(subset=["e0", "e1"]).reset_index(drop=True)
        self.perim_idx = standard.PolygonIndex(pr, "e0", "e1", "pid")
        self.perim_geom = dict(zip(pr.pid, zip(pr.geometry, pr.e0, pr.e1)))
        # all heat points by day for the smoke rule
        hp = pd.concat([self.firms[["lat", "lon", "date"]], self.hms[["lat", "lon", "date"]]], ignore_index=True)
        self.heat_all = PointIndex(hp.lat, hp.lon, np.zeros(len(hp)), hp.date, hp.date)
        from shapely.strtree import STRtree
        self.smoke_by_day = {}
        for d, g in self.smoke[self.smoke.area_km2 < 2500].groupby("date"):
            g = g.reset_index(drop=True)
            self.smoke_by_day[d] = (g, STRtree(g.geometry.values))


def point_matches(src: Sources, w) -> list[dict]:
    out = []
    from .geo import haversine_m
    for wit, (tab, idx) in src.idx.items():
        ix = idx.query(w.LATITUDE, w.LONGITUDE, w.r_m, w.t0, w.t1)
        if len(ix) > MAX_PER_WITNESS:  # keep the nearest; the count is kept in the detail of the first
            dd = haversine_m(w.LATITUDE, w.LONGITUDE, idx.lat[ix], idx.lon[ix])
            ix = ix[np.argsort(dd)[:MAX_PER_WITNESS]]
        for i in ix:
            r = tab.iloc[int(i)]
            d0 = r.d0 if "d0" in tab else r.date
            d1 = r.d1 if "d1" in tab else r.date
            det = {"lat": round(float(r.lat), 5), "lon": round(float(r.lon), 5), "half_m": round(float(r.half_m), 1)}
            if "acq_dt" in tab:
                det["time_utc"] = str(r.acq_dt)
                det["frp"] = float(r.frp) if pd.notna(r.frp) else None
                det["conf"] = str(r.confidence)
            elif "hhmm" in tab:
                det["time_utc"] = f"{r.date} {r.hhmm}"
                det["sat"] = r.sat
            else:
                det["unc_days"] = int(r.unc_days)
            out.append({"witness": wit, "d0": str(d0), "d1": str(d1), **det})
    return out


def polygon_matches(src: Sources, w, fod_big: PointIndex | None, perimeter_on=True) -> list[dict]:
    out = []
    for eid in src.mtbs_idx.query(w.LATITUDE, w.LONGITUDE, w.r_m, w.t0, w.t1):
        g, d0, d1 = src.mtbs_geom[eid]
        out.append({"witness": "MTBS", "id": eid, "d0": str(pd.Timestamp(d0).date()), "d1": str(pd.Timestamp(d1).date())})
    if perimeter_on:
        for pid in src.perim_idx.query(w.LATITUDE, w.LONGITUDE, w.r_m, w.t0, w.t1):
            g, d0, d1 = src.perim_geom[pid]
            out.append({"witness": "PERIM", "id": pid, "d0": str(pd.Timestamp(d0).date()),
                        "d1": str(pd.Timestamp(d1).date())})
    # smoke: protocol 6.3
    from shapely.geometry import Point
    pt = Point(w.LONGITUDE, w.LATITUDE)
    d = w.disc_date if hasattr(w, "disc_date") and pd.notna(w.disc_date) else w.t0 + timedelta(days=1)
    while d <= w.t1 - timedelta(days=1):
        if d in src.smoke_by_day:
            g, tree = src.smoke_by_day[d]
            for k in tree.query(pt, predicate="within"):
                poly = g.geometry.values[k]
                if _other_fire(src, poly, w, d, fod_big):
                    continue
                out.append({"witness": "HMS_SMOKE", "id": f"{d}:{k}", "d0": str(d), "d1": str(d),
                            "area_km2": round(float(g.area_km2.values[k]), 1)})
                break
        d += timedelta(days=1)
    return out


def _other_fire(src, poly, w, d, fod_big) -> bool:
    from shapely.geometry import Point
    c = poly.centroid
    minx, miny, maxx, maxy = poly.bounds
    rad = max(maxx - minx, maxy - miny) * 111_000.0
    if fod_big is not None:
        for i in fod_big.query(c.y, c.x, rad, d, d):
            la, lo = fod_big.lat[i], fod_big.lon[i]
            if abs(la - w.LATITUDE) < 1e-6 and abs(lo - w.LONGITUDE) < 1e-6:
                continue
            if poly.contains(Point(lo, la)):
                return True
    for i in src.heat_all.query(c.y, c.x, rad, d, d):
        la, lo = src.heat_all.lat[i], src.heat_all.lon[i]
        if poly.contains(Point(lo, la)):
            from .geo import haversine_m
            if haversine_m(w.LATITUDE, w.LONGITUDE, la, lo) > w.r_m + 2000:
                return True
    return False


# ------------------------------------------------------------------ scar stage
def _scar_one(args):
    rid, lon, lat, r_m, t0, t1, area_ha, name, params = args
    try:
        res = find_scar(lon, lat, r_m, t0, t1, area_ha, run=name, params=params, floor_check=True)
        d = res.to_dict()
        d["states"].pop("no_fire", None)
    except Exception as e:
        d = {"status": "error", "error": f"{type(e).__name__}: {e}"[:500]}
    d["rid"] = rid
    return d


def _scar_chunk(chunk, threads):
    import warnings
    warnings.filterwarnings("ignore")
    with ThreadPoolExecutor(threads) as ex:
        return list(ex.map(_scar_one, chunk))


def scar_stage(name: str, w: pd.DataFrame, threads: int = 40, params=None, log_every=200, procs: int | None = None,
               heat_rids: set | None = None) -> dict:
    """Run find_scar on every searched window (procs processes x threads); JSON lines checkpoint."""
    import multiprocessing as mp
    import os
    from concurrent.futures import ProcessPoolExecutor

    procs = procs or int(os.environ.get("FIREWITNESS_PROCS", "4"))

    ck = run_dir(name) / "scar.jsonl"
    done = {}
    def _lean(j):
        # labels need status, geometry, components, hotspots, dates, threshold, floor and the state areas only;
        # the full record (looks, input hashes, state shapes) stays in the checkpoint file
        j.pop("looks", None)
        j.pop("inputs", None)
        st = j.get("states") or {}
        st.pop("unknown", None)
        st.pop("fire", None)
        return j

    if ck.exists():
        with open(ck) as fh:
            for line in fh:
                try:
                    j = json.loads(line)
                    if j.get("status") != "error":
                        done[j["rid"]] = _lean(j)
                except json.JSONDecodeError:
                    continue
    todo = w[w.searched & ~w.rid.isin(done)]
    p0 = dict(params or {})
    lh = p0.pop("landsat_if_heat", True)   # round 3 (kept)

    def prm(rid):
        if lh and heat_rids and rid in heat_rids:
            return {**p0, "landsat_if_no_scar": True}
        return p0 or None
    args = [(r.rid, r.LONGITUDE, r.LATITUDE, r.r_m, r.t0, r.t1, r.area_m2 / 1e4, name, prm(r.rid))
            for r in todo.itertuples()]
    # big windows first and spread over chunks, so no worker holds several at once
    args.sort(key=lambda a: -a[3])
    k = max(1, len(args) // 24)
    chunks = [args[i::k] for i in range(k)]
    t = time.time()
    n = 0
    per = max(1, threads // procs)
    with ProcessPoolExecutor(procs, mp_context=mp.get_context("spawn"), max_tasks_per_child=8) as ex, \
            open(ck, "a") as f:
        futs = [ex.submit(_scar_chunk, c, per) for c in chunks]
        for fu in as_completed(futs):
            for d in fu.result():
                f.write(json.dumps(d, default=str) + "\n")
                done[d["rid"]] = _lean(d)
                n += 1
            f.flush()
            if n // log_every != (n - 24) // log_every:
                rate = n / (time.time() - t)
                print(f"[{name}] scar {n}/{len(args)} {rate:.2f}/s eta {(len(args)-n)/max(rate,1e-9)/3600:.2f} h",
                      flush=True)
    return done


# ------------------------------------------------------------------ items, tiers, labels
def _local(lat, lon):
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:4326", standard.local_crs(lat, lon), always_xy=True).transform


def build_items(w, pts, polys, scar, src: Sources) -> list:
    from shapely.geometry import Point, shape
    from shapely.ops import transform

    tr = _local(w.LATITUDE, w.LONGITUDE)
    items = []
    for p in pts:
        x, y = tr(p["lon"], p["lat"])
        items.append(E.Item(p["witness"], Point(x, y).buffer(p["half_m"], 16), date.fromisoformat(p["d0"]),
                            date.fromisoformat(p["d1"]), p))
    for p in polys:
        if p["witness"] == "MTBS":
            g = transform(tr, src.mtbs_geom[p["id"]][0])
        elif p["witness"] == "PERIM":
            g = transform(tr, src.perim_geom[p["id"]][0])
        else:
            g = Point(0, 0).buffer(w.r_m, 32)
        items.append(E.Item(p["witness"], g, date.fromisoformat(p["d0"]), date.fromisoformat(p["d1"]), p))
    if scar and scar.get("status") == "scar" and scar.get("geometry"):
        g = transform(tr, shape(scar["geometry"]))
        wit = "S2_SCAR" if scar["sensor"] == "s2" else "LANDSAT_SCAR"
        items.append(E.Item(wit, g, date.fromisoformat(scar["pre_date"]), date.fromisoformat(scar["post_date"]),
                            {"area_ha": scar["area_ha"], "threshold": scar["threshold"], "floor_m2": scar["floor_m2"],
                             "components": [c for c in scar["components"] if c["status"] == "accepted"]}))
    if scar:
        from pyproj import Transformer
        for h in scar.get("hotspots", []):
            t2 = Transformer.from_crs(f"EPSG:{h['epsg']}", "EPSG:4326", always_xy=True).transform
            wit = "S2_AF" if h["sensor"] == "s2" else "LANDSAT_AF"
            gs = []
            for x, y in zip(h["x"], h["y"]):
                lo, la = t2(x, y)
                gs.append(Point(*tr(lo, la)).buffer(HEAT_HALF[wit], 8))
            from shapely.ops import unary_union
            dd = date.fromisoformat(h["date"])
            items.append(E.Item(wit, unary_union(gs), dd, dd, {"item": h["item"], "n_pixels": h["n_pixels"]}))
    # an item only counts if it meets the disc (point sources were matched on the disc already)
    from shapely import make_valid
    for it in items:
        if not it.geom.is_valid:
            it.geom = make_valid(it.geom)
    disc = Point(0, 0).buffer(w.r_m, 64)
    return [it for it in items if it.geom.intersects(disc)]


def label_row(w, items, scar, perimeter_on=True) -> dict:
    from shapely.geometry import Point, mapping
    from shapely.ops import transform, unary_union
    from pyproj import Transformer

    tr_inv = Transformer.from_crs(standard.local_crs(w.LATITUDE, w.LONGITUDE), "EPSG:4326", always_xy=True).transform
    disc = Point(0, 0).buffer(w.r_m, 64)
    t, pairs = E.tier(items)
    pix = [it.geom for it in items if it.kind in ("HEAT", "SCAR")]
    if not pix and t != "record-only":
        pix = [it.geom for it in items if it.kind == "PERIMETER"]
    if pix:
        try:
            geom = unary_union(pix).intersection(disc)
        except Exception:  # GEOS topology error on unusual inputs: union after a zero buffer
            geom = unary_union([g.buffer(0) for g in pix]).intersection(disc)
        pixel_label = True
    else:
        geom = Point(0, 0).buffer(w.r_m, 4)   # the honest radius; 16 vertices are enough to carry it
        pixel_label = False
    reason = None
    st = (scar or {}).get("status")
    if t == "record-only":
        if not w.searched:
            reason = w.unsearched_reason
        elif st == "below_floor":
            reason = "below_floor"
        elif st in ("no_clear_look", "error", None):
            reason = "no_clear_look" if st != "error" else "no_clear_look (read error)"
        elif st in ("no_scar_clear", "rejected"):
            reason = "clear_look_nothing_found"
        else:
            reason = "clear_look_nothing_found"
    std = sorted({it.witness for it in items if it.witness in E.STANDARD})
    sg = [it.geom for it in items if it.witness in E.STANDARD]
    std_wkt = transform(tr_inv, unary_union(sg)).wkt if sg else None
    ev = [{"witness": it.witness, "kind": it.kind, "d0": str(it.d0), "d1": str(it.d1),
           **{k: v for k, v in it.detail.items() if k in ("time_utc", "frp", "conf", "sat", "area_ha", "id",
                                                             "area_km2", "threshold", "item", "n_pixels")}}
          for it in items]
    if items and t != "record-only":
        lab0 = max(it.d0 for it in items)
        lab1 = min(it.d1 for it in items)
        if lab0 > lab1:
            lab0, lab1 = min(it.d0 for it in items), max(it.d1 for it in items)
    else:
        lab0, lab1 = w.t0, w.t1
    return {
        "rid": w.rid, "tier": t, "pairs": json.dumps(pairs), "pixel_label": pixel_label,
        "std_label": bool(std), "std_witnesses": ",".join(std),
        "kinds": ",".join(sorted({it.kind for it in items})), "witnesses": ",".join(sorted({it.witness for it in items})),
        "n_items": len(items), "evidence": json.dumps(ev, default=str), "reason": reason,
        "scar_status": st, "scar_sensor": (scar or {}).get("sensor"), "scar_pre": (scar or {}).get("pre_date"),
        "scar_post": (scar or {}).get("post_date"), "scar_threshold": (scar or {}).get("threshold"),
        "scar_floor_m2": (scar or {}).get("floor_m2"), "scar_clear_frac": (scar or {}).get("clear_fraction"),
        "scar_area_ha": (scar or {}).get("area_ha"), "fire_m2_disc": ((scar or {}).get("states") or {}).get("fire_m2"),
        "unknown_m2_disc": ((scar or {}).get("states") or {}).get("unknown_m2"),
        "no_fire_m2_disc": ((scar or {}).get("states") or {}).get("no_fire_m2"),
        "label_t0": str(lab0), "label_t1": str(lab1),
        "geometry_wkt": transform(tr_inv, geom).wkt, "std_geometry_wkt": std_wkt,
    }


def heat_floors(lat: float, day_only=False) -> dict:
    """Edge-of-scan heat floors (m2 flaming area, 800 K) for the evidence list."""
    from .floor import Background
    d = {}
    for s in ["MODIS", "VIIRS", "AVHRR", "GOES"]:
        d[f"{s}_day"] = round(heat_floor_m2(s, None, Background(305, 300, 2, True)), 1)
        d[f"{s}_night"] = round(heat_floor_m2(s, None, Background(285, 285, 2, False)), 1)
    return d


def prepare_windows(w: pd.DataFrame, cfg) -> pd.DataFrame:
    w = w.copy()
    loc = cfg["location"]
    big = {"D", "E", "F", "G"}
    best = scar_floor_m2(PARAMS["t_abs"], 20.0, PARAMS["n_min"], PARAMS["dnbr_ref"])
    w["searched"] = True
    w["unsearched_reason"] = None
    unc = (w.r_loc_m > loc["r_loc_max_search_m"]) & ~w.FIRE_SIZE_CLASS.isin(big)
    w.loc[unc, ["searched", "unsearched_reason"]] = [False, "location_too_uncertain"]
    bf = w.area_m2 < best
    w.loc[bf & ~unc, ["searched", "unsearched_reason"]] = [False, "below_floor"]
    if "LATITUDE" in w:
        w.loc[w.LATITUDE.isna(), ["searched", "unsearched_reason"]] = [False, "no placebo location"]
    return w


def evaluate(name: str, w: pd.DataFrame, src: Sources, fod_big: PointIndex | None, perimeter_on=True,
             threads=40, params=None, extra_points: dict | None = None) -> pd.DataFrame:
    rd = run_dir(name)
    w = w[w.LATITUDE.notna()].copy() if "matched" not in w else w.copy()
    pts_p = rd / "points.json"
    if pts_p.exists():
        pts = json.loads(pts_p.read_text())
    else:
        pts = {}
        for r in w.itertuples():
            if pd.isna(r.LATITUDE):
                continue
            pts[r.rid] = {"pts": point_matches(src, r), "polys": polygon_matches(src, r, fod_big, perimeter_on)}
        pts_p.write_text(json.dumps(pts, default=str))
    heat = {"MODIS", "VIIRS_SNPP", "VIIRS_NOAA20", "GOES", "AVHRR", "HMS_ANALYST", "DNB"}
    heat_rids = {rid for rid, v in pts.items() if any(q["witness"] in heat for q in v["pts"])}
    heat_rids |= {rid for rid, v in (extra_points or {}).items() if v}
    scars = scar_stage(name, w[w.LATITUDE.notna()], threads=threads, params=params, heat_rids=heat_rids)
    for sc in scars.values():   # the label stage needs neither the look list nor the input hashes nor state shapes
        sc.pop("looks", None)
        sc.pop("inputs", None)
        st = sc.get("states") or {}
        st.pop("unknown", None)
        st.pop("fire", None)
    import pyarrow as pa
    import pyarrow.parquet as pq
    keep = [c for c in ["rid", "of_rid", "LATITUDE", "LONGITUDE", "r_m", "r_loc_m", "t0", "t1", "t1_source", "area_m2",
                        "FIRE_SIZE", "FIRE_SIZE_CLASS", "STATE", "FIRE_YEAR", "split", "searched", "unsearched_reason",
                        "MTBS_ID", "truth_id", "truth_source", "truth_kind"] if c in w]
    light_cols = keep + ["tier", "reason", "pixel_label", "std_label", "std_witnesses", "witnesses", "kinds",
                         "scar_status", "scar_sensor", "scar_threshold", "scar_floor_m2", "scar_area_ha",
                         "label_t0", "label_t1"] + (["geometry_wkt", "std_geometry_wkt", "pairs"] if "truth_id" in w else [])
    writer, parts, schema = None, [], None
    tmp = rd / "labels.parquet.part"
    CH = 20_000
    for i in range(0, len(w), CH):
        rows = []
        for r in w.iloc[i:i + CH].itertuples():
            if pd.isna(r.LATITUDE):
                rows.append({"rid": r.rid, "tier": "record-only", "reason": "no placebo location", "pixel_label": False,
                             "std_label": False})
                continue
            sc = scars.get(r.rid)
            items = build_items(r, pts[r.rid]["pts"] + list((extra_points or {}).get(r.rid, [])),
                                pts[r.rid]["polys"], sc, src)
            rows.append(label_row(r, items, sc, perimeter_on))
        chunk = w.iloc[i:i + CH][keep].merge(pd.DataFrame(rows), on="rid", how="left")
        for c in ("t0", "t1"):
            if c in chunk:
                chunk[c] = chunk[c].astype(str)
        if schema is not None:
            for f_ in schema:
                if f_.name not in chunk:
                    chunk[f_.name] = None
            chunk = chunk[[f_.name for f_ in schema]]
        tb = pa.Table.from_pandas(chunk, preserve_index=False)
        if writer is None:
            # columns empty in the first chunk are typed as strings (WKT, JSON, names)
            schema = pa.schema([pa.field(f_.name, pa.string()) if pa.types.is_null(f_.type) else f_
                                for f_ in tb.schema])
            writer = pq.ParquetWriter(tmp, schema, compression="zstd")
        writer.write_table(tb.cast(schema))
        parts.append(chunk[[c for c in light_cols if c in chunk]].copy())
        del rows, chunk, tb
    if writer is not None:
        writer.close()
        import os
        os.replace(tmp, rd / "labels.parquet")
    out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    return out

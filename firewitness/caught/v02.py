"""v0.2 (protocol/CAUGHT_PROTOCOL_v0.2.md): lift a probable scar label to verified by
(a) a second, independent scar sensor (Landsat 30 m beside Sentinel-2 20 m, or the reverse), or
(b) persistence: the scar still passes the candidate tests on a later clear date of the same sensor.

v0.1 labels, rules and numbers are not changed: v0.2 reads the v0.1 labels and adds a v0.2 tier beside them.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .scar import PARAMS, SENSORS, _nbr, item_date, scar_search, search, _query_for

V02 = {"persist_min_days": 10, "persist_max_days": 60, "persist_share": 0.5, "persist_min_clear": 0.5}


def _first_sensor(witnesses: str) -> str | None:
    w = set((witnesses or "").split(","))
    if "S2_SCAR" in w:
        return "s2"
    if "LANDSAT_SCAR" in w:
        return "landsat"
    return None


def persistence(res, sensor: str, lon: float, lat: float, run: str, p: dict) -> dict:
    """Same pre image, a later clear post image 10-60 days after the first post: share of the accepted pixels that
    still pass the candidate tests."""
    a = getattr(res, "_arrays", None)
    if a is None or not res.post_date:
        return {"persist": None, "why": "no first look"}
    S = SENSORS[sensor]
    grid = a["grid"]
    acc = a["accepted"]
    post0 = date.fromisoformat(res.post_date)
    items = search(S.collection, lon, lat, post0 + timedelta(days=V02["persist_min_days"]),
                   post0 + timedelta(days=V02["persist_max_days"]), _query_for(S))
    items = sorted([i for i in items if S.epsg(i) == grid.epsg and item_date(i) > post0 + timedelta(days=V02["persist_min_days"] - 1)],
                   key=item_date)
    pre = a["pre"]
    nbr0 = _nbr(pre)
    for it in items[: p["max_tries"]]:
        if S.cloud(it) > p["max_scene_cloud"]:
            continue
        clear = S.clear(it, grid, run, None)
        ok = acc & clear
        if acc.sum() == 0 or ok.sum() < V02["persist_min_clear"] * acc.sum():
            continue
        b = S.bands(it, grid, run, None)
        nbr1 = _nbr(b)
        cand = ((nbr0 - nbr1) >= res.threshold) & ((b["nir"] - pre["nir"]) < p["dnir"]) & \
               ((b["vis"] - pre["vis"]) < p["dvis"])
        if p.get("dswir1_max") is not None:
            cand &= (b["swir1"] - pre["swir1"]) < p["dswir1_max"]
        share = float((cand & ok).sum() / ok.sum())
        return {"persist": share >= V02["persist_share"], "share": round(share, 3), "date": str(item_date(it)),
                "item": it.id}
    return {"persist": None, "why": "no clear later scene"}


def second_sensor(res, sensor: str, lon, lat, r_m, t0, t1, area_m2, run, p) -> dict:
    other = "landsat" if sensor == "s2" else "s2"
    r2 = scar_search(lon, lat, r_m, t0, t1, area_m2, other, "small", run, p, hot=False)
    if r2.status != "scar" or r2.geometry is None or res.geometry is None:
        return {"second": False if r2.status in ("no_scar_clear", "rejected") else None, "status": r2.status,
                "sensor": other}
    meet = r2.geometry.intersects(res.geometry)
    overlap = not (date.fromisoformat(r2.pre_date) > date.fromisoformat(res.post_date) or
                   date.fromisoformat(res.pre_date) > date.fromisoformat(r2.post_date))
    return {"second": bool(meet and overlap), "status": r2.status, "sensor": other, "pre": r2.pre_date,
            "post": r2.post_date, "area_ha": round(r2.area_ha, 3)}


def check_one(args) -> dict:
    rid, lon, lat, r_m, t0, t1, area_m2, witnesses, run = args
    p = dict(PARAMS)
    out = {"rid": rid}
    try:
        s = _first_sensor(witnesses)
        out["first_sensor"] = s
        res = scar_search(lon, lat, r_m, t0, t1, area_m2, s, "small", run, p, hot=False)
        out["first_status"] = res.status
        if res.status != "scar":
            out["route"] = "none"
            out["why"] = "first look no longer a scar"
            return out
        out.update({f"persist_{k}": v for k, v in persistence(res, s, lon, lat, run, p).items()})
        out.update({f"second_{k}": v for k, v in second_sensor(res, s, lon, lat, r_m, t0, t1, area_m2, run, p).items()})
        routes = [n for n, k in (("second_sensor", "second_second"), ("persistence", "persist_persist")) if out.get(k)]
        out["route"] = "+".join(routes) if routes else "none"
    except Exception as e:
        out["route"] = "error"
        out["why"] = f"{type(e).__name__}: {e}"[:300]
    return out


def _chunk(chunk):
    import warnings
    from concurrent.futures import ThreadPoolExecutor
    warnings.filterwarnings("ignore")
    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(check_one, chunk))


def run_v02(labels: pd.DataFrame, ck_path, run: str, procs: int = 4) -> pd.DataFrame:
    """Checkpointed (JSON lines). labels: v0.1 labels with rid, LONGITUDE, LATITUDE, r_m, t0, t1, area_m2, tier,
    witnesses."""
    import multiprocessing as mp
    done = {}
    if ck_path.exists():
        for line in ck_path.read_text().splitlines():
            j = json.loads(line)
            if j.get("route") != "error":
                done[j["rid"]] = j
    sel = labels[(labels.tier == "probable") & labels.witnesses.fillna("").str.contains("S2_SCAR|LANDSAT_SCAR")]
    todo = sel[~sel.rid.isin(done)]
    args = [(r.rid, r.LONGITUDE, r.LATITUDE, r.r_m, pd.Timestamp(r.t0).date(), pd.Timestamp(r.t1).date(),
             r.area_m2, r.witnesses, run) for r in todo.itertuples()]
    chunks = [args[i:i + 16] for i in range(0, len(args), 16)]
    t = time.time()
    n = 0
    with ProcessPoolExecutor(procs, mp_context=mp.get_context("spawn"), max_tasks_per_child=8) as ex, \
            open(ck_path, "a") as f:
        for fu in as_completed([ex.submit(_chunk, c) for c in chunks]):
            for d in fu.result():
                f.write(json.dumps(d, default=str) + "\n")
                done[d["rid"]] = d
                n += 1
            f.flush()
            if n % 400 < 16:
                print(f"[v02 {run}] {n}/{len(args)} {n / (time.time() - t):.2f}/s", flush=True)
    return pd.DataFrame(list(done.values()))


def tier_v02(labels: pd.DataFrame, checks: pd.DataFrame) -> pd.DataFrame:
    """v0.2 tier beside the v0.1 tier; v0.1 columns untouched."""
    out = labels[["rid", "FIRE_SIZE_CLASS", "tier", "std_label", "searched"] +
                 [c for c in ("STATE", "FIRE_YEAR", "LATITUDE", "LONGITUDE") if c in labels]].copy()
    out = out.rename(columns={"tier": "tier_v01"})
    route = dict(zip(checks.rid, checks.route)) if len(checks) else {}
    out["route_v02"] = [route.get(r, "") for r in out.rid]
    lift = out.route_v02.isin(["second_sensor", "persistence", "second_sensor+persistence"])
    out["tier_v02"] = np.where((out.tier_v01 == "probable") & lift, "verified", out.tier_v01)
    return out


# ------------------------------------------------------------------ v0.2 sealed set (Minnesota 2021, WFIGS)
WFIGS = ("https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/WFIGS_Interagency_Perimeters/"
         "FeatureServer/0/query")


def build_sealed_v02(state: str = "US-MN", year: int = 2021) -> pd.DataFrame:
    """Record-like windows for the v0.2 sealed set (protocol v0.2 section 4). Called once, after the protocol."""
    import math
    from .perimeters import _ms, _query
    from .records import ACRE_M2, region, size_class, split_of

    cfg = region()
    where = (f"attr_POOState = '{state}' AND attr_FireDiscoveryDateTime >= DATE '{year}-01-01' AND "
             f"attr_FireDiscoveryDateTime < DATE '{year + 1}-01-01' AND poly_GISAcres < 300")
    g = _query(f"wfigs_v02_{state}_{year}", WFIGS, where,
               "OBJECTID,poly_IncidentName,poly_GISAcres,attr_FireDiscoveryDateTime,attr_ContainmentDateTime,"
               "attr_FireOutDateTime,attr_IncidentTypeCategory,attr_IrwinID")
    g = g[g.geometry.notna() & (g.poly_GISAcres > 0)].copy()
    g = g.drop_duplicates("attr_IrwinID", keep="first")
    d0 = _ms(g.attr_FireDiscoveryDateTime)
    d1 = _ms(g.attr_ContainmentDateTime).fillna(_ms(g.attr_FireOutDateTime))
    dflt = cfg["default_duration_days"]
    rows = []
    for r, a0, a1 in zip(g.itertuples(), d0, d1):
        c = r.geometry.representative_point()
        k = size_class(r.poly_GISAcres, cfg)
        e = a1 if (a1 is not None and not pd.isna(a1) and a1 >= a0 and (a1 - a0).days <= 180) else a0 + timedelta(days=dflt[k])
        a = r.poly_GISAcres * ACRE_M2
        pid = f"wfigs:{r.OBJECTID}"
        rows.append({"rid": "V02_" + pid, "truth_id": pid, "truth_source": "wfigs", "stratum": "primary_small",
                     "truth_kind": "rx" if str(r.attr_IncidentTypeCategory) == "RX" else "wildfire",
                     "LATITUDE": c.y, "LONGITUDE": c.x, "r_loc_m": 250.0, "r_fire_m": math.sqrt(a / math.pi),
                     "r_m": 250.0 + math.sqrt(a / math.pi), "area_m2": a, "FIRE_SIZE": r.poly_GISAcres,
                     "FIRE_SIZE_CLASS": k, "FIRE_YEAR": year, "STATE": state[-2:], "disc_date": a0,
                     "t0": a0 - timedelta(days=1), "t1": e + timedelta(days=1), "split": "sealed_v02",
                     "geometry_wkt": r.geometry.wkt})
    return pd.DataFrame(rows)

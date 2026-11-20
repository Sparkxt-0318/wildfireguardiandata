"""National run for the US: values, location and time, duplicates, links, permanent IDs, coverage. Times every stage (gate R2)."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ..core import Patch, PatchSet, hash_inputs, load_region
from . import canon, dedupe, geo, ids, link as L, link_tasks as LT, locate, paths, values

FOD_STR_COLS = ["FOD_ID", "FPA_ID", "SOURCE_SYSTEM_TYPE", "SOURCE_SYSTEM", "NWCG_REPORTING_AGENCY", "NWCG_REPORTING_UNIT_ID",
                "NWCG_REPORTING_UNIT_NAME", "SOURCE_REPORTING_UNIT", "SOURCE_REPORTING_UNIT_NAME", "LOCAL_FIRE_REPORT_ID",
                "LOCAL_INCIDENT_ID", "FIRE_CODE", "FIRE_NAME", "COMPLEX_NAME", "FIRE_YEAR", "DISCOVERY_DATE", "DISCOVERY_DOY",
                "DISCOVERY_TIME", "NWCG_CAUSE_CLASSIFICATION", "NWCG_GENERAL_CAUSE", "CONT_DATE", "CONT_DOY", "CONT_TIME",
                "FIRE_SIZE", "FIRE_SIZE_CLASS", "LATITUDE", "LONGITUDE", "OWNER_DESCR", "STATE", "COUNTY", "FIPS_CODE", "FIPS_NAME"]


def load_fod_strings(years=None) -> pd.DataFrame:
    c = sqlite3.connect(paths.WORK / "fpafod" / "Data" / "FPA_FOD_20260615.gpkg")
    q = "select " + ",".join(FOD_STR_COLS) + " from Fires"
    if years:
        q += " where FIRE_YEAR in (%s)" % ",".join(str(int(y)) for y in years)
    d = pd.read_sql(q, c)
    d = d.astype(object).where(d.notna(), "").astype(str)
    d.insert(0, "rid", "fod:" + d["FOD_ID"])
    return d


class Timer:
    def __init__(self):
        self.t0 = time.time(); self.stages = {}; self._t = self.t0

    def lap(self, name):
        now = time.time(); self.stages[name] = round(now - self._t, 1); self._t = now
        print(f"[{now - self.t0:7.1f}s] {name} ({self.stages[name]}s)", flush=True)


def locate_fod(fod: pd.DataFrame, ev: locate.Evidence, cfg, params: locate.Params, rel=None):
    """Tool 2 on FPA FOD, evaluated only where the point as reported disagrees with its own county or is invalid."""
    f = pd.DataFrame({"rid": fod.rid, "state": fod.STATE, "county": fod.FIPS_CODE, "lat_raw": fod.LATITUDE, "lon_raw": fod.LONGITUDE,
                      "start_raw": fod.DISCOVERY_DATE.str.replace("T00:00:00.0Z", "", regex=False), "report_raw": fod.CONT_DATE.str.replace("T00:00:00.0Z", "", regex=False),
                      "area_raw": fod.FIRE_SIZE, "uom_raw": "ACRES"})
    lat, lon, _ = locate.parse_latlon(f)
    cidx = ev.admin.locate_near(lat, lon, 3.0)
    counties, st_ab = ev.named_areas(f)
    sus = np.zeros(len(f), bool)
    for k in range(len(f)):
        cs = counties[k]
        if not np.isfinite(lat[k]) or not np.isfinite(lon[k]) or not locate._in_us(lat[k], lon[k], cfg):
            sus[k] = True
        elif cs and cidx[k] not in cs:
            sus[k] = True
        elif not cs and st_ab[k] is not None and st_ab[k] is not pd.NA and cidx[k] >= 0 and ev.admin.county["state_abbr"].iloc[cidx[k]] != st_ab[k]:
            sus[k] = True
    sub = f[sus].reset_index(drop=True)
    info = {"n_checked": int(len(f)), "n_suspicious": int(sus.sum())}
    if len(sub) == 0:
        return [], info
    if rel is None:
        rng = np.random.default_rng(0)
        yr = pd.to_numeric(fod.FIRE_YEAR, errors="coerce")
        devm = ~yr.isin(set(cfg["split"]["test_years"]) | {cfg["split"]["heldout_year"]}).to_numpy() if False else ~yr.isin(list(cfg["split"]["test_years"]) + [cfg["split"]["heldout_year"]]).to_numpy()
        key = pd.to_numeric(fod.FOD_ID, errors="coerce").fillna(0).astype("int64").to_numpy()
        pick = f[devm & (key % 11 == 0)].reset_index(drop=True)   # dev years only, chosen by id so adding a year changes nothing
        (wit, pri), _ = locate.fit_reliabilities(pick, ev, cfg, params)
        rel = (wit, {0: 0.98, 1: 0.02})
    cand, _, _ = locate.repair_locations(sub, ev, cfg, params, fitted=rel)
    dec = locate.decide(cand, len(sub), params)
    pats = locate.location_patches(sub, dec)
    # patches name the FOD columns
    out = [Patch(p.record_id, "LATITUDE" if p.field == "lat_raw" else "LONGITUDE", p.old, p.new, p.rule, p.evidence, p.confidence) for p in pats]
    info |= {"repairs": int((dec.action == "repair").sum()), "undecided": int((dec.action == "undecided").sum())}
    return out, info


def run_national(out_dir: Path, years=None, region="us", fit_models=None, skip_values=False) -> dict:
    """The whole US run. Writes patches, clean table, crosswalk, fires, parents, summary to out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    T = Timer()
    cfg = load_region(paths.REPO / "firewitness" / "records", region)
    params = locate.Params()
    res: dict = {"region": region}
    fod = load_fod_strings(years)
    input_hash = hash_inputs([paths.WORK / "fpafod" / "Data" / "FPA_FOD_20260615.gpkg"])
    T.lap("load FPA FOD")
    ps = PatchSet(tool="records.clean", meta={"region": region, "years": years})
    # 1 values
    if not skip_values:
        vp, vflags = values.clean_values(fod, "fpafod", cfg, "rid")
        ps.extend(vp)
        res["values"] = {"patches": len(vp), "flags": int(len(vflags)), "by_rule": pd.Series([p.rule for p in vp]).value_counts().to_dict()}
        T.lap("tool 1 values")
    # 2 location / time (suspicious rows only)
    ev = locate.Evidence(geo.Admin(cfg), geo.Detections(), geo.Scars())
    T.lap("load evidence (counties, FIRMS, MTBS)")
    lp, info = locate_fod(fod, ev, cfg, params)
    ps.extend(lp)
    res["location"] = info | {"patches": len(lp)}
    T.lap("tool 2 location")
    del fod, ev
    import gc; gc.collect()
    # 3 duplicates within FOD
    fc = pd.read_parquet(paths.CANON / "fod.parquet")
    if years:
        fc = fc[fc.year.isin(years)]
    fc = fc.reset_index(drop=True)
    d = fc.assign(ident=None, rid="fod:" + fc.fid.astype(str))
    dev = (LT.split_of(fc.year, cfg).to_numpy() == "dev")
    pairs, dmodel = dedupe.find(d, fit_mask=dev, cross_source_only=True)
    dp, keeper = dedupe.dedupe_patches(d, pairs, cross_source_only=True)
    ps.extend(dp)
    res["duplicates"] = {"pairs": int(len(pairs)), "linked": int((pairs.outcome == "link").sum()), "undecided": int((pairs.outcome == "undecided").sum()), "removed": len(dp)}
    T.lap("tool 3 duplicates")
    # 3b links
    lk = {}
    for name in ("fod_mtbs", "fod_ics"):
        Tk, pr, X, dec, model = LT.decide_all(name, None if not fit_models else LT.model_from_json(fit_models[name]))
        l = dec[dec.outcome == "link"]
        left, right = Tk["left"], Tk["right"]
        sel = left.fid.isin(fc.fid).to_numpy()[l.li.to_numpy()]
        l = l[sel]
        lk[name] = pd.DataFrame({"fid": left[Tk["lid"]].to_numpy()[l.li.to_numpy()], "src_id": right[Tk["rid"]].to_numpy()[l.ri.to_numpy()], "post": l.post.to_numpy()})
        res.setdefault("links", {})[name] = {"links": int(len(l)), "undecided": int((dec.outcome == "undecided").sum()), "model": LT.model_to_json(model)}
    T.lap("tool 3 links")
    # 4 IDs
    mtbs = pd.read_parquet(paths.CANON / "mtbs.parquet"); ics = pd.read_parquet(paths.CANON / "ics_inc.parquet")
    fires, xw, parents, isum = ids.build(fc, keeper, lk["fod_mtbs"], lk["fod_ics"], mtbs, ics)
    res["ids"] = isum
    fires.to_parquet(out_dir / "fires.parquet"); xw.to_parquet(out_dir / "crosswalk.parquet"); parents.to_parquet(out_dir / "complex_parents.parquet")
    T.lap("tool 4 ids")
    ps.input_sha256 = input_hash[str(paths.WORK / "fpafod" / "Data" / "FPA_FOD_20260615.gpkg")]["sha256"]
    ps.write(out_dir / "patches.jsonl")
    res["n_patches"] = len(ps)
    res["inputs"] = input_hash
    res["seconds"] = T.stages | {"total": round(time.time() - T.t0, 1)}
    (out_dir / "run_summary.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    import sys
    yrs = [int(y) for y in sys.argv[1].split(",")] if len(sys.argv) > 1 and sys.argv[1] != "all" else None
    r = run_national(paths.OUT / ("nat_" + ("all" if not yrs else "sub")), yrs)
    print(json.dumps({k: v for k, v in r.items() if k not in ("inputs",)}, indent=1, default=str)[:3000])

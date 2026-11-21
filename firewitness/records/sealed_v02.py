"""Open the v0.2 sealed set ONCE (protocol v0.2 section 4), with the rules frozen at the current commit.

Sealed set: every (source system x table x year) group of the years 2004, 2010, 2016, 2022; the state lists and the
national feed (WA, OK, AK, WFIGS) in full; the gazetteer incidents whose hash(number|year) mod 10 is 0, 1 or 2.
Refuses to run twice.
"""
from __future__ import annotations

import hashlib
import json
import subprocess

import numpy as np
import pandas as pd

from ..core import load_region
from . import geo, gazetteer as G, locate, paths, statelists as S, timeoffset as T, timeoffset_run as R
from .gates import wilson

OUT = paths.RESULTS / "data" / "sealed_v02.json"


def statelist_frames(cfg) -> pd.DataFrame:
    adm = geo.Admin(cfg)
    rows = []
    # WA 2008+: date is local midnight encoded in UTC ms, time hhmm local
    a = S._read(paths.RAW / "state_lists/wa_dnr_fire_statistics_2008_present.ndjson")
    d0 = pd.to_datetime(pd.to_numeric(a.DSCVR_DT, errors="coerce"), unit="ms", utc=True).dt.tz_convert("America/Los_Angeles").dt.tz_localize(None).dt.normalize()
    hh = pd.to_numeric(a.DSCVR_TM, errors="coerce")
    rows.append(pd.DataFrame({"rid": "wa:" + a.OBJECTID.astype(str), "table": "wa_dnr", "system": "wa_dnr", "lat": a.LAT_COORD.fillna(a._lat), "lon": a.LON_COORD.fillna(a._lon),
                              "start": d0 + pd.to_timedelta((hh // 100) * 60 + (hh % 100), unit="m"), "acres": a.ACRES_BURNED, "state": "WA", "inc": "wa:" + a.OBJECTID.astype(str)}))
    b = S._read(paths.RAW / "state_lists/ok_historical_fire_occurrence.ndjson")
    d0 = pd.to_datetime(pd.to_numeric(b.FireDiscoveryDate, errors="coerce"), unit="ms")
    hh = pd.to_numeric(b.FireDiscoveryTime, errors="coerce")
    rows.append(pd.DataFrame({"rid": "ok:" + b.OBJECTID.astype(str), "table": "ok_forestry", "system": "ok_forestry", "lat": b.Latitude.fillna(b._lat), "lon": b.Longitude.fillna(b._lon),
                              "start": d0.dt.normalize() + pd.to_timedelta((hh // 100) * 60 + (hh % 100), unit="m"), "acres": b.FinalFireAcreQuantity, "state": "OK", "inc": "ok:" + b.OBJECTID.astype(str)}))
    c = S._read(paths.RAW / "wfigs/WFIGS_Incident_Locations.ndjson")
    lat = c.InitialLatitude.fillna(c._lat); lon = c.InitialLongitude.fillna(c._lon)
    idx = adm.locate_near(lat.to_numpy(float), lon.to_numpy(float), 3.0)
    st = np.where(idx >= 0, adm.county["state_abbr"].to_numpy(dtype=object)[np.maximum(idx, 0)], None)
    rows.append(pd.DataFrame({"rid": "wfigs:" + c.OBJECTID.astype(str), "table": "wfigs", "system": "wfigs", "lat": lat, "lon": lon,
                              "start": pd.to_datetime(pd.to_numeric(c.FireDiscoveryDateTime, errors="coerce"), unit="ms"),
                              "acres": pd.to_numeric(c.FinalAcres, errors="coerce").fillna(pd.to_numeric(c.IncidentSize, errors="coerce")).fillna(pd.to_numeric(c.DiscoveryAcres, errors="coerce")),
                              "state": st, "inc": "wfigs:" + c.OBJECTID.astype(str)}))
    f = pd.concat(rows, ignore_index=True)
    f["year"] = f.start.dt.year
    return f


def group_row(fd, g, dev_conv):
    d, ul, uu = R.residual_inputs(fd, g)
    r = T.estimate_group(d, ul, uu, g.inc.to_numpy())
    return r


def run():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists: the v0.2 sealed set was already opened once")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=paths.REPO, capture_output=True, text=True).stdout.strip()
    cfg = load_region(paths.REPO / "firewitness" / "records", "us")
    res = {"frozen_rules_commit": commit}
    dev_pool = pd.read_json(paths.OUT / "timeoffset_dev" / "pooled_groups_final.json")
    conv = {(r.system, r.table): r.outcome for r in dev_pool.itertuples()}
    frames = [R.ics_frame(cfg), R.fod_frame(300.0), statelist_frames(cfg)]
    allr = pd.concat(frames, ignore_index=True)
    allr = allr[(allr.year >= 2001) & (allr.acres >= 300) & allr.state.notna() & allr.lat.notna() & allr.start.notna()]
    sealed = allr[allr.year.isin(R.SEALED_YEARS) | allr.table.isin(["wa_dnr", "ok_forestry", "wfigs"])]
    fd = T.FirstDetection(sorted(sealed.year.unique().astype(int)))
    rows = []
    for (sysm, tab, yr), g in sealed.groupby(["system", "table", "year"]):
        if len(g) < 5:
            continue
        r = group_row(fd, g, conv)
        dev = conv.get((sysm, tab), "table not in dev")
        rows.append({"system": sysm, "table": tab, "year": int(yr), "records_in_group": int(len(g)), "dev_table_outcome": dev, **r})
    tab = pd.DataFrame(rows)
    tab.to_json(paths.RESULTS / "data" / "sealed_v02_time_groups.json", orient="records", indent=1)
    res["time_groups"] = int(len(tab))
    res["time_outcomes"] = tab.outcome.value_counts().to_dict()
    big = tab[tab.n >= 30].copy()
    big["dev_utc"] = big.dev_table_outcome == "offset: recorded in UTC"
    big["gain_positive"] = big.gain_H1_over_H0 > 0
    agree = (big.dev_utc & big.gain_positive) | (~big.dev_utc & ~big.gain_positive)
    res["groups_with_30_fires"] = int(len(big))
    res["agree_with_dev_convention"] = int(agree.sum())
    res["agree_ci"] = wilson(int(agree.sum()), max(len(big), 1))
    # gazetteer
    Gz = G.Gazetteer(cfg)
    inc = pd.read_csv("/tmp/claude-0/gaz_incidents.csv") if False else None
    res["gazetteer"] = gazetteer_sealed(cfg, Gz)
    OUT.write_text(json.dumps(res, indent=1, default=float))
    return res


def gazetteer_sealed(cfg, Gz):
    from . import eval_published as E
    raw = pd.read_parquet(paths.CANON / "ics_raw_all.parquet").reset_index(drop=True)
    lat, lon, _ = locate.parse_latlon(raw)
    raw["lat0"], raw["lon0"] = lat, lon
    raw["year"] = pd.to_datetime(raw.start_raw, errors="coerce", format="mixed").dt.year.astype("Int64").astype(str)
    pub = E.load_published()
    pub = pub[~pub.year.isin(E.TEST)]
    leg = raw[(raw.src != "ics209_2014") & ~raw.year.isin(E.TEST)]
    g = leg.sort_values("rid").groupby(["number", "year"]).agg(lat0=("lat0", "first"), lon0=("lon0", "first"), state=("state", "first"), county=("county", "first"), desc=("location_desc", "first")).reset_index()
    m = pub.merge(g, on=["number", "year"], how="inner")
    m = m[(m.lat_c != 0) & m.lat_c.notna()]
    m = m[~((m.lat0.abs() > 1) & (m.lon0.abs() > 1))].copy()
    m["bucket"] = m.apply(lambda r: int(hashlib.sha256(f"{r.number}|{r.year}".encode()).hexdigest(), 16) % 10, axis=1)
    m = m[m.bucket <= 2].reset_index(drop=True)
    rows = []
    for _, r in m.iterrows():
        cn = [c.strip() for c in str(r.county).split(",")] if isinstance(r.county, str) and r.county.strip() else []
        st = r.state if isinstance(r.state, str) and len(r.state) == 2 else None
        x = Gz.match(r.desc, st, cn)
        if x["match_class"] == "matched":
            x["dist_km"] = float(geo.haversine_km(x["lat_gaz"], x["lon_gaz"], r.lat_c, r.long_c))
        x["number"], x["year"] = r.number, r.year
        rows.append(x)
    d = pd.DataFrame(rows)
    d.to_csv(paths.RESULTS / "data" / "sealed_v02_gazetteer.csv", index=False)
    mt = d[d.match_class == "matched"]
    ok = int((mt.get("dist_km", pd.Series(dtype=float)) <= mt.radius_km).sum()) if len(mt) else 0
    return {"incidents": int(len(d)), "classes": d.match_class.value_counts().to_dict(), "matched_published_inside_radius": ok,
            "matched_ci": wilson(ok, max(len(mt), 1)), "matched_within_5km": int((mt.dist_km <= 5).sum()) if len(mt) else 0}


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=float)[:3000])

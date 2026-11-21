"""Run the v0.2 time-offset estimator over groups (source system x table x year) and write patches for applied offsets."""
from __future__ import annotations

import json
import sqlite3
import sys

import numpy as np
import pandas as pd

from ..core import Patch, PatchSet, load_region
from . import locate, paths, timeoffset as T

SEALED_YEARS = {2004, 2010, 2016, 2022}


def _states_from_fips(series, fips_to_abbr):
    def f(x):
        if isinstance(x, str):
            x = x.strip()
            if len(x) == 2 and x.isdigit():
                return fips_to_abbr.get(x)
            if len(x) == 2:
                return x.upper()
        return None
    return series.map(f)


def ics_frame(cfg) -> pd.DataFrame:
    """Raw ICS-209 incident rows (one per incident) with v0.1 repaired locations."""
    d = pd.read_parquet(paths.CANON / "ics_raw_all.parquet").reset_index(drop=True)
    dec = pd.read_parquet(paths.OUT / "tool2_final" / "tool2_raw_ics.location_decisions.parquet")
    lat, lon, _ = locate.parse_latlon(d)
    rep = (dec.action == "repair").to_numpy()
    lat = np.where(rep, dec.alt_lat.to_numpy(), lat)
    lon = np.where(rep, dec.alt_lon.to_numpy(), lon)
    fips = {v: k for k, v in cfg["state_fips"].items()}
    f = pd.DataFrame({"rid": d.rid, "table": d.src, "system": d.src, "file_year": d.file_year, "inc": d.inc_key, "lat": lat, "lon": lon,
                      "start": pd.to_datetime(d.start_raw, errors="coerce", format="mixed"), "acres": locate.area_acres_of(d),
                      "state": _states_from_fips(d.state.astype("string"), fips), "start_raw": d.start_raw})
    f["year"] = f.start.dt.year
    return f.sort_values("rid").drop_duplicates("inc").reset_index(drop=True)


def fod_frame(min_acres=300.0) -> pd.DataFrame:
    c = sqlite3.connect(paths.WORK / "fpafod" / "Data" / "FPA_FOD_20260615.gpkg")
    d = pd.read_sql("select FOD_ID, SOURCE_SYSTEM, FIRE_YEAR, DISCOVERY_DATE, DISCOVERY_TIME, FIRE_SIZE, LATITUDE, LONGITUDE, STATE from Fires where FIRE_SIZE >= ?", c, params=(min_acres,))
    day = pd.to_datetime(d.DISCOVERY_DATE.str[:10], errors="coerce")
    hhmm = pd.to_numeric(d.DISCOVERY_TIME, errors="coerce")
    ok = hhmm.notna() & (hhmm >= 0) & (hhmm <= 2359) & ((hhmm % 100) < 60)
    start = day + pd.to_timedelta(np.where(ok, (hhmm // 100) * 60 + (hhmm % 100), np.nan), unit="m")
    f = pd.DataFrame({"rid": "fod:" + d.FOD_ID.astype(str), "table": "fpafod", "system": d.SOURCE_SYSTEM, "file_year": d.FIRE_YEAR.astype(str), "inc": "fod:" + d.FOD_ID.astype(str),
                      "lat": d.LATITUDE, "lon": d.LONGITUDE, "start": start, "acres": d.FIRE_SIZE, "state": d.STATE, "start_raw": d.DISCOVERY_DATE + " " + d.DISCOVERY_TIME.fillna("")})
    f["year"] = d.FIRE_YEAR.astype(int)
    return f[ok.to_numpy()].reset_index(drop=True)


def residual_inputs(fd: T.FirstDetection, g: pd.DataFrame):
    """Implied UTC starts under H0 (recorded = local) and H1 (recorded = UTC), and the first detection per fire."""
    st = g["start"].reset_index(drop=True)
    u_loc = T.local_to_utc_hours(st, g["state"].tolist())
    u_utc = T.naive_hours(st)
    lo, hi = np.fmin(u_loc, u_utc) - 24, np.fmax(u_loc, u_utc) + 96
    d = fd.first(g["lat"].to_numpy(), g["lon"].to_numpy(), lo, hi)
    return d, u_loc, u_utc


def run(include_sealed=False, min_acres=300.0, out=None):
    cfg = load_region(paths.REPO / "firewitness" / "records", "us")
    frames = [ics_frame(cfg), fod_frame(min_acres)]
    allr = pd.concat(frames, ignore_index=True)
    allr = allr[(allr.year >= 2001) & (allr.acres >= min_acres) & allr.state.notna() & allr.lat.notna()]
    if not include_sealed:
        allr = allr[~allr.year.isin(SEALED_YEARS)]
    fd = T.FirstDetection(sorted(allr.year.unique().astype(int)))
    rows, cache = [], {}
    for (sysm, tab, yr), g in allr.groupby(["system", "table", "year"]):
        if len(g) < 5:
            continue
        d, ul, uu = residual_inputs(fd, g)
        cache[(sysm, tab, int(yr))] = (d, ul, uu, g.inc.to_numpy(), g.rid.to_numpy())
        r = T.estimate_group(d, ul, uu, g.inc.to_numpy())
        rows.append({"system": sysm, "table": tab, "year": int(yr), "records_in_group": int(len(g)), **{k: v for k, v in r.items()}})
    # pooled level per (system, table)
    pooled = []
    keys = {}
    for (sysm, tab, yr) in cache:
        keys.setdefault((sysm, tab), []).append(yr)
    for (sysm, tab), yrs in keys.items():
        d = np.concatenate([cache[(sysm, tab, y)][0] for y in yrs]); ul = np.concatenate([cache[(sysm, tab, y)][1] for y in yrs])
        uu = np.concatenate([cache[(sysm, tab, y)][2] for y in yrs]); cl = np.concatenate([cache[(sysm, tab, y)][3] for y in yrs])
        r = T.estimate_group(d, ul, uu, cl)
        pooled.append({"system": sysm, "table": tab, "years": f"{min(yrs)}-{max(yrs)}", **r})
    return pd.DataFrame(rows), pd.DataFrame(pooled), cache


if __name__ == "__main__":
    yr, pl, cache = run()
    out = paths.OUT / "timeoffset_dev"
    out.mkdir(parents=True, exist_ok=True)
    import pickle
    pickle.dump(cache, open(out / "cache.pkl", "wb"))
    yr.to_json(out / "year_groups.json", orient="records", indent=1)
    pl.to_json(out / "pooled_groups.json", orient="records", indent=1)
    print(pl[["system", "table", "years", "n", "outcome"]].to_string())
    print(yr.outcome.value_counts().to_string())


# ------------------------------------------------------------------ planted trials (gate T3) and application
def planted_trials(cache, groups=(("ics209_imsr", "ics209_imsr"), ("FS-FIRESTAT", "fpafod")), sizes=(100, 300, 1000), trials=30, seed=0):
    """Plant a table-wide UTC recording, and (separately) nothing, into subsamples of tables recorded as local time."""
    from .gates import wilson
    rng = np.random.default_rng(seed)
    keys = {}
    for (s, t, y) in cache:
        keys.setdefault((s, t), []).append(y)
    out = {}
    for n in sizes:
        rec_utc = rec_clean_utc = tot = 0
        shifts = {"+8": 0, "-8": 0}
        for (s, t) in groups:
            ys = keys[(s, t)]
            d, ul, uu, cl = [np.concatenate([cache[(s, t, y)][i] for y in ys]) for i in (0, 1, 2, 3)]
            ok = np.isfinite(d)
            d, ul, uu, cl = d[ok], ul[ok], uu[ok], cl[ok]
            if len(d) < n:
                continue
            for _ in range(trials):
                idx = rng.choice(len(d), n, replace=False)
                dd, a, b, c = d[idx], ul[idx], uu[idx], cl[idx]
                tot += 1
                # planted UTC: the recorded clock time is the UTC time of the start
                r = T.estimate_group(dd, 2 * a - b, a, c, n_boot=200)
                rec_utc += r["outcome"] == "offset: recorded in UTC"
                # unplanted (false positive)
                r0 = T.estimate_group(dd, a, b, c, n_boot=200)
                rec_clean_utc += r0["outcome"].startswith("offset")
                # planted fixed shifts of +/-8 h on the recorded times (a shift of the table, read as local)
                for k in (8, -8):
                    rk = T.estimate_group(dd, a + k, b + k, c, n_boot=200)
                    shifts[f"{k:+d}".replace("+8", "+8")] += rk["outcome"].startswith("offset")
        out[n] = {"trials": tot, "planted_utc_found": rec_utc, "planted_utc_ci": wilson(rec_utc, max(tot, 1)),
                  "unplanted_false_offsets": rec_clean_utc, "unplanted_ci": wilson(rec_clean_utc, max(tot, 1)),
                  "planted_fixed_shift_flagged": shifts}
    return out


def apply_offsets(pooled: pd.DataFrame, yearly: pd.DataFrame, cfg) -> tuple[list, pd.DataFrame]:
    """Patches (start_raw / FOD discovery fields) for every record of each table found to be recorded in UTC."""
    ics = pd.read_parquet(paths.CANON / "ics_raw_all.parquet").reset_index(drop=True)
    fips = {v: k for k, v in cfg["state_fips"].items()}
    patches, summary = [], []
    for _, p in pooled[pooled.outcome == "offset: recorded in UTC"].iterrows():
        sysm, tab = p["system"], p["table"]
        bad_years = set(yearly[(yearly.system == sysm) & (yearly.table == tab) & (yearly.n >= 30) & (yearly.gain_H1_over_H0 <= 0)].year)
        if tab.startswith("ics209"):
            g = ics[ics.src == sysm]
            st = pd.to_datetime(g.start_raw, errors="coerce", format="mixed")
            states = _states_from_fips(g.state.astype("string"), fips)
            ok = st.notna() & states.notna() & ~st.dt.year.isin(bad_years)
            loc = T.utc_to_local_naive(st[ok], states[ok])
            moved = (loc.dt.normalize() != st[ok].dt.normalize()) & loc.notna()
            fmt = (lambda t: t.strftime("%-m/%-d/%Y %-I:%M:%S %p")) if sysm == "ics209_2014" else (lambda t: t.strftime("%Y-%m-%d %H:%M:%S"))
            for rid, old, new in zip(g.rid[ok], g.start_raw[ok], loc):
                if pd.isna(new):
                    continue
                patches.append(Patch(rid, "start_raw", old, fmt(new), "time:offset_utc_to_local",
                                     {"group": f"{sysm}/{tab}", "n_fires": int(p["n"]), "gain_H1": round(float(p["gain_H1_over_H0"]), 3), "gain_ci": [round(x, 3) for x in p["gain_H1_ci"]], "convention": "recorded in UTC"}, 0.7))
            summary.append({"system": sysm, "table": tab, "rows": int(len(g)), "rows_with_usable_time_and_state": int(ok.sum()), "records_changed_clock_time": int(ok.sum()), "records_calendar_date_moved": int(moved.sum())})
        else:
            c = sqlite3.connect(paths.WORK / "fpafod" / "Data" / "FPA_FOD_20260615.gpkg")
            d = pd.read_sql("select FOD_ID, FIRE_YEAR, DISCOVERY_DATE, DISCOVERY_DOY, DISCOVERY_TIME, STATE from Fires where SOURCE_SYSTEM = ?", c, params=(sysm,))
            day = pd.to_datetime(d.DISCOVERY_DATE.str[:10], errors="coerce")
            hhmm = pd.to_numeric(d.DISCOVERY_TIME, errors="coerce")
            ok = day.notna() & hhmm.notna() & (hhmm >= 0) & (hhmm <= 2359) & ((hhmm % 100) < 60) & d.STATE.notna() & ~d.FIRE_YEAR.isin(bad_years)
            st = day[ok] + pd.to_timedelta((hhmm[ok] // 100) * 60 + (hhmm[ok] % 100), unit="m")
            loc = T.utc_to_local_naive(st, d.STATE[ok])
            moved = (loc.dt.normalize() != st.dt.normalize()) & loc.notna()
            for (_, r), new in zip(d[ok].iterrows(), loc):
                if pd.isna(new):
                    continue
                ev = {"group": f"{sysm}/fpafod", "n_fires": int(p["n"]), "gain_H1": round(float(p["gain_H1_over_H0"]), 3), "gain_ci": [round(x, 3) for x in p["gain_H1_ci"]], "convention": "recorded in UTC"}
                rid = f"fod:{r.FOD_ID}"
                nd = new.strftime("%Y-%m-%dT00:00:00.0Z"); nt = new.strftime("%H%M"); ndoy = str(new.dayofyear)
                if nd != r.DISCOVERY_DATE:
                    patches.append(Patch(rid, "DISCOVERY_DATE", r.DISCOVERY_DATE, nd, "time:offset_utc_to_local", ev, 0.7))
                    if ndoy != str(r.DISCOVERY_DOY):
                        patches.append(Patch(rid, "DISCOVERY_DOY", str(r.DISCOVERY_DOY), ndoy, "time:offset_utc_to_local", ev, 0.7))
                if nt != str(r.DISCOVERY_TIME):
                    patches.append(Patch(rid, "DISCOVERY_TIME", str(r.DISCOVERY_TIME), nt, "time:offset_utc_to_local", ev, 0.7))
            summary.append({"system": sysm, "table": "fpafod", "rows": int(len(d)), "rows_with_usable_time_and_state": int(ok.sum()), "records_changed_clock_time": int(ok.sum()), "records_calendar_date_moved": int(moved.sum())})
    return patches, pd.DataFrame(summary)

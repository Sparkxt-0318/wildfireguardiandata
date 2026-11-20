"""Tool 2: location and time repair.

For each record, candidate repairs are generated (sign flip, swapped axes, degree-minute formats,
time-zone offset, day-month order). Each candidate (and the value as reported) is checked against
independent evidence the rules did not write: the county or state named in the record, satellite
detections in the window, and the burn scar. Each evidence source is a witness with reliabilities m, u
fitted without labels (EM); the combined posterior decides. A repair is applied only if its posterior is
high and higher than the posterior of the value as reported; otherwise the record is left alone and
flagged "undecided". Every applied repair is a Patch.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..core import Patch, PatchSet, Witness
from . import em, geo
from .io import parse_dt, to_num

WITNESSES = ["admin", "fire_window", "scar", "peer"]
HIDDEN = re.compile(r"[ ​‌‍﻿⁠­\u0000-\u0008\u000b\u000c\u000e-\u001f]")
EPOCH = pd.Timestamp("1970-01-01")
DAY = np.timedelta64(1, "D")


def _days(ts: pd.Series) -> np.ndarray:
    return ((ts - EPOCH) / pd.Timedelta(days=1)).to_numpy(float)


@dataclass
class Params:
    hi: float = 0.95
    lo: float = 0.05
    margin: float = 0.25
    radius_km: float = 5.0
    win_before: int = 1
    win_after: int = 10
    scar_tol_km: float = 1.0
    scar_win: int = 30
    time_tol: int = 3
    normalise_time: bool = True
    det_min_acres: float = 300.0
    none_weight: float = 0.05
    enable: tuple = ("sign_flip_lon", "sign_flip_lat", "sign_flip_both", "swap_axes", "swap_axes_neg", "dm_dd",
                     "dm_swap", "tz_shift", "day_month")


# ------------------------------------------------------------------ parsing
def clean_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype("string").str.replace(HIDDEN, "", regex=True).str.strip(), errors="coerce").astype(float)


def area_acres_of(df: pd.DataFrame) -> np.ndarray:
    """Reported area in acres, converting only when the unit field says hectares / square miles / km2."""
    a = clean_num(df["area_raw"]).to_numpy()
    u = df["uom_raw"].astype("string").str.lower().fillna("")
    f = np.ones(len(df))
    f = np.where(u.str.contains("hect"), 2.47105, f)
    f = np.where(u.str.contains("sq") & u.str.contains("mi"), 640.0, f)
    return a * f


def parse_latlon(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Numeric lat, lon as reported; degree-minute columns (1999-2002) are combined as deg + min/60 with the
    sign convention of that table (longitude west positive). Returns lat, lon, from_dm flag."""
    lat = clean_num(df["lat_raw"]).to_numpy()
    lon = clean_num(df["lon_raw"]).to_numpy()
    dm = np.zeros(len(df), bool)
    if "latdeg" in df and df["latdeg"].notna().any():
        la = clean_num(df["latdeg"]) + clean_num(df["latmin"]) / 60.0
        lo = clean_num(df["londeg"]) + clean_num(df["lonmin"]) / 60.0
        use = np.isnan(lat) & la.notna().to_numpy()
        lat = np.where(use, la.to_numpy(), lat)
        lon = np.where(use, lo.to_numpy(), lon)
        dm = use
    return lat, lon, dm


# ------------------------------------------------------------------ candidates
def _in_us(lat, lon, cfg):
    la0, la1 = cfg["lat_range"]
    lo0, lo1 = cfg["lon_range"]
    return (lat >= la0) & (lat <= la1) & (lon >= lo0) & (lon <= lo1)


def _dm_to_dd(v):
    """ddmm.mmm or dddmm.mmm packed degree-minute to decimal degrees (sign kept)."""
    a = np.abs(v)
    deg = np.floor(a / 100.0)
    minute = a - deg * 100.0
    ok = (minute < 60)
    out = np.where(ok, deg + minute / 60.0, np.nan)
    return np.sign(v) * out


def make_candidates(lat, lon, cfg, enable) -> pd.DataFrame:
    """Rows: (i, kind, lat, lon). kind 'as_reported' for the value interpreted as it stands."""
    n = len(lat)
    rows = [("as_reported", lat, lon)]
    # the value interpreted as it stands for a west-positive table is invalid; candidates below fix it
    if "sign_flip_lon" in enable:
        rows.append(("sign_flip_lon", lat, -lon))
    if "sign_flip_lat" in enable:
        rows.append(("sign_flip_lat", -lat, lon))
    if "sign_flip_both" in enable:
        rows.append(("sign_flip_both", -lat, -lon))
    if "swap_axes" in enable:
        rows.append(("swap_axes", lon, lat))
    if "swap_axes_neg" in enable:
        rows.append(("swap_axes_neg", lon, -lat))
        rows.append(("swap_axes_neg", -lon, lat))
    if "dm_dd" in enable:
        rows.append(("dm_dd", _dm_to_dd(lat), _dm_to_dd(lon)))
        rows.append(("dm_dd", _dm_to_dd(lat), -_dm_to_dd(lon)))
    if "dm_swap" in enable:
        rows.append(("dm_swap", _dm_to_dd(lon), _dm_to_dd(lat)))
        rows.append(("dm_swap", _dm_to_dd(lon), -_dm_to_dd(lat)))
    out = []
    for kind, a, b in rows:
        a, b = np.asarray(a, float), np.asarray(b, float)
        ok = np.isfinite(a) & np.isfinite(b) & _in_us(a, b, cfg)
        if kind != "as_reported":
            changed = ~(np.isclose(a, lat, equal_nan=True) & np.isclose(b, lon, equal_nan=True))
            ok &= changed
        idx = np.flatnonzero(ok)
        out.append(pd.DataFrame({"i": idx, "kind": kind, "lat": a[idx], "lon": b[idx]}))
    c = pd.concat(out, ignore_index=True)
    # collapse duplicate coordinate candidates produced by different kinds for the same record
    c = c.drop_duplicates(subset=["i", "lat", "lon"], keep="first").reset_index(drop=True)
    return c


# ------------------------------------------------------------------ evidence
class Evidence:
    def __init__(self, admin: geo.Admin, det: geo.Detections | None, scars: geo.Scars | None, peers: geo.Detections | None = None):
        self.admin, self.det, self.scars, self.peers = admin, det, scars, peers

    def named_areas(self, df: pd.DataFrame):
        """Per record: set of allowed county row indices (may be empty) and state abbreviation (or None)."""
        a = self.admin
        n = len(df)
        st = df["state"].astype("string").str.strip()
        abbr = st.where(st.str.len() == 2, None)
        abbr = abbr.str.upper()
        # FIPS-coded state (2014+): 2 digits
        fips = st.where(st.str.fullmatch(r"\d{2}"), None)
        abbr = abbr.where(~abbr.str.fullmatch(r"\d{2}", na=False), None)
        abbr = abbr.fillna(fips.map(a.fips_to_abbr))
        st_ab = abbr.to_numpy(dtype=object)
        counties: list[tuple[int, ...]] = []
        cty = df["county"].astype("string")
        for k in range(n):
            s = st_ab[k]
            c = cty.iloc[k]
            res: tuple[int, ...] = ()
            if s is not None and s is not pd.NA and c is not pd.NA and c is not None:
                c = str(c).strip()
                if re.fullmatch(r"\d{3}", c):
                    j = a.by_fips.get(a.abbr_to_fips.get(s, "") + c)
                    res = (j,) if j is not None else ()
                else:
                    hits = []
                    for nm in geo.county_names(c):
                        hits += a.by_state_name.get((s, nm), [])
                    res = tuple(sorted(set(hits)))
            counties.append(res)
        return counties, st_ab

    def observe(self, df, cand, start_day, params: Params, area_acres=None):
        """(len(cand), 3) int8 matrix: admin, fire_window, scar; 1 agree, 0 disagree, -1 unknown."""
        a = self.admin
        counties, st_ab = self.named_areas(df)
        obs = np.full((len(cand), len(WITNESSES)), -1, dtype=np.int8)
        i = cand["i"].to_numpy()
        lat, lon = cand["lat"].to_numpy(), cand["lon"].to_numpy()
        cidx = a.locate_near(lat, lon, 3.0)
        cstate = np.where(cidx >= 0, a.county["state_abbr"].to_numpy(dtype=object)[np.maximum(cidx, 0)], None)
        for r in range(len(cand)):
            k = i[r]
            cs = counties[k]
            if cs:
                # a neighbouring county is also tolerated (boundary rounding): require the point inside or within 3 km
                obs[r, 0] = 1 if cidx[r] in cs else 0
            elif st_ab[k] is not None and st_ab[k] is not pd.NA:
                obs[r, 0] = 1 if cstate[r] == st_ab[k] else 0
        if self.det is not None:
            d0 = start_day[i] - params.win_before
            d1 = start_day[i] + params.win_after
            d0 = np.where(np.isfinite(d0), d0, -1e9).astype(np.int64)
            d1 = np.where(np.isfinite(d1), d1, -1e9).astype(np.int64)
            cnt, first = self.det.window_stats(lat, lon, d0, d1, params.radius_km)
            have_sat = np.isfinite(start_day[i]) & (start_day[i] > 11_000)  # from Nov 2000
            obs[have_sat, 1] = (cnt[have_sat] > 0).astype(np.int8)
        if self.scars is not None:
            m = self.scars.near(lat, lon, start_day[i], params.scar_tol_km, params.scar_win)
            # a scar is expected only for fires large enough to be mapped (MTBS: 1000 acres east, 500 west;
            # we use 2000 acres to stay clear of the threshold); smaller fires give no information
            big = np.zeros(len(i), bool) if area_acres is None else (np.nan_to_num(area_acres[i], nan=0.0) >= 2000)
            obs[:, 2] = np.where(m, 1, np.where(big & np.isfinite(start_day[i]), 0, -1))
        if self.peers is not None:
            # another source (FPA FOD) should list a fire near this point within days of the start
            okp = np.isfinite(start_day[i])
            d0 = np.where(okp, start_day[i] - 7, -1e9).astype(np.int64); d1 = np.where(okp, start_day[i] + 7, -1e9).astype(np.int64)
            cnt, _ = self.peers.window_stats(lat, lon, d0, d1, 3.0)
            obs[okp, 3] = (cnt[okp] > 0).astype(np.int8)
        return obs


def fit_reliabilities(df: pd.DataFrame, ev: Evidence, cfg: dict, params: Params, seed: int = 0, min_km: float = 500.0):
    """Fit witness reliabilities m, u without labels.

    Pairs: (a) each record's location as reported (group 0, prior fitted); (b) placebo pairs: the same record
    given the location of a random other record at least min_km away (group 2, prior fixed ~0, a destroyed link).
    """
    rng = np.random.default_rng(seed)
    df = df.reset_index(drop=True)
    lat, lon, _ = parse_latlon(df)
    start_day = _days(parse_dt(df["start_raw"]))
    ok = np.flatnonzero(_in_us(lat, lon, cfg))
    ident = pd.DataFrame({"i": ok, "kind": "as_reported", "lat": lat[ok], "lon": lon[ok]})
    perm = rng.permutation(ok)
    for _ in range(5):  # push placebo pairs far apart
        far = geo.haversine_km(lat[ok], lon[ok], lat[perm], lon[perm]) >= min_km
        again = rng.permutation(ok)
        perm = np.where(far, perm, again)
    plc = pd.DataFrame({"i": ok, "kind": "placebo", "lat": lat[perm], "lon": lon[perm]})
    pair = pd.concat([ident, plc], ignore_index=True)
    obs = ev.observe(df, pair, start_day, params, area_acres_of(df))
    grp = np.where(pair["kind"] == "as_reported", 0, 2)
    return em.fit_grouped(obs, grp, WITNESSES, init_priors={0: 0.95}, fixed={2: 1e-4}), (obs, grp)


# ------------------------------------------------------------------ main
def repair_locations(df: pd.DataFrame, ev: Evidence, cfg: dict, params: Params | None = None,
                     fit_on: np.ndarray | None = None, fitted=None):
    """Returns (PatchSet-ready list of Patch, decisions DataFrame, fitted (witnesses, priors))."""
    params = params or Params()
    df = df.reset_index(drop=True)
    lat, lon, dm = parse_latlon(df)
    start = parse_dt(df["start_raw"])
    start_day = _days(start)
    cand = make_candidates(lat, lon, cfg, params.enable)
    obs = ev.observe(df, cand, start_day, params, area_acres_of(df))
    grp = (cand["kind"] != "as_reported").astype(int).to_numpy()
    if fitted is None:
        fitdf = df if fit_on is None else df[fit_on]
        (wit, pri), _ = fit_reliabilities(fitdf, ev, cfg, params)
        pri = {0: min(pri.get(0, 0.95), 0.995), 1: 0.02}
    else:
        wit, pri = fitted
    prior = np.where(grp == 0, pri.get(0, 0.95), pri.get(1, 0.05))
    cand["post"] = em.posterior(obs, wit, prior)
    cand["n_info"] = (obs >= 0).sum(1)
    for j, w in enumerate(WITNESSES):
        cand[w] = obs[:, j]
    return cand, (wit, pri), (lat, lon, start)


def decide(cand: pd.DataFrame, n_rows: int, params: Params) -> pd.DataFrame:
    """Per record: chosen candidate or none. Applied only if post >= hi and beats the as-reported posterior by margin."""
    ident = cand[cand["kind"] == "as_reported"].set_index("i")["post"]
    alt = cand[cand["kind"] != "as_reported"].sort_values("post", ascending=False)
    best = alt.drop_duplicates("i").set_index("i")
    second = alt.groupby("i")["post"].apply(lambda s: s.iloc[1] if len(s) > 1 else 0.0)
    dec = pd.DataFrame(index=range(n_rows))
    dec["p_as_reported"] = ident.reindex(dec.index)
    dec["alt_kind"] = best["kind"].reindex(dec.index)
    dec["alt_lat"] = best["lat"].reindex(dec.index)
    dec["alt_lon"] = best["lon"].reindex(dec.index)
    dec["p_alt"] = best["post"].reindex(dec.index)
    dec["p_alt2"] = second.reindex(dec.index).fillna(0.0)
    p_id = dec["p_as_reported"].fillna(0.0)
    p_alt = dec["p_alt"].fillna(0.0)
    unique = (p_alt - dec["p_alt2"]) >= params.margin
    has_id = dec["p_as_reported"].notna()
    has_alt = dec["p_alt"].notna()
    repair = (p_alt >= params.hi) & ((p_alt - p_id) >= params.margin) & unique
    undecided = ~repair & has_alt & ((~has_id) | ((p_alt > p_id) & (p_alt >= 0.5)))
    dec["action"] = np.where(repair, "repair", np.where(undecided, "undecided", "keep"))
    return dec


def location_patches(df: pd.DataFrame, dec: pd.DataFrame, orig_lat_field="lat_raw", orig_lon_field="lon_raw") -> list[Patch]:
    patches = []
    rep = dec[dec["action"] == "repair"]
    for i, r in rep.iterrows():
        rid = df["rid"].iloc[i]
        ev = {"kind": r["alt_kind"], "p_repair": round(float(r["p_alt"]), 4), "p_as_reported": None if pd.isna(r["p_as_reported"]) else round(float(r["p_as_reported"]), 4),
              "evidence": ["admin", "fire_window", "scar"]}
        conf = float(r["p_alt"])
        if r["alt_kind"].startswith("dm") and "latdeg" in df and pd.notna(df["latdeg"].iloc[i]):
            pass
        lat_new, lon_new = f"{r['alt_lat']:.6f}", f"{r['alt_lon']:.6f}"
        old_lat, old_lon = df[orig_lat_field].iloc[i], df[orig_lon_field].iloc[i]
        if str(old_lat) != lat_new:
            patches.append(Patch(rid, "lat", None if pd.isna(old_lat) else str(old_lat), lat_new, f"loc:{r['alt_kind']}", ev, conf))
        if str(old_lon) != lon_new:
            patches.append(Patch(rid, "lon", None if pd.isna(old_lon) else str(old_lon), lon_new, f"loc:{r['alt_kind']}", ev, conf))
    return patches


# ================================================================== time
TIME_WITNESSES = ["order", "first_detection", "scar_date"]


def _swap_day_month(ts: pd.Series) -> pd.Series:
    ok = ts.notna() & (ts.dt.day <= 12) & (ts.dt.day != ts.dt.month)
    out = ts.copy()
    idx = ok[ok].index
    sw = [pd.Timestamp(year=t.year, month=t.day, day=t.month, hour=t.hour, minute=t.minute, second=t.second) for t in ts[idx]]
    out.loc[idx] = sw
    out[~ok] = pd.NaT
    return out


def _tz_hours(state_abbr, cfg) -> np.ndarray:
    tz = {"ET": -5, "CT": -6, "MT": -7, "PT": -8}
    et = set("CT DE DC FL GA IN KY ME MD MA MI NH NJ NY NC OH PA RI SC TN VT VA WV".split())
    ct = set("AL AR IL IA KS LA MN MS MO NE ND OK SD TX WI".split())
    mt = set("AZ CO ID MT NM UT WY".split())
    pt = set("CA NV OR WA".split())
    h = []
    for s in state_abbr:
        s = s if isinstance(s, str) else None
        h.append(tz["ET"] if s in et else tz["CT"] if s in ct else tz["MT"] if s in mt else tz["PT"] if s in pt else (-9 if s == "AK" else -10 if s == "HI" else np.nan))
    return np.array(h, float)


def make_time_candidates(start: pd.Series, state_abbr, enable) -> pd.DataFrame:
    rows = [pd.DataFrame({"i": np.flatnonzero(start.notna()), "kind": "as_reported", "start": start[start.notna()].to_numpy()})]
    if "day_month" in enable:
        sw = _swap_day_month(start)
        ok = sw.notna()
        rows.append(pd.DataFrame({"i": np.flatnonzero(ok), "kind": "day_month", "start": sw[ok].to_numpy()}))
    if "tz_shift" in enable:
        h = _tz_hours(state_abbr, None)
        ok = start.notna().to_numpy() & np.isfinite(h)
        # recorded as UTC, local = UTC + offset (negative offsets move the clock back, possibly across midnight)
        sh = start[ok] + pd.to_timedelta(h[ok], unit="h")
        keep = sh.dt.normalize().to_numpy() != start[ok].dt.normalize().to_numpy()
        idx = np.flatnonzero(ok)[keep]
        rows.append(pd.DataFrame({"i": idx, "kind": "tz_shift", "start": sh[keep].to_numpy()}))
    return pd.concat(rows, ignore_index=True)


def observe_time(ev: Evidence, cand: pd.DataFrame, lat, lon, report: pd.Series, params: Params, area=None) -> np.ndarray:
    i = cand["i"].to_numpy()
    sd = ((pd.to_datetime(cand["start"]) - EPOCH) / pd.Timedelta(days=1)).to_numpy(float)
    obs = np.full((len(cand), 3), -1, dtype=np.int8)
    rep = ((report - EPOCH) / pd.Timedelta(days=1)).to_numpy(float)[i]
    ok = np.isfinite(rep)
    obs[ok, 0] = ((rep[ok] >= sd[ok] - 1) & (rep[ok] <= sd[ok] + 400)).astype(np.int8)
    la, lo = lat[i], lon[i]
    if ev.det is not None:
        okd = np.isfinite(la) & np.isfinite(lo) & (sd > 11_000)
        near = np.full(len(cand), 0, int)
        d0 = np.where(okd, sd - 1, -1e9).astype(np.int64); d1 = np.where(okd, sd + 7, -1e9).astype(np.int64)
        c_in, _ = ev.det.window_stats(la, lo, d0, d1, params.radius_km)
        e0 = np.where(okd, sd - 90, -1e9).astype(np.int64); e1 = np.where(okd, sd + 90, -1e9).astype(np.int64)
        c_wide, _ = ev.det.window_stats(la, lo, e0, e1, params.radius_km)
        obs[okd & (c_in > 0), 1] = 1
        obs[okd & (c_in == 0) & (c_wide > 0), 1] = 0
    if ev.scars is not None:
        okd = np.isfinite(la) & np.isfinite(lo) & np.isfinite(sd)
        near3 = ev.scars.near(la, lo, sd, 1.0, 3)
        near400 = ev.scars.near(la, lo, sd, 1.0, 400)
        obs[okd & near3, 2] = 1
        obs[okd & ~near3 & near400, 2] = 0
    if area is not None and params.det_min_acres > 0:
        small = np.nan_to_num(area[i], nan=0.0) < params.det_min_acres
        obs[small, 1:] = -1          # satellites cannot be expected to see a small fire: no evidence either way
    return obs


def repair_times(df: pd.DataFrame, ev: Evidence, lat, lon, cfg: dict, params: Params | None = None, seed: int = 0,
                 fitted=None, fit_mask: np.ndarray | None = None):
    params = params or Params()
    df = df.reset_index(drop=True)
    start = parse_dt(df["start_raw"])
    report = parse_dt(df["report_raw"])
    st = df["state"].astype("string").str.upper().str.strip()
    ab = st.where(st.str.len() == 2, None)
    ab = ab.where(~ab.str.fullmatch(r"\d{2}", na=False), None).fillna(st.map(lambda x: ev.admin.fips_to_abbr.get(x) if isinstance(x, str) else None)).to_numpy(dtype=object)
    cand = make_time_candidates(start, ab, params.enable)
    area = area_acres_of(df)
    obs = observe_time(ev, cand, lat, lon, report, params, area)
    grp = (cand["kind"] != "as_reported").astype(int).to_numpy()
    if fitted is None:
        rng = np.random.default_rng(seed)
        base = cand[cand["kind"] == "as_reported"]
        if fit_mask is not None:
            base = base[fit_mask[base["i"].to_numpy()]]
        shift = pd.to_timedelta(rng.choice([-1, 1], len(base)) * rng.integers(20, 200, len(base)), unit="D")
        plc = pd.DataFrame({"i": base["i"].to_numpy(), "kind": "placebo", "start": (pd.to_datetime(base["start"]) + shift).to_numpy()})
        pair = pd.concat([base, plc], ignore_index=True)
        o2 = observe_time(ev, pair, lat, lon, report, params, area)
        g2 = np.where(pair["kind"] == "as_reported", 0, 2)
        wit, pri = em.fit_grouped(o2, g2, TIME_WITNESSES, init_priors={0: 0.97}, fixed={2: 1e-4})
        pri = {0: min(pri.get(0, 0.97), 0.995), 1: 0.03}
    else:
        wit, pri = fitted
    prior = np.where(grp == 0, pri.get(0, 0.97), pri.get(1, 0.03))
    cand["post"] = em.posterior(obs, wit, prior)
    if params.normalise_time:
        # one reading of the date is true: compare the candidates of a record with each other (odds), keeping a small
        # weight for "none of these", so that evidence against the date as reported also counts for its alternatives
        odds = cand["post"] / (1 - cand["post"]).clip(lower=1e-9)
        tot = odds.groupby(cand["i"]).transform("sum") + params.none_weight
        cand["post"] = (odds / tot).clip(0, 1)
    for j, w in enumerate(TIME_WITNESSES):
        cand[w] = obs[:, j]
    return cand, (wit, pri), (start, report)


def decide_time(cand: pd.DataFrame, n_rows: int, params: Params) -> pd.DataFrame:
    ident = cand[cand["kind"] == "as_reported"].set_index("i")["post"]
    alt = cand[cand["kind"] != "as_reported"].sort_values("post", ascending=False)
    best = alt.drop_duplicates("i").set_index("i")
    dec = pd.DataFrame(index=range(n_rows))
    dec["p_as_reported"] = ident.reindex(dec.index)
    dec["alt_kind"] = best["kind"].reindex(dec.index)
    dec["alt_start"] = best["start"].reindex(dec.index)
    dec["p_alt"] = best["post"].reindex(dec.index)
    p_id, p_alt = dec["p_as_reported"].fillna(0.0), dec["p_alt"].fillna(0.0)
    repair = (p_alt >= params.hi) & ((p_alt - p_id) >= params.margin)
    dec["action"] = np.where(repair, "repair", np.where((p_alt > p_id) & (p_alt >= 0.5), "undecided", "keep"))
    return dec


def time_patches(df: pd.DataFrame, dec: pd.DataFrame) -> list[Patch]:
    out = []
    for i, r in dec[dec["action"] == "repair"].iterrows():
        old = df["start_raw"].iloc[i]
        new = pd.Timestamp(r["alt_start"]).strftime("%Y-%m-%d %H:%M:%S")
        ev = {"kind": r["alt_kind"], "p_repair": round(float(r["p_alt"]), 4),
              "p_as_reported": None if pd.isna(r["p_as_reported"]) else round(float(r["p_as_reported"]), 4)}
        out.append(Patch(df["rid"].iloc[i], "start_raw", None if pd.isna(old) else str(old), new, f"time:{r['alt_kind']}", ev, float(r["p_alt"])))
    return out

"""Gate tests R3 / R4: planted errors, do-no-harm.

Reference-clean records are those whose location agrees with the county named in the record AND with an
independent observation (satellite detections in the window or the burn scar). Errors are planted into a copy of a
random part of them; the tools never see the plan.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..core import load_region
from . import geo, locate, paths


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return ((c - h) / den, (c + h) / den)


def reference_clean(df: pd.DataFrame, ev: locate.Evidence, cfg, params, fitted):
    """Boolean mask of rows whose as-reported location is independently corroborated."""
    cand, _, (lat, lon, start) = locate.repair_locations(df, ev, cfg, params, fitted=fitted)
    ident = cand[cand.kind == "as_reported"].set_index("i")
    ok = np.zeros(len(df), bool)
    good = ident[(ident.admin == 1) & ((ident.fire_window == 1) | (ident.scar == 1)) & (ident.post >= 0.99)].index.to_numpy()
    ok[good] = True
    return ok


def _fmt(x):
    return f"{x:.6f}"


def plant_location(df: pd.DataFrame, idx: np.ndarray, kind: str, rng) -> tuple[pd.DataFrame, pd.Series]:
    """Return a copy of df with `kind` of error planted at rows idx, and the original (lat, lon) as strings."""
    out = df.copy()
    lat = pd.to_numeric(out.loc[out.index[idx], "lat_raw"], errors="coerce").to_numpy()
    lon = pd.to_numeric(out.loc[out.index[idx], "lon_raw"], errors="coerce").to_numpy()
    if kind == "sign_flip_lon":
        nl, no = lat, -lon
    elif kind == "sign_flip_lat":
        nl, no = -lat, lon
    elif kind == "swap_axes":
        nl, no = lon, lat
    elif kind == "dm_dd":
        nl = np.floor(np.abs(lat)) * 100 + (np.abs(lat) % 1) * 60
        no = -(np.floor(np.abs(lon)) * 100 + (np.abs(lon) % 1) * 60)
    else:
        raise KeyError(kind)
    out.loc[out.index[idx], "lat_raw"] = [_fmt(v) for v in nl]
    out.loc[out.index[idx], "lon_raw"] = [_fmt(v) for v in no]
    return out, pd.DataFrame({"lat": lat, "lon": lon}, index=out.index[idx])


def recovery_location(df_clean, ev, cfg, params, fitted, classes=("sign_flip_lon", "sign_flip_lat", "swap_axes", "dm_dd"),
                      n_per=300, seed=0):
    """Plant, run tool 2, count exact recoveries (within 2e-6 deg) and wrong repairs. Returns per-class results."""
    rng = np.random.default_rng(seed)
    ref = np.flatnonzero(reference_clean(df_clean, ev, cfg, params, fitted))
    res = {"n_reference_clean": int(len(ref)), "classes": {}}
    pool = rng.permutation(ref)
    for ci, kind in enumerate(classes):
        idx = np.sort(pool[ci * n_per:(ci + 1) * n_per])
        if len(idx) == 0:
            continue
        planted, orig = plant_location(df_clean, idx, kind, rng)
        cand, _, (lat0, lon0, _) = locate.repair_locations(planted, ev, cfg, params, fitted=fitted)
        dec = locate.decide(cand, len(planted), params)
        d = dec.iloc[idx]
        rep = d.action.to_numpy() == "repair"
        exact = rep & (np.abs(d.alt_lat.to_numpy() - orig.lat.to_numpy()) < 2e-6) & (np.abs(d.alt_lon.to_numpy() - orig.lon.to_numpy()) < 2e-6)
        wrong = rep & ~exact
        und = d.action.to_numpy() == "undecided"
        n = len(idx)
        res["classes"][kind] = {"n": n, "recovered": int(exact.sum()), "recall": float(exact.mean()), "ci": wilson(int(exact.sum()), n),
                                "wrong_repair": int(wrong.sum()), "undecided": int(und.sum()), "missed": int((~rep & ~und).sum())}
    return res


def harm_on_clean(df_clean, ev, cfg, params, fitted):
    """Run tool 2 on reference-clean rows with nothing planted: how many are altered?"""
    ref = np.flatnonzero(reference_clean(df_clean, ev, cfg, params, fitted))
    sub = df_clean.iloc[ref].reset_index(drop=True)
    cand, _, _ = locate.repair_locations(sub, ev, cfg, params, fitted=fitted)
    dec = locate.decide(cand, len(sub), params)
    n = len(sub)
    k = int((dec.action == "repair").sum())
    return {"n_reference_clean": n, "altered": k, "rate": k / max(n, 1), "ci": wilson(k, n)}


def recovery_time(df_clean, ev, cfg, params, fitted_loc, fitted_time=None, classes=("day_month", "tz_shift"), n_per=300, seed=1):
    """Plant date errors into reference-clean rows (location corroborated, a detection in the window) and test tool 2's time repair."""
    rng = np.random.default_rng(seed)
    ref = np.flatnonzero(reference_clean(df_clean, ev, cfg, params, fitted_loc))
    lat, lon, _ = locate.parse_latlon(df_clean)
    start = locate.parse_dt(df_clean["start_raw"])
    res = {"classes": {}}
    pool = rng.permutation(ref)
    st = df_clean["state"].astype("string").str.upper().str.strip()
    ab = st.where(st.str.len() == 2, None)
    ab = ab.where(~ab.str.fullmatch(r"\d{2}", na=False), None).fillna(st.map(lambda x: ev.admin.fips_to_abbr.get(x) if isinstance(x, str) else None)).to_numpy(dtype=object)
    tzh = locate._tz_hours(ab, cfg)
    for ci, kind in enumerate(classes):
        picks = []
        for i in pool[ci * 5000:]:
            t = start.iloc[i]
            if pd.isna(t):
                continue
            if kind == "day_month" and t.day <= 12 and t.day != t.month:
                picks.append(i)
            if kind == "tz_shift" and np.isfinite(tzh[i]) and (t + pd.Timedelta(hours=float(tzh[i]))).normalize() != t.normalize():
                picks.append(i)
            if len(picks) >= n_per:
                break
        idx = np.array(sorted(picks))
        planted = df_clean.copy()
        orig = start.iloc[idx]
        if kind == "day_month":
            new = [pd.Timestamp(year=t.year, month=t.day, day=t.month, hour=t.hour, minute=t.minute, second=t.second) for t in orig]
        else:
            # true local start was recorded in UTC: recorded = local - offset (offset negative) -> later clock time
            new = [t - pd.Timedelta(hours=float(tzh[i])) for t, i in zip(orig, idx)]
        # our tz_shift candidate = recorded + offset, so plant recorded such that recorded + offset = original
        planted.loc[planted.index[idx], "start_raw"] = [pd.Timestamp(x).strftime("%Y-%m-%d %H:%M:%S") for x in new]
        cand, _, _ = locate.repair_times(planted, ev, lat, lon, cfg, params, fitted=fitted_time) if fitted_time else locate.repair_times(planted, ev, lat, lon, cfg, params)
        dec = locate.decide_time(cand, len(planted), params)
        d = dec.iloc[idx]
        rep = d.action.to_numpy() == "repair"
        exact = rep & (pd.to_datetime(d.alt_start).to_numpy() == orig.to_numpy())
        und = d.action.to_numpy() == "undecided"
        n = len(idx)
        res["classes"][kind] = {"n": n, "recovered": int(exact.sum()), "recall": float(exact.mean()) if n else float("nan"), "ci": wilson(int(exact.sum()), n),
                                "wrong_repair": int((rep & ~exact).sum()), "undecided": int(und.sum()), "missed": int((~rep & ~und).sum())}
    return res


def distinct_pairs_test(radius_km=10.0, day_window=3.0, seed=0):
    """R3(b): MTBS events with different ids whose perimeters do not intersect are distinct fires. The duplicate step,
    run without identifiers, must not link any such pair (names, size and place alone must keep them apart)."""
    from . import dedupe, link as L
    mt = pd.read_parquet(paths.CANON / "mtbs.parquet").reset_index(drop=True)
    sc = geo.Scars()
    rec = mt.assign(ident=None, source="mtbs", rid=mt.mid)
    pairs = dedupe.self_pairs(rec, radius_km, day_window)
    ga, gb = sc.geoms[pairs.li.to_numpy()], sc.geoms[pairs.ri.to_numpy()]
    import shapely
    distinct = ~shapely.intersects(ga, gb)
    pairs = pairs[distinct].reset_index(drop=True)
    from . import link_tasks as LT
    out, model = dedupe.find(rec.iloc[:0].assign(), None) if False else (None, None)
    X = L.compare(rec, rec, pairs, dedupe.FIELDS if rec.ident.notna().any() else ["dist", "day", "size", "name"])
    # model fitted without labels on all candidate pairs (including these), like the real run
    allp = dedupe.self_pairs(rec, 3.0, 3.0)
    fields = ["dist", "day", "size", "name"]
    Xa = L.compare(rec, rec, allp, fields)
    m = L.fit_fs(Xa, fields, init_prior=0.02)
    post = m.posterior(L.compare(rec, rec, pairs, fields))
    return {"distinct_pairs": int(len(pairs)), "linked": int((post >= 0.97).sum()), "undecided": int(((post > 0.05) & (post < 0.95)).sum()), "max_posterior": float(post.max()) if len(post) else 0.0}

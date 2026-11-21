"""Mechanical selection of the 29 fires (see NOTES.md for the justification of every rule).

    cd /home/user/wildfireguardiandata && python3 -m firewitness.fuel.fires29.select

Stage 1  (attributes only)  GeoMAC 2017-2019 records grouped by uniquefireidentifier; keep wildfires in the
         contiguous US with 20-600 km2 final area, >=8 distinct perimeter datetimes spanning >=4 days, no gap > 5 days.
Stage 2  (geometry)         download the candidates' perimeters, recompute area from the polygons (EPSG:5070),
         download LF2016 FBFM40 on the final AOI and compute the dominant fuel group in the final perimeter.
Stage 2b: drop fires whose first perimeter already covers >50% of the final area, or <50% burnable fuel cells.
Stage 3  (choice)           deterministic greedy pick of exactly 29: <=4 per state, maximise states then fuel-group
         diversity, ties by incident name (alphabetical), then id. No randomness.
fires29/excluded.json ({id: reason}) lists fires dropped after a failed build; select simply skips them and re-picks.
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from ..fetch import lfps
from ..grid import read_tif
from . import perimeters as P

HERE = Path(__file__).resolve().parent
CATALOG = HERE / "catalog.json"
EXCLUDED = HERE / "excluded.json"
N_FIRES = 29
MAX_PER_STATE = 4
MIN_KM2, MAX_KM2 = 20.0, 600.0
MIN_PERIMS, MIN_SPAN_DAYS, MAX_GAP_DAYS = 8, 4.0, 5.0
MAX_FIRST_FRAC = 0.5            # first perimeter <= 50% of the final area, else the arrival raster is mostly the constant 0
MIN_BURNABLE_FRAC = 0.5          # share of final-perimeter cells with a burnable fuel model (101-204)
RX_NAME = re.compile(r"\b(?:rx|prescribed|pile|piles|broadcast|understory burn)\b", re.I)

GROUPS = {"GR": range(101, 110), "GS": range(121, 125), "SH": range(141, 150), "TU": range(161, 166),
          "TL": range(181, 190), "SB": range(201, 205)}
# dominant fuel group = class of the FBFM40 mode group in the final perimeter (GS, grass-shrub, is the "mixed" class)
CLASS_OF = {"GR": "grass", "GS": "mixed", "SH": "shrub", "TU": "timber", "TL": "timber", "SB": "timber"}
CLASSES = ["grass", "shrub", "timber", "mixed"]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def fire_id(year, state, name) -> str:
    return f"{year}_{state}_{slug(name)}"


def stage1() -> pd.DataFrame:
    df = P.fetch_attribute_table()
    df["u"] = df["uniquefireidentifier"].astype(str).str.strip()
    df = df[df.perimeterdatetime.notna() & df.u.str.match(P.UID_RE)].copy()
    df["t"] = pd.to_datetime(df.perimeterdatetime, unit="ms", utc=True)
    rows = []
    for u, g in df.groupby("u"):
        ts = sorted(g.t.unique())
        last = g[g.t == g.t.max()]
        names = g.incidentname.astype(str).str.strip()
        rows.append(dict(
            u=u, name=names.mode().iloc[0], state=g.state.astype(str).str.strip().mode().iloc[0],
            year=int(u[:4]), layer=g.layer.iloc[0], n_times=len(ts),
            t0=pd.Timestamp(ts[0]), t1=pd.Timestamp(ts[-1]),
            span_days=(pd.Timestamp(ts[-1]) - pd.Timestamp(ts[0])).total_seconds() / 86400,
            gap_ok=P.checks_gap([pd.Timestamp(x) for x in ts], MAX_GAP_DAYS),
            km2_attr=float(last.gisacres.sum()) / P.ACRES_PER_KM2, km2_max=float(g.gisacres.max()) / P.ACRES_PER_KM2,
            irwin=str(g.irwinid.dropna().iloc[0]) if g.irwinid.notna().any() else "",
            complex=bool((g.incomplex.astype(str).str.strip().str.upper() == "Y").any())))
    s = pd.DataFrame(rows)
    keep = (s.year.between(2017, 2019) & s.state.isin(P.CONUS) & ~s.name.str.contains(RX_NAME)
            & (s.km2_max >= MIN_KM2 * 0.8) & (s.km2_max <= MAX_KM2 * 1.25)  # loose here; exact area from geometry in stage 2
            & (s.n_times >= MIN_PERIMS) & (s.span_days >= MIN_SPAN_DAYS) & s.gap_ok)
    c = s[keep].copy()
    return c.reset_index(drop=True)


def fuel_stats(fbfm: np.ndarray, mask: np.ndarray) -> dict:
    v = fbfm[mask]
    cnt = {g: int(np.isin(v, list(r)).sum()) for g, r in GROUPS.items()}
    burn = sum(cnt.values())
    n = int(mask.sum())
    cls = {c: 0 for c in CLASSES}
    for g, k in cnt.items():
        cls[CLASS_OF[g]] += k
    share = {c: (cls[c] / burn if burn else 0.0) for c in CLASSES}
    mode_group = max(cnt, key=lambda g: (cnt[g], g)) if burn else "NB"  # mode over the six burnable fuel groups
    dom = CLASS_OF.get(mode_group, "nonburnable")
    return dict(dominant=dom, mode_group=mode_group, burnable_frac=burn / max(n, 1),
                class_share={c: round(share[c], 3) for c in CLASSES}, group_counts=cnt)


def stage2_one(row: dict) -> dict:
    from rasterio import features
    u = row["u"]
    fc = P.fetch_perimeters(u, row["layer"])
    per = P.dissolve_by_time(fc)
    from shapely.ops import unary_union
    final4326 = unary_union([g for _, g in per])
    final5070 = P.to_5070(final4326)
    km2 = final5070.area / 1e6
    times = [t for t, _ in per]
    first_frac = P.to_5070(per[0][1]).area / final5070.area
    out = dict(row, km2=km2, first_frac=first_frac, n_perims=len(per), t0=str(times[0]), t1=str(times[-1]),
               span_days=(times[-1] - times[0]).total_seconds() / 86400, gap_ok=P.checks_gap(times, MAX_GAP_DAYS))
    ok = (MIN_KM2 <= km2 <= MAX_KM2 and len(per) >= MIN_PERIMS and out["span_days"] >= MIN_SPAN_DAYS and out["gap_ok"])
    if not ok:
        out["fuel"] = None
        return out
    grid = P.aoi_grid(final4326)
    cand = P.RAW / "_candidates" / u / "fbfm40.tif"
    path = lfps.fetch("FBFM40", 2016, grid, cand)
    fb, _ = read_tif(path, grid)
    mask = features.rasterize([(final5070, 1)], out_shape=grid.shape, transform=grid.transform, fill=0, dtype="uint8").astype(bool)
    out["fuel"] = fuel_stats(fb, mask)
    return out


def stage2(cand: pd.DataFrame, workers: int = 4) -> list[dict]:
    cache = P.SRC / "stage2.json"
    done = json.loads(cache.read_text()) if cache.exists() else {}
    todo = [r for r in cand.to_dict("records") if r["u"] not in done]

    def run(r):
        try:
            res = stage2_one(r)
            res = json.loads(json.dumps(res, default=str))
            return r["u"], res
        except Exception as e:  # noqa: BLE001
            print("stage2 FAILED", r["u"], r["name"], repr(e)[:200], flush=True)
            return r["u"], None

    with ThreadPoolExecutor(workers) as ex:
        for i, (u, res) in enumerate(ex.map(run, todo)):
            if res is not None:
                done[u] = res
                cache.write_text(json.dumps(done))
            print(f"stage2 {i + 1}/{len(todo)} {u}", flush=True)
    return [done[u] for u in cand.u if u in done]


def choose(cands: list[dict], n=N_FIRES, per_state=MAX_PER_STATE) -> list[dict]:
    """Deterministic greedy. Score of a candidate, lexicographic (larger tuple wins):
    (new state, fewest already-chosen fires of its fuel class, fewest of its state), then alphabetical name, id."""
    pool = sorted(cands, key=lambda c: (c["name"].lower(), c["id"]))
    chosen, st, fg = [], Counter(), Counter()
    while len(chosen) < n:
        best, best_key = None, None
        for c in pool:
            if c in chosen or st[c["state"]] >= per_state:
                continue
            key = (st[c["state"]] == 0, -fg[c["dominant"]], -st[c["state"]])
            if best_key is None or key > best_key:  # strict > keeps the alphabetically first among equals
                best, best_key = c, key
        if best is None:
            break
        chosen.append(best)
        st[best["state"]] += 1
        fg[best["dominant"]] += 1
    return chosen


def main():
    excluded = json.loads(EXCLUDED.read_text()) if EXCLUDED.exists() else {}
    c1 = stage1()
    print("stage1 candidates:", len(c1), flush=True)
    s2 = stage2(c1)
    cands = []
    for r in s2:
        if r.get("first_frac", 1.0) > MAX_FIRST_FRAC:
            continue
        if not r.get("fuel") or r["fuel"]["dominant"] == "nonburnable" or r["fuel"]["burnable_frac"] < MIN_BURNABLE_FRAC:
            continue
        cid = fire_id(r["year"], r["state"], r["name"])
        if cid in excluded:
            continue
        cands.append(dict(id=cid, uid=r["u"], name=r["name"], state=r["state"], year=r["year"], area_km2=round(r["km2"], 2), first_perimeter_frac=round(r["first_frac"], 3),
                          dominant=CLASS_OF.get(r["fuel"]["mode_group"], "nonburnable"), mode_group=r["fuel"]["mode_group"],
                          class_share=r["fuel"]["class_share"], burnable_frac=round(r["fuel"]["burnable_frac"], 3),
                          n_perimeters=r["n_perims"], first_perimeter=r["t0"], last_perimeter=r["t1"],
                          layer=r["layer"], complex=r["complex"]))
    ids = Counter(c["id"] for c in cands)
    for c in cands:  # disambiguate same-name fires in one state/year
        if ids[c["id"]] > 1:
            c["id"] += "_" + c["uid"].split("-")[-1].lower()
    (P.SRC / "candidates_after_stage2.json").parent.mkdir(parents=True, exist_ok=True)
    (P.SRC / "candidates_after_stage2.json").write_text(json.dumps(cands, indent=1))
    print("candidates after stage 2:", len(cands), Counter(c["state"] for c in cands), Counter(c["dominant"] for c in cands))
    chosen = sorted(choose(cands), key=lambda c: c["id"])
    CATALOG.write_text(json.dumps(chosen, indent=1) + "\n")
    print("chosen", len(chosen), Counter(c["state"] for c in chosen), Counter(c["dominant"] for c in chosen))


if __name__ == "__main__":
    main()

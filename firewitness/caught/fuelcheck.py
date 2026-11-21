"""Scar area against mapped perimeters by fuel type (grass, shrub, timber), dev truth fires only; and sealed
recall by fuel type re-tabulated from the existing sealed run (no re-run, no re-tuning)."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from .fetch import RAW_ROOT
from .landcover import lc_class
from .records import ACRE_M2

FUEL = {10: "timber", 20: "shrub", 30: "grass"}


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def fuel_of(lat, lon):
    return FUEL.get(lc_class(lat, lon), "other")


def dev_ratios(run: str = "truth_dev_r3") -> pd.DataFrame:
    from pyproj import Transformer
    from shapely import wkt
    from shapely.geometry import shape
    from shapely.ops import transform

    from .standard import local_crs

    rd = RAW_ROOT / "derived_caught" / "runs" / run
    t = pd.read_parquet(rd / "caught.parquet").drop_duplicates("rid")
    t = t[t.stratum.isin(["primary_small", "reference_large"])]
    sc = {}
    for line in open(rd / "scar.jsonl"):
        j = json.loads(line)
        sc[j["rid"]] = j
    rows = []
    for r in t.itertuples():
        j = sc.get(r.rid)
        if not j or j.get("status") not in ("scar", "no_scar_clear", "rejected"):
            continue
        poly = wkt.loads(r.truth_wkt)
        c = poly.representative_point()
        mapped_ha = r.area_m2 / 1e4
        area = float(j.get("area_ha") or 0.0) if j["status"] == "scar" else 0.0
        inside = 0.0
        if j["status"] == "scar" and j.get("geometry"):
            tr = Transformer.from_crs("EPSG:4326", local_crs(c.y, c.x), always_xy=True).transform
            inside = transform(tr, shape(j["geometry"]).buffer(0)).intersection(transform(tr, poly.buffer(0))).area / 1e4
        acc = [x for x in j.get("components", []) if x["status"] == "accepted"]
        rows.append({"rid": r.rid, "stratum": r.stratum, "size_class": r.FIRE_SIZE_CLASS, "fuel": fuel_of(c.y, c.x),
                     "mapped_ha": mapped_ha, "scar": j["status"] == "scar", "scar_ha": area,
                     "ratio": area / mapped_ha if mapped_ha > 0 else np.nan,
                     "inside_frac": inside / mapped_ha if mapped_ha > 0 else np.nan,
                     "threshold": j.get("threshold"), "sensor": j.get("sensor"),
                     "comp_median_dnbr": float(np.median([x["median_dnbr"] for x in acc])) if acc else np.nan})
    return pd.DataFrame(rows)


def summarize_ratios(d: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (strat, fuel), g in [(("all", f), d[d.fuel == f]) for f in ["grass", "shrub", "timber", "other"]] + \
            [((s, f), d[(d.stratum == s) & (d.fuel == f)]) for s in ["primary_small", "reference_large"]
             for f in ["grass", "shrub", "timber"]]:
        s = g[g.scar]
        k = int((s.ratio < 0.2).sum())
        lo, hi = wilson(k, len(s))
        q = s.ratio.quantile([0.25, 0.5, 0.75]) if len(s) else pd.Series([np.nan] * 3, index=[0.25, 0.5, 0.75])
        qi = s.inside_frac.quantile([0.5]) if len(s) else pd.Series([np.nan], index=[0.5])
        out.append({"stratum": strat, "fuel": fuel, "looks_clear": len(g), "scars": len(s),
                    "ratio_q25": q[0.25], "ratio_median": q[0.5], "ratio_q75": q[0.75],
                    "below_0.2": k, "share_below_0.2": k / len(s) if len(s) else np.nan, "wilson_lo": lo, "wilson_hi": hi,
                    "inside_frac_median": qi[0.5],
                    "verdict": ("under-measures" if len(s) >= 10 and lo > 0.25 else
                                "not clear" if len(s) >= 10 else "too few")})
    return pd.DataFrame(out)


def floor_by_fuel(d: pd.DataFrame, n_min: int = 8) -> pd.DataFrame:
    """Scar floor (protocol section 7) with dNBR_ref taken per fuel from the scars found on dev (median component
    dNBR), and T the median threshold of that fuel's looks; Sentinel-2 20 m and Landsat 30 m."""
    rows = []
    for f in ["grass", "shrub", "timber"]:
        g = d[d.fuel == f]
        ref = float(g.comp_median_dnbr.median())
        t = float(g.threshold.median())
        for sensor, px in [("Sentinel-2", 20.0), ("Landsat", 30.0)]:
            fl = (math.sqrt(n_min) + 1) ** 2 * px ** 2 * (t / ref) if ref > t else float("inf")
            fl_proto = (math.sqrt(n_min) + 1) ** 2 * px ** 2 * (t / 0.25)
            rows.append({"fuel": f, "sensor": sensor, "n_looks": len(g), "median_T": t, "median_scar_dnbr": ref,
                         "floor_m2_fuel_dnbr": fl, "floor_acre_fuel_dnbr": fl / ACRE_M2,
                         "floor_m2_protocol_dnbr_0.25": fl_proto, "floor_acre_protocol": fl_proto / ACRE_M2})
    return pd.DataFrame(rows)


def sealed_by_fuel(run: str = "truth_sealed_final") -> pd.DataFrame:
    """Re-tabulation of the existing sealed run (opened once, 2026-11-20); nothing is re-run."""
    from shapely import wkt
    t = pd.read_parquet(RAW_ROOT / "derived_caught" / "runs" / run / "caught.parquet").drop_duplicates("rid")
    t = t[t.stratum == "primary_small"].copy()
    t["fuel"] = [fuel_of(p.y, p.x) for p in (wkt.loads(w).representative_point() for w in t.truth_wkt)]
    rows = []
    for f in ["grass", "shrub", "timber", "other"]:
        g = t[t.fuel == f]
        for k_, g2 in [("all", g)] + [(c, g[g.FIRE_SIZE_CLASS == c]) for c in "ABCD"]:
            n = len(g2)
            if not n:
                continue
            o, s, v = int(g2.caught_ours.sum()), int(g2.caught_std.sum()), int(g2.caught_verified.sum())
            rows.append({"fuel": f, "class": k_, "n": n, "recall_labelled": o / n, "recall_standard": s / n,
                         "recall_verified": v / n, "labelled_wilson": wilson(o, n), "standard_wilson": wilson(s, n)})
    return pd.DataFrame(rows)

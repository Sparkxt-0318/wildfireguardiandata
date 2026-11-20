"""Field plots (BLM AIM via Landscape Data Commons): eligibility, plot structural class, compatible fuel groups.

This module is used ONLY by grading. The agent package never imports it (tests/fuel/test_holdout.py enforces that).
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .fetch.rawindex import RAW_ROOT

IND_COLS = ["PrimaryKey", "ProjectKey", "DateVisited", "Latitude_NAD83", "Longitude_NAD83", "TotalFoliarCover", "BareSoil",
            "AH_ShrubCover", "AH_GraminoidCover", "AH_ForbCover", "FH_RockCover", "FH_WaterCover", "State"]

# protocol section 4
COMPAT = {
    "P_WATER": {"NB"},
    "P_TREE": {"TU", "TL", "SB", "GS", "SH"},
    "P_OPENTREE": {"GR", "GS", "SH", "TU", "TL", "SB"},
    "P_BARE": {"NB", "GR", "GS", "SH"},
    "P_GRASS": {"GR", "GS"},
    "P_SHRUB": {"GS", "SH"},          # plus GR when H >= 2 * Sh (handled in plot_class_and_compat)
    "P_SPARSE": {"NB", "GR", "GS", "SH"},
}


def plot_class(F, Sh, H, B, R, W, T):
    if W >= 50:
        return "P_WATER"
    if T >= 20:
        return "P_TREE"
    if T >= 10:
        return "P_OPENTREE"
    if F < 10 and B + R >= 50:
        return "P_BARE"
    if H >= 10 and Sh < 10:
        return "P_GRASS"
    if Sh >= 10:
        return "P_SHRUB"
    return "P_SPARSE"


def compat_set(cls: str, H: float, Sh: float) -> set:
    s = set(COMPAT[cls])
    if cls == "P_SHRUB" and H >= 2 * Sh:
        s.add("GR")
    return s


def build_base(raw: Path | None = None) -> pd.DataFrame:
    """Eligible AIM plot locations (one per location, latest visit, 2019+), without tree cover."""
    raw = Path(raw or RAW_ROOT / "ldc")
    cache = raw / "plots_base.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    rows = []
    with open(raw / "geoIndicators.jsonl") as fh:
        for line in fh:
            d = json.loads(line)
            if d.get("ProjectKey") != "BLM_AIM":
                continue
            rows.append({c: d.get(c) for c in IND_COLS})
    df = pd.DataFrame(rows).drop_duplicates("PrimaryKey")
    for c in IND_COLS[3:12]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["date"] = pd.to_datetime(df.DateVisited, errors="coerce")
    df = df[(df.date.dt.year >= 2019) & (df.State != "AK")]
    df = df.dropna(subset=["Latitude_NAD83", "Longitude_NAD83", "TotalFoliarCover", "BareSoil", "AH_ShrubCover",
                           "AH_GraminoidCover", "AH_ForbCover"])
    df["FH_RockCover"] = df.FH_RockCover.fillna(0)
    df["FH_WaterCover"] = df.FH_WaterCover.fillna(0)
    from pyproj import Transformer
    t = Transformer.from_crs(4326, 5070, always_xy=True)
    df["x"], df["y"] = t.transform(df.Longitude_NAD83.values, df.Latitude_NAD83.values)
    df["loc"] = df.Latitude_NAD83.round(5).astype(str) + "_" + df.Longitude_NAD83.round(5).astype(str)
    df = df.sort_values("date").drop_duplicates("loc", keep="last").reset_index(drop=True)
    df["H"] = df.AH_GraminoidCover + df.AH_ForbCover
    df.to_pickle(cache)
    return df


def fetch_tree_cover(keys, raw: Path | None = None, workers: int = 8) -> dict:
    """Tree cover (sum of tree-species any-hit cover, capped 100) per PrimaryKey, queried per plot and cached."""
    import requests
    from concurrent.futures import ThreadPoolExecutor
    raw = Path(raw or RAW_ROOT / "ldc")
    cache_p = raw / "tree_cache.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    todo = [k for k in keys if k not in cache]

    def one(k):
        for a in range(5):
            try:
                r = requests.get("https://api.landscapedatacommons.org/api/v1/geoSpecies",
                                 params={"PrimaryKey": k, "GrowthHabitSub": "Tree", "limit": 1000}, timeout=120)
                r.raise_for_status()
                seen, tot = set(), 0.0
                for d in r.json():          # rows can repeat per species: count each species once
                    if d["Species"] in seen or d.get("AH_SpeciesCover") is None:
                        continue
                    seen.add(d["Species"])
                    tot += float(d["AH_SpeciesCover"])
                return k, min(tot, 100.0)
            except Exception:  # noqa: BLE001
                import time
                time.sleep(2 * (a + 1))
        return k, None
    with ThreadPoolExecutor(workers) as ex:
        for k, v in ex.map(one, todo):
            if v is not None:
                cache[k] = v
    cache_p.write_text(json.dumps(cache))
    return cache


def classify(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["pclass"] = [plot_class(r.TotalFoliarCover, r.AH_ShrubCover, r.H, r.BareSoil, r.FH_RockCover, r.FH_WaterCover, r.T)
                    for r in df.itertuples()]
    df["compat"] = [",".join(sorted(compat_set(r.pclass, r.H, r.AH_ShrubCover))) for r in df.itertuples()]
    return df


def load_table(tiles, allow_sealed: bool = False) -> pd.DataFrame:
    """Plots inside the given tiles with tree cover attached. Sealed tiles are refused here: use sealed.py."""
    from .areas import SEALED, ORIGIN, TILE
    if not allow_sealed and any(t in SEALED for t in tiles):
        raise PermissionError("sealed areas are loaded only by the sealed-run command")
    base = build_base()
    parts = []
    for t in tiles:
        tx, ty = int(t[1:4]), int(t[5:8])
        x0, y0 = ORIGIN[0] + tx * TILE, ORIGIN[1] + ty * TILE
        parts.append(base[(base.x >= x0) & (base.x < x0 + TILE) & (base.y >= y0) & (base.y < y0 + TILE)])
    df = pd.concat(parts, ignore_index=True)
    tree = fetch_tree_cover(df.PrimaryKey.tolist())
    df["T"] = df.PrimaryKey.map(tree)
    df = df.dropna(subset=["T"])
    return classify(df)

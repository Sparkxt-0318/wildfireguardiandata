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


def build_table(raw: Path | None = None, out: Path | None = None) -> pd.DataFrame:
    raw = Path(raw or RAW_ROOT / "ldc")
    out = Path(out or raw / "plots_eligible.pkl")
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
    # tree cover: sum of tree species any-hit cover per plot visit
    tree = {}
    with open(raw / "geoSpecies_tree.jsonl") as fh:
        for line in fh:
            d = json.loads(line)
            v = d.get("AH_SpeciesCover")
            if v is not None:
                tree[d["PrimaryKey"]] = tree.get(d["PrimaryKey"], 0.0) + float(v)
    df["T"] = df.PrimaryKey.map(tree).fillna(0.0).clip(upper=100.0)
    from pyproj import Transformer
    t = Transformer.from_crs(4326, 5070, always_xy=True)
    df["x"], df["y"] = t.transform(df.Longitude_NAD83.values, df.Latitude_NAD83.values)
    df["loc"] = df.Latitude_NAD83.round(5).astype(str) + "_" + df.Longitude_NAD83.round(5).astype(str)
    df = df.sort_values("date").drop_duplicates("loc", keep="last").reset_index(drop=True)
    df["H"] = df.AH_GraminoidCover + df.AH_ForbCover
    df["pclass"] = [plot_class(r.TotalFoliarCover, r.AH_ShrubCover, r.H, r.BareSoil, r.FH_RockCover, r.FH_WaterCover, r.T)
                    for r in df.itertuples()]
    df["compat"] = [",".join(sorted(compat_set(r.pclass, r.H, r.AH_ShrubCover))) for r in df.itertuples()]
    df.to_pickle(out)
    return df


def load_table(path: Path | None = None) -> pd.DataFrame:
    p = Path(path or RAW_ROOT / "ldc" / "plots_eligible.pkl")
    if not p.exists():
        return build_table()
    return pd.read_pickle(p)

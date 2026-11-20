"""Grade agent overlays against held-out field plots (protocol sections 4, 6, 8). The only module that reads plots."""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from . import metrics, plots
from .agent import BIT_RULES, GROUP_NAMES, VERDICT_NAMES
from .areas import DEV, SEALED, TILE, ORIGIN, tile_grid
from .grid import Grid
from .runner import OUT_ROOT, region_cfg

FUEL_DIR = Path(__file__).parent


def _group_of(cfg):
    lut = {}
    for g, codes in cfg["groups"].items():
        for c in codes:
            lut[c] = g
    return lut


def plots_for_tile(df: pd.DataFrame, tile: str) -> pd.DataFrame:
    tx, ty = int(tile[1:4]), int(tile[5:8])
    x0, y0 = ORIGIN[0] + tx * TILE, ORIGIN[1] + ty * TILE
    return df[(df.x >= x0) & (df.x < x0 + TILE) & (df.y >= y0) & (df.y < y0 + TILE)]


def grade_tiles(tiles, map_key="M22", cfg=None, out_root=None, allow_sealed=False, table=None) -> pd.DataFrame:
    """One row per plot with verdict, rules fired, map class/group and agreement. Refuses sealed tiles unless allowed."""
    if not allow_sealed and any(t in SEALED for t in tiles):
        raise PermissionError("sealed areas can only be opened through the sealed-run command (protocol section 8)")
    cfg = cfg or region_cfg()
    glut = _group_of(cfg)
    table = plots.load_table() if table is None else table
    rows = []
    for t in tiles:
        pt = plots_for_tile(table, t)
        if not len(pt):
            continue
        g = tile_grid(t)
        out = Path(out_root or OUT_ROOT) / map_key / t
        with rasterio.open(out / "verdict.tif") as sv, rasterio.open(out / "rules.tif") as sr, rasterio.open(out / "suggest.tif") as ss:
            v, r, sg = sv.read(1), sr.read(1), ss.read(1)
        import rasterio as _r
        d = Path(OUT_ROOT).parent / "firewitness_raw" / "areas" / t
        from .areas import area_dir
        with _r.open(area_dir(t) / cfg["maps"][map_key]["file"]) as sf:
            fb = sf.read(1)
        row, col = g.cell_of(pt.x.values, pt.y.values)
        ok = g.inside(row, col)
        pt, row, col = pt[ok], row[ok], col[ok]
        cls = fb[row, col].astype(int)
        grp = np.array([glut.get(int(c), "") for c in cls])
        comp = [set(s.split(",")) for s in pt.compat]
        dis = np.array([(gg != "") and (gg not in cs) for gg, cs in zip(grp, comp)])
        rows.append(pd.DataFrame({"tile": t, "plot": pt.PrimaryKey.values, "x": pt.x.values, "y": pt.y.values,
                                  "pclass": pt.pclass.values, "map_class": cls, "map_group": grp, "disagree": dis,
                                  "verdict": [VERDICT_NAMES[int(k)] for k in v[row, col]], "rules": r[row, col],
                                  "suggest": sg[row, col], "row": row, "col": col}))
    df = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    df = df[df.map_group != ""] if len(df) else df
    return metrics.add_blocks(df) if len(df) else df


def summarize(df: pd.DataFrame, label: str = "") -> dict:
    out = {"label": label, "n_plots": int(len(df)),
           "verdict_counts": df.verdict.value_counts().to_dict(),
           "disagree_overall": float(df.disagree.mean()) if len(df) else float("nan")}
    out["F1"] = metrics.f1(df)
    out["F2"] = metrics.f2(df)
    out["F1_stale"] = metrics.f1(df, a="stale", b="consistent", min_a=10)
    per_rule = {}
    for bit, name in BIT_RULES.items():
        m = ((df.rules.values >> bit) & 1).astype(bool)
        if m.sum():
            per_rule[name] = {"n_plots": int(m.sum()), "disagree": float(df.disagree[m].mean())}
    out["per_rule"] = per_rule
    out["per_tile"] = {t: {"n": int(len(d)), "contradicted": int((d.verdict == "contradicted").sum()),
                           "consistent": int((d.verdict == "consistent").sum())} for t, d in df.groupby("tile")}
    return out


def wrong_verdicts(df: pd.DataFrame) -> pd.DataFrame:
    """Dev-loop helper: contradicted cells where the plot agrees, consistent cells where the plot disagrees."""
    return df[((df.verdict == "contradicted") & ~df.disagree) | ((df.verdict == "consistent") & df.disagree)]

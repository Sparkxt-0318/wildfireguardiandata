"""Adapter for track 50's three-state table `caught_states_v0.1.parquet` (GeoParquet, EPSG:4326).

One row per (window, state): rid, state in {fire, no_fire, unknown}, geometry (the three partition the record's disc),
t0/t1 (interval the state holds), floor_m2 (no_fire: smallest burned area the look would have seen), tier, std_label.
Each rid becomes one Scene on a local grid. no_fire cells carry `static['floor_m2']`; the negatives sampler only
accepts a no_fire cell whose floor is no larger than the cell area (a look that could not see a burn that small does
not verify "no fire" at that cell).
No weather or fuel layers exist in this table: danger class and land cover are unavailable, so negatives are matched
on region and season only and the sampler says so in its statistics.
"""
from __future__ import annotations

from ..dataset import Dataset
from .states import bbox, build_scene


def from_rows(rows, cell_km: float | None = None, max_cells: int = 200) -> Dataset:
    by = {}
    for r in rows:
        by.setdefault(r["rid"], []).append(r)
    scenes = {}
    for rid in sorted(by):
        regs = by[rid]
        box = bbox([r["geometry"] for r in regs if r.get("geometry") is not None])
        if box is None:
            continue
        tier = next((r.get("tier") for r in regs if r.get("tier")), None)
        s = build_scene(str(rid), regs, box, cell_km, max_cells, meta={"source": "caught_states_v0.1", "tier": tier})
        if s is not None:
            scenes[s.fire_id] = s
    return Dataset("caught_states_v0.1", scenes, 0.0, {"source": "track 50 three-state table",
                   "state_rule": "caught three states: fire / verified no fire (floor_m2) / unknown"})


def read_parquet(path: str, **kw) -> Dataset:
    try:
        import geopandas as gpd
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("reading the parquet needs geopandas and pyarrow (pip install geopandas pyarrow)") from e
    g = gpd.read_parquet(path)
    return from_rows(g.to_dict("records"), **kw)

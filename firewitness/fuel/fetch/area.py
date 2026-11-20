"""Fetch every layer the agent needs for one area into RAW_ROOT/areas/<name>/ (restartable)."""
from __future__ import annotations
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..areas import DEV, SEALED, area_dir, tile_grid
from ..grid import Grid
from . import lfps, nifc, nlcd, remote


def fetch_area(name: str, grid: Grid | None = None, maps=(2022, 2016)) -> Path:
    grid = grid or tile_grid(name)
    d = area_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    (d / "grid.json").write_text(__import__("json").dumps(grid.to_dict()))
    for yr in maps:
        lfps.fetch("FBFM40", yr, grid, d / f"fbfm40_lf{yr}.tif")
    nlcd.fetch("lc2021", grid, d / "nlcd_lc2021.tif")
    nlcd.fetch("tcc2021", grid, d / "tcc2021.tif")
    nifc.fetch(grid, d / "perimeters.geojson")
    # disturbance layers only for years that have a wildfire perimeter in the area
    import geopandas as gpd
    per = gpd.read_file(d / "perimeters.geojson")
    years = sorted({int(y) for y in per[per.KIND == "WF"].YEAR if 1999 <= y <= 2025}) if len(per) else []
    for y in years:
        try:
            lfps.fetch("Dist", y, grid, d / f"dist_{y}.tif")
        except RuntimeError as e:
            print(name, "Dist", y, "unavailable:", str(e)[:120], file=sys.stderr)
    remote.worldcover_shares(grid, d / "wc_shares.tif")
    remote.hansen(grid, d / "hansen.tif")
    remote.meta_chm(grid, d / "chm.tif")
    (d / "DONE").write_text("ok\n")
    return d


def main(names):
    def one(n):
        try:
            fetch_area(n)
            print("done", n, flush=True)
        except Exception:  # noqa: BLE001
            print("FAILED", n, traceback.format_exc()[-600:], flush=True)
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(one, names))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "dev"
    main(DEV if which == "dev" else SEALED if which == "sealed" else DEV + SEALED)

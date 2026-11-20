"""Load the independent layers of one area onto its grid. Read-only; never touches plots."""
from __future__ import annotations
from dataclasses import dataclass, field
import json
from pathlib import Path

import numpy as np
import rasterio

from .grid import Grid


@dataclass
class Layers:
    grid: Grid
    fbfm: np.ndarray            # int16 fuel class of the map under test
    lc: np.ndarray              # NLCD 2021 class (uint8; 0 = none)
    tcc: np.ndarray             # tree canopy cover % (uint8; >100 = nodata)
    chm_max: np.ndarray         # canopy max height m (uint8; 255 = nodata)
    chm_cov: np.ndarray         # % of 10 m sub-cells >= 3 m
    wc: dict                    # WorldCover class -> share % (uint8; 255 = nodata)
    tc2000: np.ndarray          # Hansen tree cover 2000
    loss_year: np.ndarray       # Hansen loss year 2000+v (0 none)
    post_fire_year: np.ndarray  # latest wildfire-perimeter year strictly after the map year (0 none)
    pre_burn: np.ndarray        # bool: inside a wildfire perimeter of year<=map year AND LANDFIRE dist(year)!=0
    map_year: int = 0
    files: list = field(default_factory=list)   # input files (for hashing)


def _read(path, files, band=1):
    files.append(str(path))
    with rasterio.open(path) as s:
        return s.read(band) if band else s.read()


def rasterize_years(per, grid: Grid, years):
    """{year: bool mask} of wildfire perimeters for each year in `years`."""
    from rasterio import features
    out = {}
    for y in years:
        s = per[(per.YEAR == y) & (per.KIND == "WF")]
        if len(s):
            out[y] = features.rasterize(((g, 1) for g in s.geometry), out_shape=grid.shape, transform=grid.transform,
                                        fill=0, dtype="uint8").astype(bool)
    return out


def load(area_dir: Path, map_key: str, cfg: dict) -> Layers:
    import geopandas as gpd
    d = Path(area_dir)
    grid = Grid.from_dict(json.loads((d / "grid.json").read_text()))
    m = cfg["maps"][map_key]
    files: list = []
    fbfm = _read(d / m["file"], files)
    lc = _read(d / "nlcd_lc2021.tif", files)
    tcc = _read(d / "tcc2021.tif", files)
    chm = _read(d / "chm.tif", files, band=None)
    wcarr = _read(d / "wc_shares.tif", files, band=None)
    wc = {c: wcarr[i] for i, c in enumerate(cfg["data"]["wc_classes"])}
    han = _read(d / "hansen.tif", files, band=None)
    loss = np.where(han[1] > 0, 2000 + han[1].astype(np.int16), 0).astype(np.int16)
    files.append(str(d / "perimeters.geojson"))
    per = gpd.read_file(d / "perimeters.geojson")
    my = m["map_year"]
    post = np.zeros(grid.shape, np.int16)
    pre_burn = np.zeros(grid.shape, bool)
    if len(per):
        yrs = sorted(set(int(y) for y in per[per.KIND == "WF"].YEAR))
        masks = rasterize_years(per, grid, yrs)
        for y, mk in sorted(masks.items()):
            if y > my:
                post = np.where(mk, np.int16(y), post)
            elif y >= 1999:
                p = d / f"dist_{y}.tif"
                if p.exists():
                    dist = _read(p, files)
                    pre_burn |= mk & (dist != 0)
    return Layers(grid, fbfm, lc, tcc, chm[0], chm[1], wc, han[0], loss, post, pre_burn, my, files)

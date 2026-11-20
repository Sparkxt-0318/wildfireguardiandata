"""Layers that live on cloud object storage as GeoTIFFs: ESA WorldCover, Hansen GFC, Meta canopy height.

Each reader warps the needed window onto the analysis grid (or a finer sub-grid) through a WarpedVRT, so only the
source blocks that cover the area are fetched.
"""
from __future__ import annotations
import math
import os
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds

from ..grid import CRS, Grid, write_tif
from .rawindex import register

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
if os.environ.get("HTTPS_PROXY") and not os.environ.get("GDAL_HTTP_PROXY"):
    os.environ["GDAL_HTTP_PROXY"] = os.environ["HTTPS_PROXY"]
os.environ.setdefault("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")

WC_BASE = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
HANSEN_BASE = "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/Hansen_GFC-2024-v1.12_{layer}_{tile}.tif"
META_BASE = "https://dataforgood-fb-data.s3.amazonaws.com/forests/v1/alsgedi_global_v6_float/chm/{qk}.tif"


def _lonlat_bounds(grid: Grid):
    return transform_bounds(CRS, "EPSG:4326", *grid.bounds(), densify_pts=21)


def _warp(url: str, grid: Grid, factor: int, resampling, dtype="uint8", nodata=0):
    """Read `url` onto the grid refined by `factor` (cells of 30/factor m)."""
    tr = Affine(30.0 / factor, 0, grid.xmin, 0, -30.0 / factor, grid.ymax)
    with rasterio.open("/vsicurl/" + url) as src:
        with WarpedVRT(src, crs=CRS, transform=tr, width=grid.width * factor, height=grid.height * factor,
                       resampling=resampling, nodata=nodata, dtype=dtype) as vrt:
            return vrt.read(1)


def _wc_tiles(grid):
    w, s, e, n = _lonlat_bounds(grid)
    out = []
    for la in range(math.floor(s / 3) * 3, math.floor(n / 3) * 3 + 1, 3):
        for lo in range(math.floor(w / 3) * 3, math.floor(e / 3) * 3 + 1, 3):
            out.append(f"{'N' if la >= 0 else 'S'}{abs(la):02d}{'E' if lo >= 0 else 'W'}{abs(lo):03d}")
    return out


def _hansen_tiles(grid):
    w, s, e, n = _lonlat_bounds(grid)
    out = []
    for la in range(math.floor(s / 10) * 10 + 10, math.floor(n / 10) * 10 + 11, 10):
        for lo in range(math.floor(w / 10) * 10, math.floor(e / 10) * 10 + 1, 10):
            out.append(f"{abs(la):02d}{'N' if la >= 0 else 'S'}_{abs(lo):03d}{'E' if lo >= 0 else 'W'}")
    return out


WC_CLASSES = (10, 20, 30, 40, 50, 60, 70, 80, 90, 100)


def worldcover_shares(grid: Grid, out: Path) -> Path:
    """10 bands (WC classes 10..100), each the share (0-100) of the 3x3 10 m sub-cells of the 30 m cell."""
    out = Path(out)
    if out.exists():
        return out
    full = np.zeros((grid.height * 3, grid.width * 3), dtype="uint8")
    for t in _wc_tiles(grid):
        try:
            a = _warp(WC_BASE.format(tile=t), grid, 3, Resampling.nearest)
        except rasterio.errors.RasterioIOError:
            continue  # ocean/empty tile
        full = np.where(a > 0, a, full)
    h, w = grid.height, grid.width
    blocks = full.reshape(h, 3, w, 3).transpose(0, 2, 1, 3).reshape(h, w, 9)
    bands = [(blocks == c).sum(axis=2) * 100 // 9 for c in WC_CLASSES]
    valid = (blocks > 0).any(axis=2)
    arr = np.stack(bands).astype("uint8")
    arr[:, ~valid] = 255
    write_tif(out, arr, grid, nodata=255)
    register(out, WC_BASE.format(tile="*"), "WorldCover 2021 v200, class shares per 30 m cell")
    return out


def hansen(grid: Grid, out: Path) -> Path:
    """2 bands: treecover2000 (0-100), lossyear (0 none, 1-24 = 2001-2024)."""
    out = Path(out)
    if out.exists():
        return out
    tc = np.zeros(grid.shape, "uint8")
    ly = np.zeros(grid.shape, "uint8")
    for t in _hansen_tiles(grid):
        a = _warp(HANSEN_BASE.format(layer="treecover2000", tile=t), grid, 1, Resampling.nearest)
        b = _warp(HANSEN_BASE.format(layer="lossyear", tile=t), grid, 1, Resampling.nearest)
        tc = np.maximum(tc, a)
        ly = np.maximum(ly, b)
    write_tif(out, np.stack([tc, ly]), grid, nodata=None)
    register(out, HANSEN_BASE.format(layer="*", tile="*"), "Hansen GFC 2024 v1.12 treecover2000, lossyear")
    return out


def _quadkey(lat, lon, z=9):
    x = int((lon + 180) / 360 * 2 ** z)
    y = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * 2 ** z)
    q = ""
    for i in range(z, 0, -1):
        d = 0
        m = 1 << (i - 1)
        if x & m:
            d += 1
        if y & m:
            d += 2
        q += str(d)
    return q


def meta_chm(grid: Grid, out: Path) -> Path:
    """2 bands per 30 m cell from the 1 m canopy height: max height (m) and share (0-100) of 10 m sub-cells with max >= 3 m."""
    out = Path(out)
    if out.exists():
        return out
    w, s, e, n = _lonlat_bounds(grid)
    qks = sorted({_quadkey(la, lo) for la in np.linspace(s, n, 5) for lo in np.linspace(w, e, 5)})
    full = np.zeros((grid.height * 3, grid.width * 3), "uint8")
    seen = np.zeros(full.shape, bool)
    for qk in qks:
        try:
            a = _warp(META_BASE.format(qk=qk), grid, 3, Resampling.max, nodata=255)
        except rasterio.errors.RasterioIOError:
            continue
        ok = a != 255
        full = np.where(ok & ~seen, a, full)
        seen |= ok
    h, wd = grid.height, grid.width
    blocks = full.reshape(h, 3, wd, 3).transpose(0, 2, 1, 3).reshape(h, wd, 9)
    mx = blocks.max(axis=2)
    cov = (blocks >= 3).sum(axis=2) * 100 // 9
    sv = seen.reshape(h, 3, wd, 3).any(axis=(1, 3))
    arr = np.stack([mx, cov]).astype("uint8")
    arr[:, ~sv] = 255
    write_tif(out, arr, grid, nodata=255)
    register(out, META_BASE.format(qk="*"), "Meta/WRI canopy height (Tolan 2024): 30 m max height, share>=3m")
    return out

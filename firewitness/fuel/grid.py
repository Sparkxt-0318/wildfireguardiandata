"""Common analysis grid: EPSG:5070 (CONUS Albers), 30 m cells, edges at x, y = 15 (mod 30).

This is the native grid of LANDFIRE and NLCD, so those layers are read without resampling.
Every raster the agent sees is cut to one `Grid` (bounds + shape).
"""
from __future__ import annotations
from dataclasses import dataclass
import math

import numpy as np

CRS = "EPSG:5070"
RES = 30.0
OFFSET = 15.0  # edges are at multiples of 30 plus 15


def snap_down(v: float) -> float:
    return math.floor((v - OFFSET) / RES) * RES + OFFSET


def snap_up(v: float) -> float:
    return math.ceil((v - OFFSET) / RES) * RES + OFFSET


@dataclass(frozen=True)
class Grid:
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @classmethod
    def from_bounds(cls, xmin, ymin, xmax, ymax) -> "Grid":
        return cls(snap_down(xmin), snap_down(ymin), snap_up(xmax), snap_up(ymax))

    @property
    def width(self) -> int:
        return int(round((self.xmax - self.xmin) / RES))

    @property
    def height(self) -> int:
        return int(round((self.ymax - self.ymin) / RES))

    @property
    def shape(self) -> tuple[int, int]:
        return (self.height, self.width)

    @property
    def transform(self):
        from rasterio.transform import from_origin
        return from_origin(self.xmin, self.ymax, RES, RES)

    def bounds(self):
        return (self.xmin, self.ymin, self.xmax, self.ymax)

    def to_dict(self) -> dict:
        return {"crs": CRS, "res": RES, "bounds": list(self.bounds()), "shape": list(self.shape)}

    @classmethod
    def from_dict(cls, d: dict) -> "Grid":
        return cls(*d["bounds"])

    def cell_of(self, x: np.ndarray, y: np.ndarray):
        """Row, col of points in EPSG:5070 metres (floor); callers mask out-of-grid."""
        col = np.floor((np.asarray(x) - self.xmin) / RES).astype(int)
        row = np.floor((self.ymax - np.asarray(y)) / RES).astype(int)
        return row, col

    def inside(self, row, col):
        return (row >= 0) & (row < self.height) & (col >= 0) & (col < self.width)


def lonlat_to_5070(lon, lat):
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    return t.transform(lon, lat)


def write_tif(path, arr, grid: Grid, nodata=None, dtype=None, compress="deflate"):
    import rasterio
    arr = np.asarray(arr)
    if arr.ndim == 2:
        arr = arr[None]
    with rasterio.open(path, "w", driver="GTiff", height=grid.height, width=grid.width, count=arr.shape[0],
                       dtype=dtype or arr.dtype, crs=CRS, transform=grid.transform, nodata=nodata,
                       compress=compress, tiled=True, blockxsize=256, blockysize=256) as dst:
        dst.write(arr.astype(dtype or arr.dtype))


def read_tif(path, grid: Grid | None = None):
    """Read band 1 as an array; if `grid` is given, assert the file is on it."""
    import rasterio
    with rasterio.open(path) as src:
        if grid is not None:
            b = src.bounds
            if (abs(b.left - grid.xmin) > 1e-3 or abs(b.top - grid.ymax) > 1e-3
                    or src.width != grid.width or src.height != grid.height):
                raise ValueError(f"{path}: not on grid {grid}")
        return src.read(1), src.nodata

"""Study areas (protocol section 5) and the per-area layer folder."""
from __future__ import annotations
from pathlib import Path

from .fetch.rawindex import RAW_ROOT
from .grid import Grid

TILE = 60000
ORIGIN = (-2362395.0, 221265.0)

DEV = ["T012_030", "T008_029", "T016_033", "T015_024", "T012_036", "T021_025", "T016_037", "T016_026", "T010_033", "T021_028"]
SEALED = ["T019_033", "T016_039", "T012_018", "T023_036", "T009_036", "T007_037", "T012_027", "T015_015", "T013_024", "T023_042"]


def tile_grid(tile_id: str) -> Grid:
    tx, ty = int(tile_id[1:4]), int(tile_id[5:8])
    ox, oy = ORIGIN
    return Grid.from_bounds(ox + tx * TILE, oy + ty * TILE, ox + (tx + 1) * TILE, oy + (ty + 1) * TILE)


def split_of(tile_id: str) -> str:
    return "dev" if tile_id in DEV else "sealed" if tile_id in SEALED else "other"


def area_dir(name: str) -> Path:
    return RAW_ROOT / "areas" / name

"""ESA WorldCover 2020 majority class at ~200 m, for matching placebo places (protocol section 8, C1)."""
from __future__ import annotations

import math
import threading

import numpy as np

from .fetch import RAW_ROOT, _index_add
from firewitness.core.hashing import sha256_file

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
N = 1800  # pixels per 3-degree tile at the decimated read (~185 m)
_lock = threading.Lock()
_cache: dict = {}


def _tile_name(lat: float, lon: float) -> tuple[int, int]:
    return int(math.floor(lat / 3) * 3), int(math.floor(lon / 3) * 3)


def _path(la: int, lo: int):
    ns = "N" if la >= 0 else "S"
    ew = "E" if lo >= 0 else "W"
    return RAW_ROOT / "worldcover" / f"ESA_WorldCover_2020_v100_{ns}{abs(la):02d}{ew}{abs(lo):03d}_mode{N}.npy"


def _load(la: int, lo: int):
    key = (la, lo)
    with _lock:
        if key in _cache:
            return _cache[key]
    p = _path(la, lo)
    if not p.exists():
        import planetary_computer as pc
        import pystac_client
        import rasterio
        from rasterio.enums import Resampling

        cat = pystac_client.Client.open(STAC, modifier=pc.sign_inplace)
        its = [i for i in cat.search(collections=["esa-worldcover"], bbox=[lo + 1, la + 1, lo + 2, la + 2],
                                     query={"esa_worldcover:product_version": {"eq": "1.0.0"}}).items()]
        p.parent.mkdir(parents=True, exist_ok=True)
        if not its:
            arr = np.zeros((N, N), np.uint8)
        else:
            with rasterio.open(its[0].assets["map"].href) as s:
                arr = s.read(1, out_shape=(N, N), resampling=Resampling.mode)
        np.save(p, arr)
        _index_add(str(p.relative_to(RAW_ROOT)), its[0].assets["map"].href.split("?")[0] if its else "none",
                   sha256_file(p), p.stat().st_size)
    arr = np.load(p)
    with _lock:
        _cache[key] = arr
    return arr


def lc_class(lat: float, lon: float) -> int:
    """WorldCover class (10 tree, 20 shrub, 30 grass, 40 crop, 50 built, 60 bare, 70 snow, 80 water, 90 wetland,
    95 mangrove, 100 moss); 0 = no data."""
    la, lo = _tile_name(lat, lon)
    a = _load(la, lo)
    r = int((la + 3 - lat) / 3 * N)
    c = int((lon - lo) / 3 * N)
    return int(a[min(max(r, 0), N - 1), min(max(c, 0), N - 1)])

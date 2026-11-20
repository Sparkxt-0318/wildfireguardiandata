"""NLCD 2021 land cover and USFS tree canopy cover (v2021-4) from the MRLC WCS, native 5070 30 m grid."""
from __future__ import annotations
from pathlib import Path
import time

import requests

from ..grid import Grid
from .rawindex import register

WCS = "https://www.mrlc.gov/geoserver/mrlc_download/wcs"
COVERAGES = {"lc2021": "mrlc_download__NLCD_2021_Land_Cover_L48", "tcc2021": "mrlc_download__nlcd_tcc_conus_2021_v2021-4"}


def fetch(key: str, grid: Grid, out: Path, retries: int = 4) -> Path:
    out = Path(out)
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    # subset by cell centres, so the returned grid is exactly ours
    xmin, ymin, xmax, ymax = grid.bounds()
    p = [("service", "WCS"), ("version", "2.0.1"), ("request", "GetCoverage"), ("coverageId", COVERAGES[key]),
         ("format", "image/tiff"), ("subset", f"X({xmin + 1},{xmax - 1})"), ("subset", f"Y({ymin + 1},{ymax - 1})")]
    last = None
    for k in range(retries):
        try:
            r = requests.get(WCS, params=p, timeout=600)
            r.raise_for_status()
            if r.content[:2] not in (b"II", b"MM"):
                raise RuntimeError(r.text[:300])
            out.write_bytes(r.content)
            register(out, f"{WCS} {COVERAGES[key]}", f"MRLC {key}, window {grid.bounds()}")
            return out
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(4 * (k + 1))
    raise RuntimeError(f"MRLC fetch failed: {last}")

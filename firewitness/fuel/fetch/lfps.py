"""LANDFIRE layers from the USGS LFPS ImageServer, cut to a `Grid` (native 30 m, no resampling)."""
from __future__ import annotations
from pathlib import Path
import time

import requests

from ..grid import Grid, RES
from .rawindex import register

ROOT = "https://lfps.usgs.gov/arcgis/rest/services/"


def service_url(product: str, year: int) -> str:
    """product e.g. FBFM40, CC, CH, EVT; disturbance: product='Dist', year=2023 (yy of the disturbance year)."""
    if product in ("Asp", "Elev", "SlpD", "SlpP"):  # topography, LF2020 release (year ignored)
        return f"{ROOT}Landfire_Topo/LF2020_{product}_CONUS/ImageServer"
    if product.startswith("Dist") or product in ("LDist", "PDist"):
        y2 = f"{year % 100:02d}"
        return f"{ROOT}Landfire_Disturbance/LF{year if year >= 2022 else _dist_release(year)}_{product}{y2}_CONUS/ImageServer"
    return f"{ROOT}Landfire_LF{year}/LF{year}_{product}_CONUS/ImageServer"


def _dist_release(year: int) -> int:
    """Disturbance layers are named by the LANDFIRE release that first contained them."""
    table = {range(1999, 2008): 2001, range(2008, 2009): 2008, range(2009, 2011): 2010, range(2011, 2013): 2012,
             range(2013, 2015): 2014, range(2015, 2017): 2016, range(2017, 2021): 2020, range(2021, 2022): 2022}
    for r, rel in table.items():
        if year in r:
            return rel
    return year


def fetch(product: str, year: int, grid: Grid, out: Path, pixel_type: str = "S16", retries: int = 4) -> Path:
    out = Path(out)
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    url = service_url(product, year)
    params = {"f": "json", "bbox": ",".join(str(v) for v in grid.bounds()), "bboxSR": 5070, "imageSR": 5070,
              "size": f"{grid.width},{grid.height}", "format": "tiff", "pixelType": pixel_type,
              "interpolation": "RSP_NearestNeighbor", "noData": "-9999"}
    last = None
    for k in range(retries):
        try:
            r = requests.get(url + "/exportImage", params=params, timeout=300)
            r.raise_for_status()
            js = r.json()
            if "href" not in js:
                raise RuntimeError(str(js)[:300])
            t = requests.get(js["href"], timeout=300)
            t.raise_for_status()
            out.write_bytes(t.content)
            register(out, url, f"LANDFIRE {product} {year}, native 30 m window {grid.bounds()}")
            return out
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(4 * (k + 1))
    raise RuntimeError(f"LFPS fetch failed for {url}: {last}")

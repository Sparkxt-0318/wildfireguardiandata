"""Shared builder: three-state regions (fire / no_fire / unknown, each with a date interval) -> Scene on a local grid."""
from __future__ import annotations

import datetime as dt

import numpy as np

from ..dataset import FIRE, NO_FIRE, UNKNOWN, Scene

STATE_CODE = {"fire": FIRE, "no_fire": NO_FIRE, "unknown": UNKNOWN}
PRIORITY = {"unknown": 0, "no_fire": 1, "fire": 2}     # later wins where regions overlap
MAX_DAYS = 60
NO_FLOOR = np.float32(1e12)


def to_ordinal(x) -> int:
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return dt.datetime.fromtimestamp(float(x), dt.timezone.utc).date().toordinal()
    if isinstance(x, dt.datetime):
        return x.date().toordinal()
    if isinstance(x, dt.date):
        return x.toordinal()
    return dt.date.fromisoformat(str(x)[:10]).toordinal()


def _rings(geom):
    if hasattr(geom, "__geo_interface__"):
        geom = geom.__geo_interface__
    if geom is None:
        return []
    t = geom["type"]
    if t == "Polygon":
        return [geom["coordinates"]]
    if t == "MultiPolygon":
        return list(geom["coordinates"])
    if t == "GeometryCollection":
        out = []
        for g in geom["geometries"]:
            out += _rings(g)
        return out
    return []


def bbox(geoms):
    xs, ys = [], []
    for g in geoms:
        for poly in _rings(g):
            for ring in poly:
                for x, y in ring:
                    xs.append(x); ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def rasterise(geom, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Cell centres inside a (Multi)Polygon, even-odd rule, holes honoured."""
    out = np.zeros(lat.shape, bool)
    for poly in _rings(geom):
        inside = np.zeros(lat.shape, bool)
        for ring in poly:
            inside ^= _in_ring(np.asarray(ring, float), lat, lon)
        out |= inside
    return out


def _in_ring(ring, lat, lon):
    x, y = ring[:, 0], ring[:, 1]
    inside = np.zeros(lat.shape, bool)
    n = len(x)
    j = n - 1
    for i in range(n):
        xi, yi, xj, yj = x[i], y[i], x[j], y[j]
        cond = (yi > lat) != (yj > lat)
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (xj - xi) * (lat - yi) / (yj - yi) + xi
        inside ^= cond & (lon < xint)
        j = i
    return inside


def build_scene(fid: str, regions: list, geom_box, cell_km: float | None = None, max_cells: int = 200, min_cell_km: float = 0.0,
                static_extra: dict | None = None, meta: dict | None = None, pad_km: float = 0.2) -> Scene | None:
    """regions: dicts {state, t0, t1, geometry|mask, floor_m2 (no_fire only)}; geom_box = (lon0, lat0, lon1, lat1)."""
    lon0, lat0, lon1, lat1 = geom_box
    latc, lonc = (lat0 + lat1) / 2, (lon0 + lon1) / 2
    kmlat, kmlon = 111.32, 111.32 * np.cos(np.radians(latc))
    h_km, w_km = (lat1 - lat0) * kmlat + 2 * pad_km, (lon1 - lon0) * kmlon + 2 * pad_km
    if cell_km is None:
        cell_km = max(0.02, max(h_km, w_km) / max_cells)
    cell_km = max(cell_km, min_cell_km)
    H, W = max(1, int(np.ceil(h_km / cell_km))), max(1, int(np.ceil(w_km / cell_km)))
    days0 = min(to_ordinal(r["t0"]) for r in regions)
    days1 = min(max(to_ordinal(r["t1"]) for r in regions), days0 + MAX_DAYS - 1)
    dates = np.arange(days0, days1 + 1, dtype=np.int32)
    if len(dates) < 2:
        dates = np.arange(days0, days0 + 2, dtype=np.int32)
    T = len(dates)
    scene = Scene(fid, dates, np.zeros((T, H, W), np.int8), {}, {}, lat0=latc, lon0=lonc, cell_km=float(cell_km),
                  region=f"R{int(np.floor(latc / 4) * 4)}_{int(np.floor(lonc / 4) * 4)}",
                  year=dt.date.fromordinal(int(days0)).year, interval_slack=1, meta=meta or {})
    lat, lon = scene.latlon_grid()
    floor = np.full((H, W), NO_FLOOR, np.float32)
    slack = 0
    has_floor = False
    for r in sorted(regions, key=lambda r: PRIORITY[r["state"]]):
        if "mask" in r:
            m = r["mask"](lat, lon) if callable(r["mask"]) else r["mask"]
        else:
            m = rasterise(r["geometry"], lat, lon)
        a, b = to_ordinal(r["t0"]) - days0, to_ordinal(r["t1"]) - days0
        a, b = max(a, 0), min(b, T - 1)
        if b < a or not m.any():
            continue
        scene.state[a:b + 1][:, m] = STATE_CODE[r["state"]]
        if r["state"] == "no_fire" and r.get("floor_m2") is not None:
            floor[m] = np.minimum(floor[m], np.float32(r["floor_m2"]))
            has_floor = True
        if r["state"] == "fire":
            slack = max(slack, int(np.ceil((to_ordinal(r["t1"]) - to_ordinal(r["t0"])) / 2)))
    scene.interval_slack = max(1, slack)
    if has_floor:
        scene.static["floor_m2"] = floor
    for k, v in (static_extra or {}).items():
        scene.static[k] = v
    return scene

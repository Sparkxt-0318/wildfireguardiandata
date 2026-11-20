"""Scar finder (protocol section 6) and short-wave hot spots in the same looks.

find_scar(lon, lat, radius_m, start, end, area_ha)  -> ScarResult   (small fires, attribution rule on)
make_perimeter(lon, lat, start, end, area_ha)        -> ScarResult   (large fires, for track 49)

Imagery: Sentinel-2 L2A (20 m grid; 10 m visible bands averaged to 20 m) and Landsat 7/8 Collection 2 L2 (30 m)
from the Planetary Computer STAC (no key). Every window read is written raw under firewitness_raw/windows/,
hashed into a manifest, and deleted after the values are extracted (C3). No dilation, filling, smoothing or
interpolation: a fire pixel is always a candidate pixel.
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

from firewitness.core.hashing import sha256_bytes

from .fetch import RAW_ROOT
from .floor import scar_floor_m2

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")
os.environ.setdefault("GDAL_HTTP_MULTIPLEX", "YES")
os.environ.setdefault("GDAL_HTTP_VERSION", "2")
os.environ.setdefault("VSI_CACHE", "TRUE")
os.environ.setdefault("GDAL_CACHEMAX", "96")
os.environ.setdefault("VSI_CACHE_SIZE", "4000000")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "5")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.TIF,.tiff")
if os.path.exists("/root/.ccr/ca-bundle.crt"):
    os.environ.setdefault("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")

PARAMS = {
    "pre_days": 60, "post_days": 45, "min_clear": 0.8, "max_scene_cloud": 90.0, "max_tries": 10,
    "t_abs": 0.10, "k_sigma": 3.0, "dnir": -0.01, "dvis": 0.02, "n_min": 8,
    "regional_frac": 0.25, "attr_factor": 20.0, "attr_add_m2": 100_000.0,
    "ref_ratio": 0.5, "ref_slack_days": 16, "window_min_m": 1000.0, "max_window_px": 1000,
    "dnbr_ref": 0.25,
    "comp_min_dnbr": 0.0,      # minimum median dNBR of a component (0 = off)
    "dswir1_max": 0.02,        # a candidate pixel's SWIR1 change must be below this (D2; None = off)
    "min_nir_pre": None,       # unused unless set
    "landsat_if_no_scar": False,  # also look in Landsat when Sentinel-2 was clear but found no scar
}

S2_BAD = {0, 1, 3, 6, 8, 9, 10, 11}
CACHE_MIN_FREE = 30 * 1024 ** 3   # the dev cache never takes the disk below 30 GB free (half of the start)   # no data, saturated, shadow, water, cloud med/high, cirrus, snow
_tls = threading.local()
_manifest_lock = threading.Lock()


# ------------------------------------------------------------------ result
@dataclass
class ScarResult:
    status: str                      # scar | no_scar_clear | no_clear_look | below_floor | rejected
    sensor: str | None = None
    pre_date: str | None = None
    post_date: str | None = None
    threshold: float | None = None
    floor_m2: float | None = None
    clear_fraction: float | None = None
    area_ha: float = 0.0
    geometry: object = None          # shapely geometry EPSG:4326 (accepted components)
    components: list = field(default_factory=list)   # per component: area, median dNBR, status, reason
    reject_reason: str | None = None
    hotspots: list = field(default_factory=list)     # short-wave hot spots in looks inside the window
    looks: list = field(default_factory=list)        # every look tried: item, date, clear fraction, used for
    states: dict = field(default_factory=dict)       # three-state areas within the disc (m2) + geometries
    inputs: list = field(default_factory=list)       # (item id, asset, sha256 of window)

    def to_dict(self) -> dict:
        d = asdict(self)
        from shapely.geometry import mapping
        d["geometry"] = mapping(self.geometry) if self.geometry is not None and not self.geometry.is_empty else None
        st = {}
        for k, v in (self.states or {}).items():
            st[k] = mapping(v) if hasattr(v, "geom_type") else v
        d["states"] = st
        return d


# ------------------------------------------------------------------ STAC
def _catalog():
    if getattr(_tls, "cat", None) is None:
        import pystac_client
        _tls.cat = pystac_client.Client.open(STAC)
    return _tls.cat


def search(collection: str, lon: float, lat: float, d0: date, d1: date, query: dict | None = None) -> list:
    cache = os.environ.get("FIREWITNESS_WINDOW_CACHE")
    if cache:
        import hashlib
        import pystac
        key = hashlib.sha256(json.dumps([collection, round(lon, 6), round(lat, 6), str(d0), str(d1), query or {}],
                                        sort_keys=True).encode()).hexdigest()[:24]
        cf = Path(cache) / "stac" / f"{key}.json"
        if cf.exists():
            return [pystac.Item.from_dict(d) for d in json.loads(cf.read_text())]
        items = _search(collection, lon, lat, d0, d1, query)
        cf.parent.mkdir(parents=True, exist_ok=True)
        cf.write_text(json.dumps([i.to_dict() for i in items]))
        return items
    return _search(collection, lon, lat, d0, d1, query)


def _search(collection, lon, lat, d0, d1, query):
    for i in range(6):
        try:
            s = _catalog().search(collections=[collection], intersects={"type": "Point", "coordinates": [lon, lat]},
                                  datetime=f"{d0.isoformat()}/{d1.isoformat()}", query=query or {}, max_items=500)
            return list(s.items())
        except Exception:  # rate limit / transient
            _tls.cat = None
            time.sleep(2 * 2 ** i)
    raise RuntimeError(f"STAC search failed {collection}")


def _sign(href: str) -> str:
    import planetary_computer as pc
    return pc.sign(href)


def item_date(it) -> date:
    return it.datetime.date() if it.datetime else datetime.fromisoformat(it.properties["start_datetime"][:19]).date()


# ------------------------------------------------------------------ window reading
class Grid:
    """A pixel grid in the item's UTM CRS centred on the point."""

    def __init__(self, epsg: int, x: float, y: float, half_m: float, res: float):
        n = int(math.ceil(half_m / res))
        x0 = math.floor(x / res) * res - n * res
        y1 = math.floor(y / res) * res + (n + 1) * res
        self.epsg, self.res, self.n = epsg, res, 2 * n + 1
        self.bounds = (x0, y1 - self.n * res, x0 + self.n * res, y1)
        self.cx, self.cy = x, y
        xs = x0 + (np.arange(self.n) + 0.5) * res
        ys = y1 - (np.arange(self.n) + 0.5) * res
        self.X, self.Y = np.meshgrid(xs, ys)

    def dist(self):
        return np.hypot(self.X - self.cx, self.Y - self.cy)

    @property
    def transform(self):
        from rasterio.transform import from_origin
        return from_origin(self.bounds[0], self.bounds[3], self.res, self.res)


def _windows_dir(run: str) -> Path:
    p = RAW_ROOT / "windows" / run
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_asset(item, asset: str, grid: Grid, resampling: str = "nearest", run: str = "adhoc",
               inputs: list | None = None) -> np.ndarray:
    """Read one asset on `grid` (boundless, nodata 0); raw window saved, hashed and deleted after extraction."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT
    from rasterio.windows import from_bounds

    cache = os.environ.get("FIREWITNESS_WINDOW_CACHE")
    if cache:
        cf = Path(cache) / f"{item.id}.{asset}.{grid.epsg}.{grid.res:g}.{grid.bounds[0]:.0f}_{grid.bounds[1]:.0f}_{grid.n}.npy"
        if cf.exists():
            arr = np.load(cf)
            if inputs is not None:
                inputs.append((item.id, asset, sha256_bytes(np.ascontiguousarray(arr).tobytes())))
            return arr
    href = _sign(item.assets[asset].href)
    last = None
    for i in range(4):
        try:
            with rasterio.open(href) as src:
                if src.crs and src.crs.to_epsg() == grid.epsg:
                    # same grid family: windowed read; a coarser grid is read decimated (overviews), never warped
                    w = from_bounds(*grid.bounds, transform=src.transform)
                    w = w.round_offsets().round_lengths()
                    rs = Resampling.nearest if abs(src.res[0] - grid.res) < 1e-6 else getattr(Resampling, resampling)
                    arr = src.read(1, window=w, boundless=True, fill_value=0, out_shape=(grid.n, grid.n),
                                   resampling=rs)
                else:
                    rs = getattr(Resampling, resampling)
                    with WarpedVRT(src, crs=f"EPSG:{grid.epsg}", transform=grid.transform, width=grid.n,
                                   height=grid.n, resampling=rs, nodata=0) as vrt:
                        arr = vrt.read(1)
            break
        except Exception as e:
            last = e
            time.sleep(2 * 2 ** i)
    else:
        raise RuntimeError(f"read failed {item.id} {asset}: {type(last).__name__}")
    b = np.ascontiguousarray(arr).tobytes()
    sha = sha256_bytes(b)
    d = _windows_dir(run)
    f = d / f"{item.id}.{asset}.{grid.bounds[0]:.0f}_{grid.bounds[1]:.0f}.npy"
    np.save(f, arr)   # the raw window as downloaded (decoded), then removed below once values are extracted
    if inputs is not None:
        inputs.append((item.id, asset, sha))
    with _manifest_lock:
        with open(d / "MANIFEST.tsv", "a") as m:
            m.write(f"{item.id}\t{asset}\t{grid.epsg}\t{','.join(f'{v:.0f}' for v in grid.bounds)}\t{sha}\t{len(b)}\n")
    import shutil as _sh
    if cache and _sh.disk_usage(str(RAW_ROOT)).free > CACHE_MIN_FREE:
        Path(cache).mkdir(parents=True, exist_ok=True)
        os.replace(f, cf)   # kept for the dev rounds; the cache folder is deleted when the rounds end
    else:
        try:
            f.unlink()
        except OSError:
            pass
    return arr


# ------------------------------------------------------------------ sensor adapters
class S2:
    name = "s2"
    collection = "sentinel-2-l2a"
    res = 20.0
    mask_asset = "SCL"

    @staticmethod
    def epsg(it):
        return int(it.properties.get("proj:epsg") or it.properties["proj:code"].split(":")[1])

    @staticmethod
    def tile(it):
        return it.properties.get("s2:mgrs_tile")

    @staticmethod
    def cloud(it):
        return float(it.properties.get("eo:cloud_cover", 0.0))

    @staticmethod
    def clear(it, grid, run, inputs):
        scl = read_asset(it, "SCL", grid, "nearest", run, inputs)
        return ~np.isin(scl, list(S2_BAD))

    @staticmethod
    def offset(it):
        pb = str(it.properties.get("s2:processing_baseline", "0"))
        try:
            return 1000.0 if float(pb) >= 4.0 else 0.0
        except ValueError:
            return 0.0

    @classmethod
    def bands(cls, it, grid, run, inputs):
        off = cls.offset(it)
        g10 = Grid(grid.epsg, grid.cx, grid.cy, (grid.n // 2) * grid.res, grid.res / 2)
        # 10 m grid exactly covering the 20 m grid (2x2 blocks)
        g10.n = grid.n * 2
        g10.bounds = grid.bounds

        def r20(a):
            return (read_asset(it, a, grid, "average", run, inputs).astype("f4") - off) / 10000.0

        def r10(a):
            x = (read_asset(it, a, g10, "average", run, inputs).astype("f4") - off) / 10000.0
            return x.reshape(grid.n, 2, grid.n, 2).mean(axis=(1, 3))

        return {"nir": r20("B8A"), "swir1": r20("B11"), "swir2": r20("B12"),
                "vis": (r10("B02") + r10("B03") + r10("B04")) / 3.0}


class LANDSAT:
    name = "landsat"
    collection = "landsat-c2-l2"
    res = 30.0
    mask_asset = "qa_pixel"

    @staticmethod
    def epsg(it):
        return int(it.properties.get("proj:epsg") or it.properties["proj:code"].split(":")[1])

    @staticmethod
    def tile(it):
        return it.properties.get("proj:epsg")  # same UTM grid is enough (30 m grid is common within a zone)

    @staticmethod
    def cloud(it):
        return float(it.properties.get("eo:cloud_cover", 0.0))

    @staticmethod
    def clear(it, grid, run, inputs):
        qa = read_asset(it, "qa_pixel", grid, "nearest", run, inputs).astype(np.uint16)
        bad = (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5) | (1 << 7)
        return (qa & bad) == 0

    @classmethod
    def bands(cls, it, grid, run, inputs):
        def r(a):
            x = read_asset(it, a, grid, "nearest", run, inputs).astype("f4")
            return np.where(x > 0, x * 0.0000275 - 0.2, np.nan)
        return {"nir": r("nir08"), "swir1": r("swir16"), "swir2": r("swir22"),
                "vis": (r("blue") + r("green") + r("red")) / 3.0}


SENSORS = {"s2": S2, "landsat": LANDSAT}


def _query_for(sensor) -> dict:
    if sensor is LANDSAT:
        return {"platform": {"in": ["landsat-7", "landsat-8"]}}
    return {}


# ------------------------------------------------------------------ core
def _nbr(b):
    with np.errstate(invalid="ignore", divide="ignore"):
        return (b["nir"] - b["swir2"]) / (b["nir"] + b["swir2"])


def _pick(items, sensor, grid, disc, run, inputs, looks, role, p):
    for it in items[: p["max_tries"]]:
        if sensor.cloud(it) > p["max_scene_cloud"]:
            looks.append({"item": it.id, "date": str(item_date(it)), "role": role, "clear": None,
                          "skipped": "scene cloud"})
            continue
        clear = sensor.clear(it, grid, run, inputs)
        cf = float(clear[disc].mean()) if disc.any() else 0.0
        looks.append({"item": it.id, "date": str(item_date(it)), "role": role, "clear": round(cf, 3)})
        if cf >= p["min_clear"]:
            return it, clear
    return None, None


def _hotspots(sensor, items, grid, disc, run, inputs):
    """Schroeder et al. 2016 Landsat-8 tests on SWIR2/SWIR1/NIR, applied to looks taken during the window."""
    out = []
    for it in items[:3]:
        b = sensor.bands(it, grid, run, inputs)
        clear = sensor.clear(it, grid, run, inputs)
        r5, r6, r7 = b["nir"], b["swir1"], b["swir2"]
        with np.errstate(invalid="ignore", divide="ignore"):
            r75 = r7 / r5
            r76 = r7 / r6
        unamb = ((r75 > 2.5) & ((r7 - r5) > 0.3) & (r7 > 0.5)) | ((r6 > 0.8) & (r7 < 0.1) & (b["vis"] < 0.2))
        cand = (r75 > 1.8) & ((r7 - r5) > 0.17) & (r76 > 1.6)
        bgm = clear & ~cand & np.isfinite(r75)
        if bgm.sum() > 50:
            m75, s75 = np.nanmean(r75[bgm]), np.nanstd(r75[bgm])
            m7, s7 = np.nanmean(r7[bgm]), np.nanstd(r7[bgm])
            ctx = (r75 > m75 + max(3 * s75, 0.8)) & (r7 > m7 + max(3 * s7, 0.08))
        else:
            ctx = np.zeros_like(cand)
        hot = (unamb | (cand & ctx)) & disc & np.isfinite(r7)
        if hot.any():
            ys, xs = np.nonzero(hot)
            out.append({"item": it.id, "date": str(item_date(it)), "sensor": sensor.name, "n_pixels": int(hot.sum()),
                        "x": [float(grid.X[y, x]) for y, x in zip(ys, xs)][:50],
                        "y": [float(grid.Y[y, x]) for y, x in zip(ys, xs)][:50], "epsg": grid.epsg})
    return out


def _to_wgs(geom, epsg):
    from pyproj import Transformer
    from shapely.ops import transform
    tr = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True).transform
    return transform(tr, geom)


def _shapes(mask, grid):
    from rasterio.features import shapes
    from shapely.geometry import shape
    from shapely.ops import unary_union
    if not mask.any():
        return None
    polys = [shape(g) for g, v in shapes(mask.astype("uint8"), mask=mask, transform=grid.transform) if v == 1]
    return unary_union(polys)


def scar_search(lon, lat, radius_m, start: date, end: date, area_m2: float | None, sensor="s2",
                mode="small", run="adhoc", params: dict | None = None, hot=True) -> ScarResult:
    from pyproj import Transformer
    from scipy import ndimage

    p = {**PARAMS, **(params or {})}
    S = SENSORS[sensor]
    inputs: list = []
    looks: list = []
    items = search(S.collection, lon, lat, start - timedelta(days=p["pre_days"]), end + timedelta(days=p["post_days"]),
                   _query_for(S))
    if not items:
        return ScarResult("no_clear_look", sensor=sensor, reject_reason="no acquisition", looks=looks)
    # one grid: the tile/zone most common among items
    tiles = {}
    for it in items:
        tiles.setdefault((S.tile(it), S.epsg(it)), []).append(it)
    (tile, epsg), items = max(tiles.items(), key=lambda kv: len(kv[1]))
    x, y = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True).transform(lon, lat)
    half = radius_m + max(p["window_min_m"], radius_m)
    res = S.res
    while 2 * half / res > p["max_window_px"]:
        res *= 2
    grid = Grid(epsg, x, y, half, res)
    dist = grid.dist()
    disc = dist <= radius_m
    pre_items = sorted([i for i in items if item_date(i) < start], key=item_date, reverse=True)
    post_items = sorted([i for i in items if item_date(i) > end], key=item_date)
    during = sorted([i for i in items if start <= item_date(i) <= end], key=item_date)
    hotspots = _hotspots(S, during, grid, disc, run, inputs) if (hot and during and res == S.res) else []
    pre, cpre = _pick(pre_items, S, grid, disc, run, inputs, looks, "pre", p)
    post, cpost = _pick(post_items, S, grid, disc, run, inputs, looks, "post", p) if pre is not None else (None, None)
    if pre is None or post is None:
        return ScarResult("no_clear_look", sensor=sensor, reject_reason="no clear pre" if pre is None else "no clear post",
                          looks=looks, hotspots=hotspots, inputs=inputs)
    bpre = S.bands(pre, grid, run, inputs)
    bpost = S.bands(post, grid, run, inputs)
    nbr0, nbr1 = _nbr(bpre), _nbr(bpost)
    valid = cpre & cpost & np.isfinite(nbr0) & np.isfinite(nbr1) & (bpre["nir"] > 0) & (bpost["nir"] > 0)
    dnbr = nbr0 - nbr1
    bg = valid & ~disc
    if bg.sum() < 50:
        bg = valid
    med = float(np.median(dnbr[bg])) if bg.any() else 0.0
    mad = float(np.median(np.abs(dnbr[bg] - med))) * 1.4826 if bg.any() else 0.0
    thr = max(p["t_abs"], med + p["k_sigma"] * mad)
    cand = valid & (dnbr >= thr) & ((bpost["nir"] - bpre["nir"]) < p["dnir"]) & ((bpost["vis"] - bpre["vis"]) < p["dvis"])
    if p.get("dswir1_max") is not None:
        cand &= (bpost["swir1"] - bpre["swir1"]) < p["dswir1_max"]
    floor = scar_floor_m2(thr, grid.res, p["n_min"], p["dnbr_ref"])
    clear_frac = float(valid[disc].mean()) if disc.any() else 0.0
    res_ = ScarResult("no_scar_clear", sensor=sensor, pre_date=str(item_date(pre)), post_date=str(item_date(post)),
                      threshold=round(thr, 4), floor_m2=round(floor, 1), clear_fraction=round(clear_frac, 3),
                      looks=looks, hotspots=hotspots, inputs=inputs)
    regional = float(cand[bg].mean()) if bg.any() else 0.0
    lab, n = ndimage.label(cand, structure=np.ones((3, 3), bool))
    px = grid.res ** 2
    accepted = np.zeros_like(cand)
    comps = []
    if n:
        sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
        in_disc = ndimage.maximum(disc, lab, index=np.arange(1, n + 1))
        meds = ndimage.median(dnbr, lab, index=np.arange(1, n + 1))
        keep = [k + 1 for k in range(n) if sizes[k] >= p["n_min"] and in_disc[k]]
        if mode == "perimeter" and keep:
            # keep the component nearest the point plus everything connected to it (already one label)
            dmin = {k: float(dist[lab == k].min()) for k in keep}
            keep = [min(dmin, key=dmin.get)] + [k for k in keep if sizes[k - 1] * px > 0.05 * (area_m2 or 0)]
            keep = sorted(set(keep))
        for k in keep:
            c = {"label": int(k), "n_px": int(sizes[k - 1]), "area_m2": float(sizes[k - 1] * px),
                 "median_dnbr": round(float(meds[k - 1]), 4), "status": "accepted", "reason": None}
            if mode == "small" and c["median_dnbr"] < p.get("comp_min_dnbr", 0.0):
                c["status"], c["reason"] = "rejected", f"component median dNBR below {p['comp_min_dnbr']}"
            elif regional > p["regional_frac"] and mode == "small":
                c["status"], c["reason"] = "rejected", f"regional change ({regional:.2f} of neighbouring land)"
            elif mode == "small" and area_m2 is not None and c["area_m2"] > p["attr_factor"] * area_m2 + p["attr_add_m2"]:
                c["status"], c["reason"] = "rejected", "larger than the recorded fire allows (other event)"
            comps.append(c)
    # same dates in other years
    live = [c for c in comps if c["status"] == "accepted"]
    if live:
        ref = _reference(S, lon, lat, item_date(pre), item_date(post), grid, run, inputs, p, looks)
        for c in live:
            m = lab == c["label"]
            if ref is None:
                c["ref"] = "unchecked (no clear look in the two earlier years)"
                continue
            rd, rvalid, ry = ref
            mv = m & rvalid
            if mv.sum() < max(2, 0.5 * m.sum()):
                c["ref"] = "unchecked (reference pixels masked)"
                continue
            rmed = float(np.median(rd[mv]))
            c["ref"] = f"{ry}: median dNBR {rmed:.3f}"
            if rmed >= p["ref_ratio"] * c["median_dnbr"]:
                c["status"], c["reason"] = "rejected", f"recurs on the same dates in {ry} (seasonal or land use)"
    for c in comps:
        if c["status"] == "accepted":
            accepted |= lab == c["label"]
    res_.components = comps
    fire_area_disc = float((accepted & disc).sum() * px)
    if accepted.any():
        g = _shapes(accepted, grid)
        res_.geometry = _to_wgs(g, grid.epsg)
        res_.area_ha = float(accepted.sum() * px / 1e4)
        res_.status = "scar"
    elif comps:
        res_.status = "rejected"
        res_.reject_reason = "; ".join(sorted({c["reason"] for c in comps if c["reason"]}))
    # three states inside the disc
    nofire = disc & valid & ~accepted
    unknown = disc & ~valid
    res_.states = {"fire_m2": fire_area_disc, "no_fire_m2": float(nofire.sum() * px),
                   "unknown_m2": float(unknown.sum() * px), "epsg": grid.epsg}
    res_.states["fire"] = res_.geometry
    nf = _shapes(nofire, grid)
    uk = _shapes(unknown, grid)
    res_.states["no_fire"] = _to_wgs(nf.simplify(grid.res / 2), grid.epsg) if nf is not None else None
    res_.states["unknown"] = _to_wgs(uk.simplify(grid.res / 2), grid.epsg) if uk is not None else None
    res_._arrays = {"pre": bpre, "post": bpost, "dnbr": dnbr, "accepted": accepted, "valid": valid, "grid": grid}
    return res_


def _reference(S, lon, lat, d_pre, d_post, grid, run, inputs, p, looks):
    """dNBR over the same calendar dates one (else two) years earlier, on the same grid."""
    for yrs in (1, 2):
        def shift(d):
            try:
                return d.replace(year=d.year - yrs)
            except ValueError:
                return d.replace(year=d.year - yrs, day=28)
        a, b = shift(d_pre), shift(d_post)
        sl = timedelta(days=p["ref_slack_days"])
        items = [i for i in search(S.collection, lon, lat, a - sl, b + sl, _query_for(S)) if S.epsg(i) == grid.epsg]
        pres = sorted([i for i in items if abs((item_date(i) - a).days) <= p["ref_slack_days"]],
                      key=lambda i: abs((item_date(i) - a).days))
        posts = sorted([i for i in items if abs((item_date(i) - b).days) <= p["ref_slack_days"]
                        and item_date(i) > a], key=lambda i: abs((item_date(i) - b).days))
        disc = np.ones((grid.n, grid.n), bool)
        q = {**p, "min_clear": 0.5}
        pr, c0 = _pick(pres, S, grid, disc, run, inputs, looks, f"ref-{yrs}y-pre", q)
        if pr is None:
            continue
        po, c1 = _pick([i for i in posts if item_date(i) > item_date(pr)], S, grid, disc, run, inputs, looks,
                       f"ref-{yrs}y-post", q)
        if po is None:
            continue
        b0, b1 = S.bands(pr, grid, run, inputs), S.bands(po, grid, run, inputs)
        n0, n1 = _nbr(b0), _nbr(b1)
        v = c0 & c1 & np.isfinite(n0) & np.isfinite(n1)
        return n0 - n1, v, f"{item_date(pr)}..{item_date(po)}"
    return None


# ------------------------------------------------------------------ public API
def find_scar(lon: float, lat: float, radius_m: float, start: date, end: date, area_ha: float | None = None,
              sensors=("s2", "landsat"), run: str = "adhoc", params: dict | None = None,
              floor_check: bool = True) -> ScarResult:
    """Small-fire scar search inside the disc. Sentinel-2 first; Landsat when Sentinel-2 has no clear look."""
    area_m2 = area_ha * 1e4 if area_ha is not None else None
    p = {**PARAMS, **(params or {})}
    best_floor = scar_floor_m2(p["t_abs"], 20.0 if "s2" in sensors else 30.0, p["n_min"], p["dnbr_ref"])
    if floor_check and area_m2 is not None and area_m2 < best_floor:
        return ScarResult("below_floor", floor_m2=round(best_floor, 1),
                          reject_reason=f"recorded area {area_m2:.0f} m2 below the best scar floor {best_floor:.0f} m2")
    out = None
    hs = []
    for s in sensors:
        r = scar_search(lon, lat, radius_m, start, end, area_m2, s, "small", run, p)
        hs += r.hotspots
        if out is None or (out.status == "no_clear_look" and r.status != "no_clear_look") or \
                (r.status == "scar" and out.status != "scar"):
            if out is not None and out.status != "no_clear_look":
                r.looks = out.looks + r.looks
            out = r
        if r.status == "scar" or (r.status != "no_clear_look" and not p.get("landsat_if_no_scar")):
            break
    out.hotspots = hs
    return out


def make_perimeter(lon: float, lat: float, start: date, end: date, area_ha: float,
                   search_radius_m: float | None = None, sensors=("s2", "landsat"), run: str = "perimeter",
                   params: dict | None = None) -> ScarResult:
    """Perimeter of a large fire with no mapped perimeter: connected scar components near the point."""
    r_fire = math.sqrt(area_ha * 1e4 / math.pi)
    radius = search_radius_m or (1.5 * r_fire + 500.0)
    p = {**PARAMS, "window_min_m": max(PARAMS["window_min_m"], r_fire), **(params or {})}
    out = None
    for s in sensors:
        r = scar_search(lon, lat, radius, start, end, area_ha * 1e4, s, "perimeter", run, p, hot=False)
        if out is None or (out.status == "no_clear_look" and r.status != "no_clear_look"):
            out = r
        if r.status == "scar":
            break
    return out

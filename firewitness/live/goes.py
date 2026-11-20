"""GOES ABI access on the public NOAA S3 buckets (no key).

Reads only the pixels needed: HTTP range requests on the NetCDF4/HDF5 files, decoded with h5py from a
range-backed file object. h5py serialises all calls inside one process, so parallel reads use processes.

Times: a frame's time is its scan start (``s`` in the file name). Its availability time is the S3
LastModified of the file (when it could first be fetched), used for causal replay.
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

RAW_ROOT = Path(os.environ.get("FIREWITNESS_RAW", "/home/user/wildfire 3 (1)/firewitness_raw"))
LIST_CACHE = RAW_ROOT / "live" / "listings"

_FNAME = re.compile(r"OR_ABI-(?P<lvl>L1b|L2)-(?P<prod>[A-Za-z0-9]+)-M(?P<mode>\d)(?:C(?P<band>\d\d))?_(?P<sat>G\d\d)_"
                    r"s(?P<s>\d{14})_e(?P<e>\d{14})_c(?P<c>\d{14})\.nc")

# GRS80 ellipsoid used by the ABI fixed grid
REQ = 6378137.0
RPOL = 6356752.31414
ECC = 0.0818191910435
H_SAT = 35786023.0 + REQ


def parse_goes_time(s: str) -> datetime:
    """'20242001801191' (YYYYJJJHHMMSSt) -> aware UTC datetime."""
    y, j, hh, mm, ss, t = int(s[:4]), int(s[4:7]), int(s[7:9]), int(s[9:11]), int(s[11:13]), int(s[13])
    return datetime(y, 1, 1, tzinfo=timezone.utc) + timedelta(days=j - 1, hours=hh, minutes=mm, seconds=ss + t / 10)


def utc(x) -> datetime:
    if isinstance(x, datetime):
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    if isinstance(x, (int, float, np.integer, np.floating)):
        return datetime.fromtimestamp(float(x), tz=timezone.utc)
    return datetime.fromisoformat(str(x).replace("Z", "+00:00")).astimezone(timezone.utc)


# ---------------------------------------------------------------- HTTP
_tl = threading.local()


def session():
    s = getattr(_tl, "s", None)
    if s is None:
        s = requests.Session()
        ad = requests.adapters.HTTPAdapter(pool_connections=2, pool_maxsize=2)
        s.mount("https://", ad)
        _tl.s = s
    return s


def http_get(url, headers=None, tries=5, timeout=60):
    last = None
    for i in range(tries):
        try:
            r = session().get(url, headers=headers or {}, timeout=timeout)
            if r.status_code in (200, 206):
                return r
            if r.status_code == 404:
                r.raise_for_status()
            last = RuntimeError(f"HTTP {r.status_code} {url}")
        except requests.HTTPError:
            raise
        except Exception as e:  # network hiccup through the proxy
            last = e
        time.sleep(min(30, 1.5 * 2 ** i))
    raise last


class RangeFile(io.RawIOBase):
    """Read-only file object backed by HTTP range requests with a block cache."""

    B = 128 * 1024

    def __init__(self, url):
        self.url, self.pos, self.cache, self.nreq, self.nbytes = url, 0, {}, 0, 0
        r = http_get(url, {"Range": f"bytes=0-{self.B - 1}"})
        self.nreq += 1
        self.size = int(r.headers["Content-Range"].split("/")[1])
        self.cache[0] = r.content
        self.nbytes += len(r.content)

    def readable(self):
        return True

    def seekable(self):
        return True

    def seek(self, o, wh=0):
        self.pos = o if wh == 0 else (self.pos + o if wh == 1 else self.size + o)
        return self.pos

    def tell(self):
        return self.pos

    def readinto(self, buf):
        n = min(len(buf), self.size - self.pos)
        if n <= 0:
            return 0
        p, end = self.pos, self.pos + n
        i0, i1 = p // self.B, (end - 1) // self.B
        miss = [i for i in range(i0, i1 + 1) if i not in self.cache]
        if miss:
            a, b = miss[0] * self.B, min(self.size, (miss[-1] + 1) * self.B) - 1
            c = http_get(self.url, {"Range": f"bytes={a}-{b}"}).content
            self.nreq += 1
            self.nbytes += len(c)
            for j, i in enumerate(range(miss[0], miss[-1] + 1)):
                self.cache[i] = c[j * self.B:(j + 1) * self.B]
        out = bytearray()
        while p < end:
            i = p // self.B
            o = p - i * self.B
            blk = self.cache[i]
            take = min(end - p, len(blk) - o)
            out += blk[o:o + take]
            p += take
        buf[:n] = out
        self.pos = end
        return n


# ---------------------------------------------------------------- listing
def list_prefix(bucket: str, prefix: str, cache: bool = True) -> list[dict]:
    """List S3 keys under prefix with LastModified and size. Past hours are cached on disk."""
    cf = LIST_CACHE / bucket / (prefix.strip("/").replace("/", "_") + ".json")
    if cache and cf.is_file():
        return json.loads(cf.read_text())
    out, token = [], None
    while True:
        url = f"https://{bucket}.s3.amazonaws.com/?list-type=2&prefix={prefix}"
        if token:
            url += "&continuation-token=" + requests.utils.quote(token, safe="")
        r = http_get(url)
        root = ET.fromstring(r.content)
        ns = {"s": root.tag.split("}")[0].strip("{")}
        for c in root.findall("s:Contents", ns):
            out.append({"key": c.find("s:Key", ns).text, "lm": c.find("s:LastModified", ns).text,
                        "size": int(c.find("s:Size", ns).text)})
        t = root.find("s:NextContinuationToken", ns)
        if t is None:
            break
        token = t.text
    # cache only hours that are complete (older than 3 h)
    m = re.search(r"/(\d{4})/(\d{3})/(\d{2})/?$", prefix)
    if cache and m:
        hour = datetime(int(m[1]), 1, 1, int(m[3]), tzinfo=timezone.utc) + timedelta(days=int(m[2]) - 1)
        if datetime.now(timezone.utc) - hour > timedelta(hours=3):
            cf.parent.mkdir(parents=True, exist_ok=True)
            cf.write_text(json.dumps(out))
    return out


def hour_prefix(prefix: str, t: datetime) -> str:
    return f"{prefix}/{t.year:04d}/{t.timetuple().tm_yday:03d}/{t.hour:02d}/"


def frames(bucket: str, prefix: str, band: int | None, t0: datetime, t1: datetime) -> list[dict]:
    """Files of one product (and band) with scan start in [t0, t1). Each: key, t (scan start), avail, sat."""
    out = []
    h = t0.replace(minute=0, second=0, microsecond=0)
    while h < t1:
        for it in list_prefix(bucket, hour_prefix(prefix, h)):
            m = _FNAME.search(it["key"])
            if not m:
                continue
            if band is not None and (m["band"] is None or int(m["band"]) != band):
                continue
            ts = parse_goes_time(m["s"])
            if t0 <= ts < t1:
                out.append({"key": it["key"], "bucket": bucket, "t": ts.timestamp(), "sat": m["sat"],
                            "avail": utc(it["lm"]).timestamp(), "mode": int(m["mode"])})
        h += timedelta(hours=1)
    out.sort(key=lambda d: d["t"])
    # one file per scan start (duplicates re-processed: keep the first available)
    ded, seen = [], set()
    for d in out:
        k = round(d["t"] / 60)
        if k not in seen:
            seen.add(k)
            ded.append(d)
    return ded


# ---------------------------------------------------------------- geometry
def lonlat_to_scan(lon, lat, lon0):
    """Geodetic lon/lat (deg) -> ABI scan angles x, y (rad). NaN where not visible."""
    lam = np.radians(np.asarray(lon, float))
    phi = np.radians(np.asarray(lat, float))
    lam0 = math.radians(lon0)
    phic = np.arctan((RPOL ** 2 / REQ ** 2) * np.tan(phi))
    rc = RPOL / np.sqrt(1 - ECC ** 2 * np.cos(phic) ** 2)
    sx = H_SAT - rc * np.cos(phic) * np.cos(lam - lam0)
    sy = -rc * np.cos(phic) * np.sin(lam - lam0)
    sz = rc * np.sin(phic)
    vis = H_SAT * (H_SAT - sx) >= sy ** 2 + (REQ ** 2 / RPOL ** 2) * sz ** 2
    y = np.arctan(sz / sx)
    x = np.arcsin(-sy / np.sqrt(sx ** 2 + sy ** 2 + sz ** 2))
    return np.where(vis, x, np.nan), np.where(vis, y, np.nan)


def scan_to_lonlat(x, y, lon0):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    lam0 = math.radians(lon0)
    a = np.sin(x) ** 2 + np.cos(x) ** 2 * (np.cos(y) ** 2 + (REQ ** 2 / RPOL ** 2) * np.sin(y) ** 2)
    b = -2 * H_SAT * np.cos(x) * np.cos(y)
    c = H_SAT ** 2 - REQ ** 2
    disc = b ** 2 - 4 * a * c
    rs = (-b - np.sqrt(np.where(disc >= 0, disc, np.nan))) / (2 * a)
    sx = rs * np.cos(x) * np.cos(y)
    sy = -rs * np.sin(x)
    sz = rs * np.cos(x) * np.sin(y)
    lat = np.degrees(np.arctan((REQ ** 2 / RPOL ** 2) * (sz / np.sqrt((H_SAT - sx) ** 2 + sy ** 2))))
    lon = np.degrees(lam0 - np.arctan(sy / (H_SAT - sx)))
    return lon, lat


GRID_CACHE = Path(__file__).parent / "config" / "grids.json"


def grid_info(bucket: str, prefix: str, band: int | None, sat: str) -> dict:
    """Fixed-grid scale/offset and shape of a product (read once, cached in config/grids.json)."""
    key = f"{sat}:{prefix}:{band}"
    cache = json.loads(GRID_CACHE.read_text()) if GRID_CACHE.is_file() else {}
    if key in cache:
        return cache[key]
    import h5py
    t = datetime(2024, 7, 1, 18, tzinfo=timezone.utc)
    if sat == "G19":
        t = datetime(2025, 7, 1, 18, tzinfo=timezone.utc)
    if sat == "G17":
        t = datetime(2022, 7, 1, 18, tzinfo=timezone.utc)
    fr = frames(bucket, prefix, band, t, t + timedelta(hours=1))
    rf = RangeFile(f"https://{bucket}.s3.amazonaws.com/{fr[0]['key']}")
    h = h5py.File(rf, "r")
    xa, ya = dict(h["x"].attrs), dict(h["y"].attrs)
    proj = dict(h["goes_imager_projection"].attrs)
    info = {"x_scale": float(xa["scale_factor"][0]), "x_offset": float(xa["add_offset"][0]),
            "y_scale": float(ya["scale_factor"][0]), "y_offset": float(ya["add_offset"][0]),
            "nx": int(h["x"].shape[0]), "ny": int(h["y"].shape[0]),
            "lon0": float(proj["longitude_of_projection_origin"][0])}
    cache[key] = info
    GRID_CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True))
    return info


def lonlat_to_rc(lon, lat, g: dict):
    x, y = lonlat_to_scan(lon, lat, g["lon0"])
    col = (x - g["x_offset"]) / g["x_scale"]
    row = (y - g["y_offset"]) / g["y_scale"]
    return row, col


def rc_to_lonlat(row, col, g: dict):
    x = g["x_offset"] + np.asarray(col, float) * g["x_scale"]
    y = g["y_offset"] + np.asarray(row, float) * g["y_scale"]
    return scan_to_lonlat(x, y, g["lon0"])


# ---------------------------------------------------------------- reading boxes
def _box(ds, r0, c0, n, m):
    ny, nx = ds.shape
    out = None
    a0, a1, b0, b1 = max(0, r0), min(ny, r0 + n), max(0, c0), min(nx, c0 + m)
    data = ds[a0:a1, b0:b1]
    out = np.full((n, m), np.nan if data.dtype.kind == "f" else 0, dtype=data.dtype)
    out[a0 - r0:a1 - r0, b0 - c0:b1 - c0] = data
    return out, (a0, a1, b0, b1)


def read_job(job: dict) -> dict:
    """Read one file. job: url, kind ('bt'|'refl'|'acm'|'fdc'), boxes [(r0, c0, n, m)].

    Returns {'ok', 'boxes': [array], 'nreq', 'nbytes'}. bt -> brightness temperature K (float32, NaN missing);
    refl -> reflectance factor (float32); acm -> uint8 (255 missing); fdc -> int16 Mask (-1 missing)."""
    import h5py
    for attempt in range(4):
        try:
            rf = RangeFile(job["url"])
            h = h5py.File(rf, "r")
            kind = job["kind"]
            res = []
            if kind in ("bt", "refl"):
                ds = h["Rad"]
                at = ds.attrs
                sc, of = float(at["scale_factor"][0]), float(at["add_offset"][0])
                fill = int(at["_FillValue"][0])
                for (r0, c0, n, m) in job["boxes"]:
                    raw, (a0, a1, b0, b1) = _box(ds, r0, c0, n, m)
                    raw = raw.view(np.uint16) if raw.dtype == np.int16 else raw
                    valid = np.zeros((n, m), bool)
                    valid[a0 - r0:a1 - r0, b0 - c0:b1 - c0] = True
                    valid &= raw != (fill & 0xFFFF)
                    L = raw.astype(np.float32) * sc + of
                    if kind == "bt":
                        fk1, fk2 = float(h["planck_fk1"][()]), float(h["planck_fk2"][()])
                        bc1, bc2 = float(h["planck_bc1"][()]), float(h["planck_bc2"][()])
                        with np.errstate(invalid="ignore", divide="ignore"):
                            v = (fk2 / np.log(fk1 / np.where(L > 0, L, np.nan) + 1) - bc1) / bc2
                    else:
                        v = L * float(h["kappa0"][()])
                    v = np.where(valid, v, np.nan).astype(np.float32)
                    res.append(v)
            elif kind == "acm":
                ds = h["ACM"]
                for (r0, c0, n, m) in job["boxes"]:
                    raw, (a0, a1, b0, b1) = _box(ds, r0, c0, n, m)
                    v = np.full((n, m), 255, np.uint8)
                    v[a0 - r0:a1 - r0, b0 - c0:b1 - c0] = raw[a0 - r0:a1 - r0, b0 - c0:b1 - c0]
                    res.append(v)
            elif kind == "fdc":
                ds = h["Mask"]
                for (r0, c0, n, m) in job["boxes"]:
                    raw, (a0, a1, b0, b1) = _box(ds, r0, c0, n, m)
                    v = np.full((n, m), -1, np.int16)
                    v[a0 - r0:a1 - r0, b0 - c0:b1 - c0] = raw[a0 - r0:a1 - r0, b0 - c0:b1 - c0]
                    res.append(v)
            else:
                raise ValueError(kind)
            return {"ok": True, "boxes": res, "nreq": rf.nreq, "nbytes": rf.nbytes}
        except Exception as e:  # noqa: BLE001
            err = repr(e)
            if "404" in err:
                break
            time.sleep(2 * (attempt + 1))
    return {"ok": False, "boxes": None, "err": err, "nreq": 0, "nbytes": 0}


def run_jobs(jobs: list[dict], procs: int = 48) -> list[dict]:
    """Run read_job over many files with a process pool (h5py serialises threads)."""
    if not jobs:
        return []
    from multiprocessing import get_context
    with get_context("fork").Pool(min(procs, len(jobs))) as pool:
        return pool.map(read_job, jobs, chunksize=1)


def url_of(fr: dict) -> str:
    return f"https://{fr['bucket']}.s3.amazonaws.com/{fr['key']}"

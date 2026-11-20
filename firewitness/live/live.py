"""Part C: the live detector on the current public GOES stream (protocol §8).

Every 5-minute CONUS cycle: read bands 7 and 14 and the clear-sky mask of GOES-East and GOES-West, compute the
protocol §3 score for every pixel of the US box with the frozen Part B settings, update each pixel's CUSUM, and write
the candidates of that cycle to a JSON record before any outcome is known. Records are signed and committed by the
caller (GitHub Actions workflow, Sigstore keyless). Reconciliation against agency records is separate (reconcile.py).
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from . import goes
from . import signal as sg
from .detector import Config

HERE = Path(__file__).parent
SCHEMA = "firewitness.live.record/1"
FIRMS_NRT = {
    "VIIRS_NOAA20": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_USA_contiguous_and_Hawaii_7d.csv",
    "VIIRS_NOAA21": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-21-viirs-c2/csv/J2_VIIRS_C2_USA_contiguous_and_Hawaii_7d.csv",
    "VIIRS_SNPP": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_USA_contiguous_and_Hawaii_7d.csv",
    "MODIS": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_USA_contiguous_and_Hawaii_7d.csv",
}


def utcnow():
    return datetime.now(timezone.utc)


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_detector(region="us") -> tuple[Config, float, dict]:
    p = HERE / "config" / f"detector_{region}.json"
    d = json.loads(p.read_text())
    return Config.from_json(d["config"]), float(d["h"]), d


# ---------------------------------------------------------------- full-frame reading
def fetch_bytes(url):
    return goes.http_get(url, timeout=120).content


def decode(raw: bytes, kind: str, box):
    import h5py
    r0, r1, c0, c1 = box
    h = h5py.File(io.BytesIO(raw), "r")
    if kind == "bt":
        ds = h["Rad"]
        at = ds.attrs
        sc, of, fill = float(at["scale_factor"][0]), float(at["add_offset"][0]), int(at["_FillValue"][0])
        v = ds[r0:r1, c0:c1].view(np.uint16)
        L = v.astype(np.float32) * sc + of
        fk1, fk2 = float(h["planck_fk1"][()]), float(h["planck_fk2"][()])
        bc1, bc2 = float(h["planck_bc1"][()]), float(h["planck_bc2"][()])
        with np.errstate(all="ignore"):
            bt = (fk2 / np.log(fk1 / np.where(L > 0, L, np.nan) + 1) - bc1) / bc2
        return np.where(v == (fill & 0xFFFF), np.nan, bt).astype(np.float32)
    if kind == "acm":
        return h["ACM"][r0:r1, c0:c1].astype(np.uint8)
    raise ValueError(kind)


class SatStream:
    """One satellite: region box on its grid, ring buffer of residual frames, CUSUM state."""

    def __init__(self, sat: dict, bbox, cfg: Config):
        self.sat = sat
        self.name, self.bucket = sat["name"], sat["bucket"]
        self.g = goes.grid_info(self.bucket, "ABI-L1b-RadC", 7, self.name)
        lon0, lat0, lon1, lat1 = bbox
        lons = np.linspace(lon0, lon1, 60)
        lats = np.linspace(lat0, lat1, 30)
        LO, LA = np.meshgrid(lons, lats)
        r, c = goes.lonlat_to_rc(LO, LA, self.g)
        ok = np.isfinite(r) & np.isfinite(c)
        r, c = r[ok], c[ok]
        self.box = (max(0, int(r.min()) - 10), min(self.g["ny"], int(r.max()) + 11),
                    max(0, int(c.min()) - 10), min(self.g["nx"], int(c.max()) + 11))
        r0, r1, c0, c1 = self.box
        RR, CC = np.mgrid[r0:r1, c0:c1]
        self.lon, self.lat = goes.rc_to_lonlat(RR, CC, self.g)
        self.inside = np.isfinite(self.lat) & (self.lon >= lon0) & (self.lon <= lon1) & (self.lat >= lat0) & (self.lat <= lat1)
        self.cfg = cfg
        self.ring = {}       # slot epoch (int, rounded to 60 s) -> residual float16
        self.S = np.zeros(self.lat.shape, np.float32)
        self.files_used = []

    def list_slot(self, t, prod, band):
        fr = goes.frames(self.bucket, prod, band, goes.utc(t - 150), goes.utc(t + 150))
        return fr[0] if fr else None

    def frame(self, t, wait_s=0):
        """Residual and z inputs at scan time t: returns (r, clear-fraction, files) or (None, ..) if unavailable."""
        files = {}
        deadline = time.time() + wait_s
        while True:
            for prod, band, key in (("ABI-L1b-RadC", 7, "C07"), ("ABI-L1b-RadC", 14, "C14"), ("ABI-L2-ACMC", None, "ACM")):
                if key not in files:
                    f = self.list_slot(t, prod, band)
                    if f:
                        files[key] = f
            if len(files) == 3 or time.time() > deadline:
                break
            time.sleep(20)
        if len(files) < 3:
            return None, files
        with ThreadPoolExecutor(3) as ex:
            raws = dict(zip(files, ex.map(lambda k: fetch_bytes(goes.url_of(files[k])), files)))
        bt7 = decode(raws["C07"], "bt", self.box)
        bt14 = decode(raws["C14"], "bt", self.box)
        acm = decode(raws["ACM"], "acm", self.box)
        for k, f in files.items():
            f["sha256"] = hashlib.sha256(raws[k]).hexdigest()
        ref = sg.bt14_spatial_ref(bt14[None], acm[None])[0]
        clear = sg.clear_from_cloud(sg.effective_cloud(acm, bt14, ref))
        f = np.where(clear, bt7 - bt14, np.nan).astype(np.float32)
        r = residual_fast(f)
        return r, files

    def residual_hist(self, t):
        """Residual at scan time t from the ring buffer, fetching if needed (None if missing)."""
        key = int(round(t / 60))
        if key in self.ring:
            return self.ring[key]
        r, _ = self.frame(t)
        val = None if r is None else r.astype(np.float16)
        self.ring[key] = val
        return val

    def prune(self, t_now):
        lim = t_now - 8 * 86400
        for k in [k for k in self.ring if k * 60 < lim]:
            del self.ring[k]


def residual_fast(f):
    """sg.residual on a large 2-D frame, in row blocks."""
    out = np.full_like(f, np.nan)
    H = f.shape[0]
    step = 200
    for a in range(0, H, step):
        lo, hi = max(0, a - 4), min(H, a + step + 4)
        rr = sg.residual(f[lo:hi][None])[0]
        out[a:min(H, a + step)] = rr[a - lo:a - lo + min(step, H - a)]
    return out


def zscore_live(stream: SatStream, t, r_now):
    """z of the current frame against 7 previous days at t-5, t, t+5 min (protocol §3)."""
    hist = []
    for d in range(1, 8):
        for dk in (-300, 0, 300):
            h = stream.residual_hist(t - d * 86400 + dk)
            if h is not None:
                hist.append(h.astype(np.float32))
    if len(hist) < sg.MIN_HIST:
        return None, len(hist)
    st = np.stack(hist, 0)
    med, cnt = sg.nanmedian0(st)
    mad, _ = sg.nanmedian0(np.abs(st - med))
    sc = np.maximum(sg.S_FLOOR, 1.4826 * mad)
    med[cnt < sg.MIN_HIST] = np.nan
    z = (r_now - med) / sc
    z = sg.scene_filter(z[None])[0]
    return z, len(hist)


# ---------------------------------------------------------------- recent-fire mask from FIRMS NRT
def firms_recent(cache_dir: Path, now: float, days=9):
    """Polar detections of the last `days` days (kept across runs in cache_dir, since the public files hold 7 days)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    store = cache_dir / "firms_recent.json"
    pts = json.loads(store.read_text()) if store.is_file() else []
    status = {}
    for name, url in FIRMS_NRT.items():
        try:
            txt = goes.http_get(url, timeout=60).text
            n = 0
            for r in csv.DictReader(io.StringIO(txt)):
                hhmm = r["acq_time"].zfill(4)
                t = datetime.fromisoformat(r["acq_date"]).replace(hour=int(hhmm[:2]), minute=int(hhmm[2:]),
                                                                  tzinfo=timezone.utc).timestamp()
                pts.append([round(float(r["latitude"]), 4), round(float(r["longitude"]), 4), t])
                n += 1
            status[name] = {"ok": True, "n": n, "sha256": hashlib.sha256(txt.encode()).hexdigest()}
        except Exception as e:  # noqa: BLE001
            status[name] = {"ok": False, "err": type(e).__name__}
    pts = {(a, b, c) for a, b, c in pts if c >= now - days * 86400}
    pts = sorted(pts)
    store.write_text(json.dumps(pts))
    return np.array(pts) if pts else np.zeros((0, 3)), status


def recent_mask(stream: SatStream, pts: np.ndarray, t_now: float, km=5.0):
    """True where a polar detection lies within km in the 9 days before t_now."""
    m = np.zeros(stream.lat.shape, bool)
    if not len(pts):
        return m
    p = pts[pts[:, 2] < t_now]
    if not len(p):
        return m
    # rasterise onto the region grid by nearest pixel, then dilate by the pixel distance (~2-4 km/pixel)
    r, c = goes.lonlat_to_rc(p[:, 1], p[:, 0], stream.g)
    r = np.round(r).astype(float) - stream.box[0]
    c = np.round(c).astype(float) - stream.box[2]
    ok = np.isfinite(r) & np.isfinite(c) & (r >= 0) & (r < m.shape[0]) & (c >= 0) & (c < m.shape[1])
    m[r[ok].astype(int), c[ok].astype(int)] = True
    from scipy.ndimage import maximum_filter
    rad = 2   # 2 pixels ~ 4-6 km at CONUS view angles
    return maximum_filter(m, size=2 * rad + 1)


# ---------------------------------------------------------------- the service
class LiveService:
    def __init__(self, region="us", log_dir: Path = Path("live-log"), cache_dir: Path = Path("live-cache"),
                 now: float | None = None):
        from firewitness.core import load_region
        self.rcfg = load_region(HERE, region)
        self.det, self.h, self.det_doc = load_detector(region)
        self.det_hash = hashlib.sha256(json.dumps(self.det_doc, sort_keys=True).encode()).hexdigest()
        now = now or time.time()
        sats = {}
        for s in self.rcfg["satellites"]:
            a = goes.utc(s["from"]).timestamp()
            b = goes.utc(s["to"]).timestamp() if s["to"] else 1e12
            if a <= now < b:
                sats[s["role"]] = s
        self.E = SatStream(sats["east"], self.rcfg["bbox_lonlat"], self.det)
        self.W = SatStream(sats["west"], self.rcfg["bbox_lonlat"], self.det) if "west" in sats else None
        if self.W is not None:
            r, c = goes.lonlat_to_rc(self.E.lon, self.E.lat, self.W.g)
            r = np.round(r) - self.W.box[0]
            c = np.round(c) - self.W.box[2]
            ok = np.isfinite(r) & np.isfinite(c) & (r >= 0) & (r < self.W.lat.shape[0]) & (c >= 0) & (c < self.W.lat.shape[1])
            self.mapW = (np.where(ok, r, 0).astype(np.int32), np.where(ok, c, 0).astype(np.int32), ok)
        self.alerted = np.zeros(self.E.lat.shape, bool)
        self.active = []      # candidates: dict(id, pixels set, last_t, first_t)
        self.log_dir, self.cache_dir = Path(log_dir), Path(cache_dir)
        self.last_slot = None
        self.firms_pts, self.firms_status, self.firms_t = np.zeros((0, 3)), {}, 0

    # -- state handoff
    def save_state(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, SE=self.E.S, SW=self.W.S if self.W else np.zeros(0), alerted=self.alerted,
                            meta=np.array(json.dumps({"last_slot": self.last_slot, "active": [
                                {**a, "pixels": sorted(a["pixels"])} for a in self.active], "det_hash": self.det_hash})))

    def load_state(self, path: Path) -> bool:
        if not path.is_file():
            return False
        z = np.load(path, allow_pickle=True)
        meta = json.loads(str(z["meta"]))
        if meta.get("det_hash") != self.det_hash:
            return False
        if z["SE"].shape != self.E.S.shape:
            return False
        self.E.S = z["SE"]
        if self.W is not None and z["SW"].shape == self.W.S.shape:
            self.W.S = z["SW"]
        self.alerted = z["alerted"]
        self.last_slot = meta["last_slot"]
        self.active = [{**a, "pixels": {tuple(p) for p in a["pixels"]}} for a in meta["active"]]
        return True

    def cycle(self, t: float, wait_s: int = 0) -> dict:
        """Process the CONUS scan starting at t (epoch s). Returns the record (not yet written)."""
        t_start = time.time()
        rec = {"schema": SCHEMA, "cycle_scan_start": iso(t), "processed_at": None, "region": self.rcfg["region"],
               "detector": {"config": self.det.to_json(), "h": self.h, "sha256": self.det_hash,
                            "frozen": self.det_doc.get("frozen", False), "note": self.det_doc.get("note", "")},
               "code_commit": os.environ.get("GITHUB_SHA") or _git_head(), "inputs": [], "satellites": {},
               "candidates": [], "notes": []}
        if time.time() - self.firms_t > 3600:
            self.firms_pts, self.firms_status = firms_recent(self.cache_dir, time.time())
            self.firms_t = time.time()
        rec["firms_nrt"] = self.firms_status
        U = {}
        for st in [self.E] + ([self.W] if self.W else []):
            r_now, files = st.frame(t, wait_s=wait_s)
            for k, f in files.items():
                rec["inputs"].append({"sat": st.name, "product": k, "key": f["key"], "scan_start": iso(f["t"]),
                                      "s3_last_modified": iso(f["avail"]), "sha256": f.get("sha256")})
            if r_now is None:
                rec["satellites"][st.name] = {"status": "missing frame"}
                continue
            st.ring[int(round(t / 60))] = r_now.astype(np.float16)
            z, nh = zscore_live(st, t, r_now)
            if z is None:
                rec["satellites"][st.name] = {"status": f"history too short ({nh} frames)"}
                continue
            from .detector import parse_ukey
            feat, compact = parse_ukey(self.det.ukey)
            if compact is not None:
                z = sg.compact_filter(z[None], compact)[0]
            u = sg.site_u(z[None], cap=99.0)[0]
            x = np.minimum(u, self.det.cap)
            fx = np.isfinite(x)
            st.S = np.where(fx, np.maximum(0, st.S + np.where(fx, x, 0) - self.det.k), st.S * self.det.decay)
            U[st.name] = u
            rec["satellites"][st.name] = {"status": "ok", "history_frames": nh,
                                          "clear_fraction": float(np.isfinite(r_now[st.inside]).mean()),
                                          "avail_latest": max(f["avail"] for f in files.values())}
            st.prune(t)
        # combine on the East grid
        SE = self.E.S
        if self.W is not None:
            ii, jj, ok = self.mapW
            SW = np.where(ok, self.W.S[ii, jj], 0.0)
            G = np.maximum(SE, SW)
            if not math.isinf(self.det.rho):
                both = (SE >= self.det.m) & (SW >= self.det.m)
                G = np.maximum(G, np.where(both, (SE + SW) / self.det.rho, 0))
        else:
            SW = np.zeros_like(SE)
            G = SE
        mask = recent_mask(self.E, self.firms_pts, t)
        G = np.where(mask | ~self.E.inside, 0, G)
        self.alerted &= G > 0                       # episode over -> may alert again later
        new = (G >= self.h) & ~self.alerted
        self.alerted |= new
        rec["masked_recent_fire_pixels"] = int((mask & self.E.inside).sum())
        rec["G_summary"] = {"max": round(float(G.max()), 2), "n_ge_half_h": int((G >= self.h / 2).sum()),
                            "n_ge_quarter_h": int((G >= self.h / 4).sum()), "n_in_episode": int((G > 0).sum())}
        rec["evaluated_pixels"] = int(self.E.inside.sum())
        rec["candidates"] = self._candidates(new, G, SE, SW, t)
        rec["processed_at"] = iso(time.time())
        rec["processing_s"] = round(time.time() - t_start, 1)
        self.last_slot = t
        return rec

    def _candidates(self, new, G, SE, SW, t):
        from scipy.ndimage import label
        lab, n = label(new, structure=np.ones((3, 3)))
        out = []
        self.active = [a for a in self.active if t - a["last_t"] <= 1800]
        for k in range(1, n + 1):
            pix = {tuple(map(int, p)) for p in np.argwhere(lab == k)}
            # attach to an active candidate if adjacent
            host = None
            for a in self.active:
                if any((p[0] + di, p[1] + dj) in a["pixels"] for p in pix for di in (-1, 0, 1) for dj in (-1, 0, 1)):
                    host = a
                    break
            arr = np.array(sorted(pix))
            g = G[arr[:, 0], arr[:, 1]]
            i = int(np.argmax(g))
            pi, pj = arr[i]
            item = {"lat": round(float(self.E.lat[pi, pj]), 4), "lon": round(float(self.E.lon[pi, pj]), 4),
                    "n_pixels": len(pix), "G": round(float(g[i]), 2), "S_east": round(float(SE[pi, pj]), 2),
                    "S_west": round(float(SW[pi, pj]), 2),
                    "witnesses": [s for s, v in ((self.E.name, SE[pi, pj]), (self.W.name if self.W else "", SW[pi, pj]))
                                  if s and v >= self.det.m],
                    "pixel_rc_east": [int(pi + self.E.box[0]), int(pj + self.E.box[2])]}
            if host is None:
                cid = f"L{datetime.fromtimestamp(t, timezone.utc):%Y%m%dT%H%M}Z-{len(out) + 1:03d}"
                host = {"id": cid, "pixels": set(), "first_t": t, "last_t": t}
                self.active.append(host)
                item["kind"] = "new"
            else:
                item["kind"] = "grows"
            host["pixels"] |= pix
            host["last_t"] = t
            item["id"] = host["id"]
            item["first_alert_scan"] = iso(host["first_t"])
            out.append(item)
        return out


def _git_head():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    except Exception:
        return None


def slot_times(t0: float, t1: float, cadence=300, phase=78):
    """CONUS scan starts (mode 6: hh:m1:18, hh:m6:18 UTC) in [t0, t1)."""
    a = math.ceil((t0 - phase) / cadence) * cadence + phase
    return list(np.arange(a, t1, cadence, dtype=float))


def record_path(log_dir: Path, t: float) -> Path:
    d = datetime.fromtimestamp(t, timezone.utc)
    return log_dir / f"{d:%Y}" / f"{d:%m}" / f"{d:%d}" / f"{d:%Y%m%dT%H%M}Z.json"


def write_record(log_dir: Path, rec: dict, t: float) -> Path:
    p = record_path(log_dir, t)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        raise FileExistsError(p)        # records are never rewritten
    p.write_text(json.dumps(rec, indent=1, sort_keys=False))
    return p

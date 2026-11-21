"""Fire list for the live track: confirmed US wildfires, stratified sample, dev / sealed-test split by fire.

Confirmed = a WFIGS wildfire record (agency) with at least one polar satellite detection (FIRMS VIIRS S-NPP
nominal/high, or MODIS confidence >= 30) within ``match_km`` of the origin point in [discovery - 24 h,
discovery + 72 h]. GOES FDC detections are found later, per fire, by the trace-back (fires with no polar
detection are not in the pool; see DECISIONS).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from .goes import RAW_ROOT

WFIGS_FILE = RAW_ROOT / "live" / "wfigs" / "wfigs_incidents_ge10ac_20230110_20250406.json"
FIRMS_DIR = RAW_ROOT / "live" / "firms"


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dl = np.radians(np.asarray(lon2) - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def load_firms(years=(2023, 2024, 2025), sensors=("viirs-snpp", "modis"), viirs_conf=("n", "h"), modis_min=30):
    """Polar detections as arrays: lat, lon, t (epoch s), sensor code (0 VIIRS, 1 MODIS), daynight."""
    lat, lon, t, sen = [], [], [], []
    for s in sensors:
        for y in years:
            f = FIRMS_DIR / f"{s}_{y}_United_States.csv"
            if not f.is_file():
                continue
            with open(f) as fh:
                for r in csv.DictReader(fh):
                    c = r["confidence"]
                    if s.startswith("viirs"):
                        if c not in viirs_conf:
                            continue
                    else:
                        try:
                            if int(c) < modis_min:
                                continue
                        except ValueError:
                            continue
                    if r.get("type") not in (None, "", "0"):  # 0 = presumed vegetation fire
                        continue
                    hhmm = r["acq_time"].zfill(4)
                    dt = datetime.fromisoformat(r["acq_date"]).replace(hour=int(hhmm[:2]), minute=int(hhmm[2:]),
                                                                       tzinfo=timezone.utc)
                    lat.append(float(r["latitude"]))
                    lon.append(float(r["longitude"]))
                    t.append(dt.timestamp())
                    sen.append(0 if s.startswith("viirs") else 1)
    o = np.argsort(t)
    return {"lat": np.array(lat)[o], "lon": np.array(lon)[o], "t": np.array(t)[o], "sensor": np.array(sen)[o]}


class GridIndex:
    """0.1 degree bins for fast spatial lookup of detections."""

    def __init__(self, d):
        self.d = d
        self.bins = defaultdict(list)
        for i, (a, b) in enumerate(zip(np.floor(d["lat"] * 10).astype(int), np.floor(d["lon"] * 10).astype(int))):
            self.bins[(a, b)].append(i)
        self.bins = {k: np.array(v) for k, v in self.bins.items()}

    def near(self, lat, lon, km, t0=None, t1=None):
        a, b = int(math.floor(lat * 10)), int(math.floor(lon * 10))
        nb = int(math.ceil(km / 8.0)) + 1
        idx = [self.bins[(a + i, b + j)] for i in range(-nb, nb + 1) for j in range(-nb, nb + 1) if (a + i, b + j) in self.bins]
        if not idx:
            return np.array([], int)
        idx = np.concatenate(idx)
        d = haversine_km(lat, lon, self.d["lat"][idx], self.d["lon"][idx])
        keep = d <= km
        if t0 is not None:
            keep &= self.d["t"][idx] >= t0
        if t1 is not None:
            keep &= self.d["t"][idx] < t1
        return idx[keep]


def size_class(acres, edges):
    k = 0
    for i, e in enumerate(edges):
        if acres >= e:
            k = i
    return k


def build(cfg: dict, out_dir: Path, n_per_class: int = 60, seed: int = 51, match_km: float = 3.0,
          pre_km: float = 5.0, pre_days: int = 9, dedup_km: float = 5.0) -> dict:
    fl = cfg["fire_list"]
    feats = json.loads(WFIGS_FILE.read_text())
    t_lo, t_hi = (datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp() for x in fl["period"])
    lon0, lat0, lon1, lat1 = cfg["bbox_lonlat"]
    recs = []
    for f in feats:
        a = f["attributes"]
        g = f.get("geometry") or {}
        lat = a.get("InitialLatitude") or g.get("y")
        lon = a.get("InitialLongitude") or g.get("x")
        if lat is None or lon is None or a.get("FireDiscoveryDateTime") is None:
            continue
        if a.get("POOState") and a["POOState"].replace("US-", "") in fl["states_excluded"]:
            continue
        if not (lon0 <= lon <= lon1 and lat0 <= lat <= lat1):
            continue
        acres = a.get("FinalAcres") or a.get("IncidentSize") or 0
        if acres < fl["min_acres"]:
            continue
        td = a["FireDiscoveryDateTime"] / 1000.0
        if not (t_lo <= td < t_hi):
            continue
        recs.append({"fire_id": a["UniqueFireIdentifier"] or f"OBJ{a['OBJECTID']}", "irwin": (a.get("IrwinID") or "").lower(),
                     "name": (a.get("IncidentName") or "").strip().title(), "lat": float(lat), "lon": float(lon),
                     "discovery_t": td, "acres": float(acres), "state": (a.get("POOState") or "").replace("US-", ""),
                     "cause": a.get("FireCauseGeneral") or a.get("FireCause"), "fuel": a.get("PredominantFuelGroup")})
    n_raw = len(recs)
    # dedup: same fire recorded twice (complex children, duplicates) -> keep largest
    recs.sort(key=lambda r: -r["acres"])
    kept = []
    gi = defaultdict(list)
    for r in recs:
        k = (int(r["lat"] * 10), int(r["lon"] * 10))
        dup = False
        for i in range(-1, 2):
            for j in range(-1, 2):
                for q in gi[(k[0] + i, k[1] + j)]:
                    if abs(q["discovery_t"] - r["discovery_t"]) < 2 * 86400 and \
                            haversine_km(r["lat"], r["lon"], q["lat"], q["lon"]) < dedup_km:
                        dup = True
        if not dup:
            kept.append(r)
            gi[k].append(r)
    n_dedup = len(kept)
    firms = load_firms()
    idx = GridIndex(firms)
    pool, why = [], defaultdict(int)
    for r in kept:
        td = r["discovery_t"]
        pre = idx.near(r["lat"], r["lon"], pre_km, td - pre_days * 86400, td - 86400)
        if len(pre):
            why["pre_existing_heat_within_5km_9d"] += 1
            continue
        m = idx.near(r["lat"], r["lon"], match_km, td - 86400, td + 72 * 3600)
        if not len(m):
            why["no_polar_detection"] += 1
            continue
        j = m[np.argmin(firms["t"][m])]
        r["polar_first_t"] = float(firms["t"][j])
        r["polar_first_sensor"] = "VIIRS-SNPP" if firms["sensor"][j] == 0 else "MODIS"
        r["polar_first_lat"], r["polar_first_lon"] = float(firms["lat"][j]), float(firms["lon"][j])
        r["n_polar_72h"] = int(len(m))
        r["size_class"] = size_class(r["acres"], fl["size_classes_acres"])
        pool.append(r)
    # stratified sample, then split by fire hash within class
    rng = random.Random(seed)
    sample = []
    for k in range(len(fl["size_classes_acres"])):
        cls = sorted([r for r in pool if r["size_class"] == k], key=lambda r: r["fire_id"])
        pick = cls if len(cls) <= n_per_class else rng.sample(cls, n_per_class)
        pick.sort(key=lambda r: hashlib.sha256((r["fire_id"] + str(seed)).encode()).hexdigest())
        for i, r in enumerate(pick):
            r["split"] = "dev" if i % 2 == 0 else "test"
        sample += pick
    sample.sort(key=lambda r: (r["split"], r["size_class"], r["fire_id"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    cols = ["fire_id", "split", "size_class", "acres", "name", "state", "lat", "lon", "discovery_t",
            "polar_first_t", "polar_first_sensor", "polar_first_lat", "polar_first_lon", "n_polar_72h", "cause", "fuel", "irwin"]
    with open(out_dir / "fires.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in sample:
            w.writerow(r)
    summ = {"n_wfigs_in_scope": n_raw, "n_after_dedup": n_dedup, "excluded": dict(why), "n_pool": len(pool),
            "pool_by_class": {str(k): sum(1 for r in pool if r["size_class"] == k) for k in range(4)},
            "n_sample": len(sample), "seed": seed, "n_per_class": n_per_class,
            "by_split_class": {f"{s}:{k}": sum(1 for r in sample if r["split"] == s and r["size_class"] == k)
                               for s in ("dev", "test") for k in range(4)}}
    (out_dir / "fires_summary.json").write_text(json.dumps(summ, indent=1))
    return summ


def build_supplement(verified_csv: Path, out_csv: Path, n_per_group: int = 10, seed: int = 51, match_km: float = 3.0):
    """Supplementary list from track 50's verified fires (never in the sealed test). Groups by FPA FOD size class:
    small A-C, medium D-E, large F-G. Site = first polar detection within 3 km in [label_t0 - 1 d, label_t0 + 3 d]."""
    rows = list(csv.DictReader(open(verified_csv)))
    years = sorted({int(r["label_t0"][:4]) for r in rows})
    firms = load_firms(years=tuple(years))
    idx = GridIndex(firms)
    groups = {"small": "ABC", "medium": "DE", "large": "FG"}
    rng = random.Random(seed)
    out = []
    for g, cls in groups.items():
        cand = sorted([r for r in rows if r["FIRE_SIZE_CLASS"] in cls], key=lambda r: r["rid"])
        rng.shuffle(cand)
        got = 0
        for r in cand:
            if got >= n_per_group:
                break
            lat, lon = float(r["LATITUDE"]), float(r["LONGITUDE"])
            t0 = datetime.fromisoformat(r["label_t0"]).replace(tzinfo=timezone.utc).timestamp()
            pre = idx.near(lat, lon, 5.0, t0 - 9 * 86400, t0 - 86400)
            if len(pre):
                continue
            m = idx.near(lat, lon, match_km, t0 - 86400, t0 + 3 * 86400)
            if not len(m):
                continue
            j = m[np.argmin(firms["t"][m])]
            acres = float(r["FIRE_SIZE"])
            out.append({"fire_id": "CAUGHT-" + r["rid"], "split": "supplement",
                        "size_class": size_class(acres, [10, 100, 1000, 10000]) if acres >= 10 else 0, "acres": acres,
                        "name": "", "state": "CA", "lat": lat, "lon": lon, "discovery_t": t0,
                        "polar_first_t": float(firms["t"][j]),
                        "polar_first_sensor": "VIIRS-SNPP" if firms["sensor"][j] == 0 else "MODIS",
                        "polar_first_lat": float(firms["lat"][j]), "polar_first_lon": float(firms["lon"][j]),
                        "n_polar_72h": int(len(m)), "cause": "", "fuel": "", "irwin": "", "caught_tier": r["tier"],
                        "caught_kinds": r["kinds"], "size_group": g})
            got += 1
    cols = list(out[0].keys())
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    return len(out)


def build_v02_test(cfg: dict, out_csv: Path, exclude_ids: set, n_per_class: int = 25, seed: int = 52) -> dict:
    """Trace-back v0.2 test set: fires from the v0.1 confirmed pool (same source, period and exclusions) never used
    before (not the 240, not the supplement), n_per_class per final-size class, random with the given seed."""
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    summ = build(cfg, tmp, n_per_class=10 ** 6, seed=seed)          # whole pool, every class
    pool = list(csv.DictReader(open(tmp / "fires.csv")))
    pool = [r for r in pool if r["fire_id"] not in exclude_ids]
    rng = random.Random(seed)
    out = []
    for k in range(4):
        cls = sorted([r for r in pool if int(r["size_class"]) == k], key=lambda r: r["fire_id"])
        out += cls if len(cls) <= n_per_class else rng.sample(cls, n_per_class)
    for r in out:
        r["split"] = "test_v02"
    out.sort(key=lambda r: (int(r["size_class"]), r["fire_id"]))
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    return {"pool_after_exclusion": len(pool), "n": len(out), "seed": seed,
            "by_class": {str(k): sum(1 for r in out if int(r["size_class"]) == k) for k in range(4)}}

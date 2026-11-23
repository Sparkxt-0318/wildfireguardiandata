"""Fire lists for the early growth rate (protocol/GROWTH_PROTOCOL.md §2).

Set A: every fire of the three earlier live lists, with its frozen start time from the released onset labels.
Set B: new fires from the same public incident source (WFIGS), 2023-01-10 to 2025-12-31, built with the v0.1 rules
(firewitness/live/firelist.py: de-duplication, polar confirmation, clean background), none in Set A, stratified by
final size class and split into dev and sealed halves by a hash of the fire id.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from .. import firelist as fl
from ..goes import RAW_ROOT
from .common import CFG, load_region, sha256_file

SET_A_FILES = {
    "v0.1": ("protocol/live_fires.csv", "results/live/onset_labels_v0.1.csv"),
    "v0.2": ("protocol/live_fires_v02_test.csv", "results/live/v02/onset_labels_v02_test.csv"),
    "supplement": ("protocol/live_fires_supplement_caught.csv", "results/live/supplement_caught_onset_labels.csv"),
}
WFIGS_URL = ("https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/WFIGS_Incident_Locations/"
             "FeatureServer/0/query")
FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/data/country/{s}/{y}/{s}_{y}_United_States.csv"
COLS = ["fire_id", "set", "split", "size_class", "acres", "name", "state", "lat", "lon", "discovery_t",
        "polar_first_t", "polar_first_sensor", "polar_first_lat", "polar_first_lon", "n_polar_72h", "cause", "fuel",
        "irwin", "source_list"]


def ts(x: str) -> float:
    return datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp()


# ---------------------------------------------------------------- downloads (public, no key)
def fetch_wfigs(period, out: Path) -> Path:
    import requests
    where = (f"IncidentTypeCategory='WF' AND FireDiscoveryDateTime >= DATE '{period[0][:10]}' AND "
             f"FireDiscoveryDateTime < DATE '{period[1][:10]}' AND (FinalAcres >= 10 OR IncidentSize >= 10)")
    feats, off = [], 0
    while True:
        r = requests.get(WFIGS_URL, params={"where": where, "outFields": "*", "outSR": 4326, "f": "json",
                                            "orderByFields": "OBJECTID", "resultOffset": off,
                                            "resultRecordCount": 2000}, timeout=120)
        r.raise_for_status()
        js = r.json()
        got = js.get("features", [])
        feats += got
        if not got or not js.get("exceededTransferLimit"):
            break
        off += len(got)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(feats))
    return out


def fetch_firms(years, sensors=("viirs-snpp", "modis")):
    import requests
    fl.FIRMS_DIR.mkdir(parents=True, exist_ok=True)
    got = {}
    for s in sensors:
        for y in years:
            f = fl.FIRMS_DIR / f"{s}_{y}_United_States.csv"
            if not f.is_file():
                with requests.get(FIRMS_URL.format(s=s, y=y), stream=True, timeout=600) as r:
                    r.raise_for_status()
                    tmp = f.with_suffix(".tmp")
                    with open(tmp, "wb") as fh:
                        for c in r.iter_content(1 << 20):
                            fh.write(c)
                    tmp.replace(f)
            got[f.name] = sha256_file(f)
    return got


# ---------------------------------------------------------------- Set A
def set_a() -> list[dict]:
    """Every Set A fire with its frozen start time t0 (released onset label, else the anchor T0)."""
    out = []
    for name, (lst, lab) in SET_A_FILES.items():
        labels = {r["fire_id"]: r for r in csv.DictReader(open(lab))}
        for r in csv.DictReader(open(lst)):
            L = labels[r["fire_id"]]
            onset = L.get("onset_utc") or None
            row = {k: r.get(k, "") for k in COLS}
            row.update({"set": "A", "split": "A", "source_list": name, "frozen_T0": L["T0"],
                        "frozen_onset": onset or "", "frozen_label_kind": L["label_kind"]})
            out.append(row)
    return out


# ---------------------------------------------------------------- Set B
def visible(lat, lon, region_cfg, t) -> list[str]:
    """Satellites whose CONUS grid holds the whole 40 x 40 box around the site (cached grid geometry, no network)."""
    from ..extract import HALF, sats_for
    from .. import goes
    out = []
    grids = json.loads(goes.GRID_CACHE.read_text())
    for role, s in sorted(sats_for(region_cfg, t).items()):
        key = f"{s['name']}:ABI-L1b-RadC:7"
        if key not in grids:
            continue
        g = grids[key]
        r, c = goes.lonlat_to_rc(lon, lat, g)
        if np.isfinite(r) and np.isfinite(c) and HALF <= round(float(r)) < g["ny"] - HALF and \
                HALF <= round(float(c)) < g["nx"] - HALF:
            out.append(s["name"])
    return out


def build_set_b(out_dir: Path, wfigs_file: Path) -> dict:
    cfg = CFG["set_b"]
    region = load_region()
    region = json.loads(json.dumps(region))
    region["fire_list"]["period"] = cfg["period"]
    fl.WFIGS_FILE = wfigs_file
    tmp = out_dir / "_pool"
    summ = fl.build(region, tmp, n_per_class=10 ** 6, seed=cfg["seed"])      # whole confirmed pool, v0.1 rules
    pool = list(csv.DictReader(open(tmp / "fires.csv")))
    A = set_a()
    a_ids = {r["fire_id"] for r in A}
    a_pts = [(float(r["lat"]), float(r["lon"]), float(r["discovery_t"])) for r in A]
    x0, x1 = (ts(x) for x in cfg["exclude_discovery"])
    why = {"in_set_a": 0, "near_set_a": 0, "satellite_switch": 0, "not_visible": 0}
    keep = []
    for r in pool:
        lat, lon, td = float(r["lat"]), float(r["lon"]), float(r["discovery_t"])
        if r["fire_id"] in a_ids:
            why["in_set_a"] += 1
            continue
        if any(abs(td - t) < cfg["exclude_near_set_a_days"] * 86400 and
               fl.haversine_km(lat, lon, la, lo) < cfg["exclude_near_set_a_km"] for la, lo, t in a_pts):
            why["near_set_a"] += 1
            continue
        if x0 <= td < x1:
            why["satellite_switch"] += 1
            continue
        sats = visible(float(r["polar_first_lat"]), float(r["polar_first_lon"]), region, td)
        if not sats:
            why["not_visible"] += 1
            continue
        r["visible_sats"] = "+".join(sats)
        keep.append(r)
    rng = random.Random(cfg["seed"])
    sample = []
    for k in range(4):
        cls = sorted([r for r in keep if int(r["size_class"]) == k], key=lambda r: r["fire_id"])
        pick = cls if len(cls) <= cfg["n_per_class"] else rng.sample(cls, cfg["n_per_class"])
        pick.sort(key=lambda r: hashlib.sha256((r["fire_id"] + cfg["split_salt"]).encode()).hexdigest())
        for i, r in enumerate(pick):
            r["split"] = "dev" if i % 2 == 0 else "sealed"
            r["set"] = "B"
            r["source_list"] = "growth_set_b"
        sample += pick
    sample.sort(key=lambda r: (r["split"], int(r["size_class"]), r["fire_id"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    f = out_dir / "growth_fires_set_b.csv"
    with open(f, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS + ["visible_sats"], extrasaction="ignore")
        w.writeheader()
        w.writerows(sample)
    res = {"wfigs_snapshot": wfigs_file.name, "wfigs_sha256": sha256_file(wfigs_file),
           "wfigs_records": len(json.loads(wfigs_file.read_text())), "v01_rules_summary": summ,
           "pool_after_v01_rules": len(pool), "excluded_after_pool": why, "pool_eligible": len(keep),
           "pool_eligible_by_class": {str(k): sum(1 for r in keep if int(r["size_class"]) == k) for k in range(4)},
           "n": len(sample),
           "by_split_class": {f"{s}:{k}": sum(1 for r in sample if r["split"] == s and int(r["size_class"]) == k)
                              for s in ("dev", "sealed") for k in range(4)},
           "by_east_satellite": {s: sum(1 for r in sample if r["visible_sats"].startswith(s)) for s in ("G16", "G19")},
           "file": f.name, "sha256": sha256_file(f), "made": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())}
    (out_dir / "growth_fires_set_b_summary.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


def write_set_a(out: Path) -> dict:
    rows = set_a()
    cols = COLS + ["frozen_T0", "frozen_onset", "frozen_label_kind"]
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return {"n": len(rows), "sha256": sha256_file(out)}


def all_fires(protocol_dir: Path = Path("protocol")) -> list[dict]:
    a = list(csv.DictReader(open(protocol_dir / "growth_fires_set_a.csv")))
    b = list(csv.DictReader(open(protocol_dir / "growth_fires_set_b.csv")))
    return a + b

"""Reconcile live candidates with agency incidents (WFIGS) and polar detections (FIRMS NRT), after the fact.

Run on records at least `min_age_h` old; writes live/reconcile/<UTC date>.json in the live-log checkout. Records are
never edited: reconciliation is a separate file made later, so every candidate was published before its outcome.
"""
from __future__ import annotations

import csv
import io
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from . import goes
from .firelist import haversine_km
from .live import FIRMS_NRT

WFIGS = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/WFIGS_Incident_Locations/FeatureServer/0/query"


def wfigs_since(t0: float):
    where = f"FireDiscoveryDateTime >= TIMESTAMP '{datetime.fromtimestamp(t0, timezone.utc):%Y-%m-%d %H:%M:%S}'"
    out, off = [], 0
    while True:
        r = goes.session().get(WFIGS, params={"where": where, "outFields": "UniqueFireIdentifier,IncidentName,"
                                              "FireDiscoveryDateTime,IncidentSize,InitialLatitude,InitialLongitude,"
                                              "IncidentTypeCategory", "returnGeometry": "true", "outSR": 4326,
                                              "f": "json", "resultOffset": off, "resultRecordCount": 2000}, timeout=60).json()
        fs = r.get("features", [])
        for f in fs:
            a = f["attributes"]
            g = f.get("geometry") or {}
            lat = a.get("InitialLatitude") or g.get("y")
            lon = a.get("InitialLongitude") or g.get("x")
            if lat is None or lon is None or a.get("FireDiscoveryDateTime") is None:
                continue
            out.append({"id": a["UniqueFireIdentifier"], "name": a.get("IncidentName"), "type": a.get("IncidentTypeCategory"),
                        "t": a["FireDiscoveryDateTime"] / 1000, "acres": a.get("IncidentSize"), "lat": lat, "lon": lon})
        off += len(fs)
        if not fs or not r.get("exceededTransferLimit"):
            break
    return out


def firms_points():
    pts = []
    for name, url in FIRMS_NRT.items():
        try:
            txt = goes.http_get(url, timeout=60).text
        except Exception:
            continue
        for r in csv.DictReader(io.StringIO(txt)):
            hhmm = r["acq_time"].zfill(4)
            t = datetime.fromisoformat(r["acq_date"]).replace(hour=int(hhmm[:2]), minute=int(hhmm[2:]), tzinfo=timezone.utc)
            pts.append((float(r["latitude"]), float(r["longitude"]), t.timestamp(), name))
    return pts


def reconcile(log_repo: Path, min_age_h=24.0, max_age_h=72.0):
    log = log_repo / "live" / "log"
    outd = log_repo / "live" / "reconcile"
    outd.mkdir(parents=True, exist_ok=True)
    now = time.time()
    cands = []
    for p in sorted(log.rglob("*Z.json")):
        try:
            rec = json.loads(p.read_text())
        except Exception:
            continue
        t = datetime.fromisoformat(rec["cycle_scan_start"].replace("Z", "+00:00")).timestamp()
        if not (now - max_age_h * 3600 <= t <= now - min_age_h * 3600):
            continue
        for c in rec.get("candidates", []):
            if c.get("kind") == "new":
                cands.append({**c, "record": p.name, "t": t, "published_at": rec.get("published_at")})
    if not cands:
        return {"n_candidates": 0}
    inc = wfigs_since(min(c["t"] for c in cands) - 2 * 86400)
    fp = firms_points()
    fa = np.array([(a, b, c) for a, b, c, _ in fp]) if fp else np.zeros((0, 3))
    res = []
    for c in cands:
        best = None
        for i in inc:
            if not (c["t"] - 24 * 3600 <= i["t"] <= c["t"] + 48 * 3600):
                continue
            d = haversine_km(c["lat"], c["lon"], i["lat"], i["lon"])
            if d <= 5 and (best is None or d < best[1]):
                best = (i, d)
        pol = []
        if len(fa):
            sel = (fa[:, 2] >= c["t"] - 12 * 3600) & (fa[:, 2] <= c["t"] + 24 * 3600)
            if sel.any():
                d = haversine_km(c["lat"], c["lon"], fa[sel, 0], fa[sel, 1])
                pol = sorted(fa[sel][d <= 3][:, 2].tolist())
        out = {"id": c["id"], "record": c["record"], "lat": c["lat"], "lon": c["lon"], "alert_scan": c["first_alert_scan"],
               "published_at": c["published_at"]}
        if best:
            i, d = best
            out.update({"outcome": "agency incident", "incident": i["id"], "incident_type": i["type"],
                        "discovery_utc": datetime.fromtimestamp(i["t"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "lead_vs_discovery_min": round((i["t"] - c["t"]) / 60, 1), "distance_km": round(d, 2)})
        elif pol:
            out.update({"outcome": "polar detection only", "first_polar_utc":
                        datetime.fromtimestamp(pol[0], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "lead_vs_polar_min": round((pol[0] - c["t"]) / 60, 1)})
        else:
            out["outcome"] = "unmatched (false alert or unrecorded heat)"
        res.append(out)
    day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H%MZ")
    f = outd / f"reconcile_{day}.json"
    f.write_text(json.dumps({"made": day, "window_h": [min_age_h, max_age_h], "n": len(res),
                             "wfigs_incidents_fetched": len(inc), "firms_points": len(fp), "candidates": res}, indent=1))
    from collections import Counter
    return {"n_candidates": len(res), "outcomes": dict(Counter(r["outcome"] for r in res)), "file": str(f)}

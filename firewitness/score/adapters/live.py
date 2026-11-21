"""Adapter for track 51's onset labels (protocol/live_fires.csv anchors; onset intervals from the trace-back when present).

Columns used: fire_id, lat, lon, acres, onset_lo_t, onset_hi_t (epoch seconds, UTC). When the trace-back columns are absent
the anchor `discovery_t` is both ends: the interval is then record-only and the scene says so in meta.
Per fire one Scene on a 0.2 km grid around the ignition point, 3 days before to 3 days after the onset:
  fire     = the burned footprint (radius from `acres`) from the day of onset_hi onward;
  no_fire  = that footprint on days earlier than the day of onset_lo minus 1 (not yet ignited; reasoned from the onset
             record, not from a satellite look, so meta['negatives'] = 'pre-ignition, not satellite verified');
  unknown  = everything else, including the ambiguous days inside and next to the onset interval.
"""
from __future__ import annotations

import csv

import numpy as np

from ..dataset import Dataset
from .states import build_scene, to_ordinal

ACRE_KM2 = 0.00404686


def _day(x) -> int:
    try:
        return to_ordinal(float(x))        # epoch seconds
    except ValueError:
        return to_ordinal(str(x))          # ISO date or datetime


def from_rows(rows, cell_km: float = 0.2, half_days: int = 3) -> Dataset:
    scenes = {}
    for r in rows:
        lat, lon = float(r["lat"]), float(r["lon"])
        lo = r.get("onset_lo_t") or r["discovery_t"]
        hi = r.get("onset_hi_t") or r["discovery_t"]
        d_lo, d_hi = _day(lo), _day(hi)
        radius_km = max(float(np.sqrt(max(float(r.get("acres") or 1.0), 1.0) * ACRE_KM2 / np.pi)), cell_km)
        pad = radius_km + 2 * cell_km
        kmlon = 111.32 * np.cos(np.radians(lat))
        box = (lon - pad / kmlon, lat - pad / 111.32, lon + pad / kmlon, lat + pad / 111.32)
        d0, d1 = d_lo - half_days, d_hi + half_days

        def foot(la, lo_g, lat=lat, lon=lon, kmlon=kmlon, radius_km=radius_km):
            m = np.hypot((la - lat) * 111.32, (lo_g - lon) * kmlon) <= radius_km
            if not m.any():
                m[np.unravel_index(np.argmin(np.hypot(la - lat, lo_g - lon)), m.shape)] = True
            return m

        regs = [{"state": "unknown", "t0": d0, "t1": d1, "mask": lambda la, lo_g: np.ones(la.shape, bool)},
                {"state": "no_fire", "t0": d0, "t1": d_lo - 2, "mask": foot},
                {"state": "fire", "t0": d_hi, "t1": d1, "mask": foot}]
        regs = [g for g in regs if to_ordinal(g["t1"]) >= to_ordinal(g["t0"])]
        s = build_scene(str(r["fire_id"]), regs, box, cell_km, pad_km=0.0,
                        meta={"source": "live_fires", "record_only": not (r.get("_real_interval", bool(r.get("onset_lo_t")))),
                              "label_kind": r.get("_kind"),
                              "negatives": "pre-ignition, not satellite verified"})
        s.interval_slack = max(1, int(np.ceil((d_hi - d_lo) / 2)))
        scenes[s.fire_id] = s
    return Dataset("live_onset_labels", scenes, cell_km, {"source": "track 51 onset labels",
                   "state_rule": "fire from onset day; pre-ignition footprint = no_fire; rest unknown"})


def read_csv(path: str, **kw) -> Dataset:
    return from_rows(list(csv.DictReader(open(path, newline=""))), **kw)


def read_onset(onset_csv: str, fires_csv: str = "protocol/live_fires.csv", **kw) -> Dataset:
    """Track 51's `onset_labels_v0.1.csv` (ISO UTC onset_lo_t/onset_hi_t, label_utc) joined to live_fires.csv for lat/lon.
    Fires with no earlier onset ('anchor kept') use the anchor day as both ends of the interval."""
    pos = {r["fire_id"]: r for r in csv.DictReader(open(fires_csv, newline=""))}
    rows = []
    for r in csv.DictReader(open(onset_csv, newline="")):
        f = pos.get(r["fire_id"])
        if f is None:
            continue
        anchor = r.get("label_utc") or r.get("T0")
        rows.append({"fire_id": r["fire_id"], "lat": f["lat"], "lon": f["lon"], "acres": r.get("acres") or f["acres"],
                     "onset_lo_t": r.get("onset_lo_t") or anchor, "onset_hi_t": r.get("onset_hi_t") or anchor,
                     "discovery_t": anchor, "_real_interval": bool(r.get("onset_lo_t")), "_kind": r.get("label_kind")})
    return from_rows(rows, **kw)

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


def from_rows(rows, cell_km: float = 0.2, half_days: int = 3) -> Dataset:
    scenes = {}
    for r in rows:
        lat, lon = float(r["lat"]), float(r["lon"])
        lo = r.get("onset_lo_t") or r["discovery_t"]
        hi = r.get("onset_hi_t") or r["discovery_t"]
        d_lo, d_hi = to_ordinal(float(lo)), to_ordinal(float(hi))
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
                        meta={"source": "live_fires", "record_only": not r.get("onset_lo_t"),
                              "negatives": "pre-ignition, not satellite verified"})
        s.interval_slack = max(1, int(np.ceil((d_hi - d_lo) / 2)))
        scenes[s.fire_id] = s
    return Dataset("live_onset_labels", scenes, cell_km, {"source": "track 51 onset labels",
                   "state_rule": "fire from onset day; pre-ignition footprint = no_fire; rest unknown"})


def read_csv(path: str, **kw) -> Dataset:
    return from_rows(list(csv.DictReader(open(path, newline=""))), **kw)

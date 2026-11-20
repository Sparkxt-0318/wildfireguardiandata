"""Export for track 52 (video): per fire the frame series, the pixel signal and the detection times of each method.

Layout (agreed with track smoke, outbox 2026-11-20): results/live_export/<fire_id>/
  fire.json                 fire_id, name, final_acres, lat, lon, discovery_utc, satellites, pixel per satellite, box
  frames_<sat>_<band>.npz   t (int64 epoch s, scan start), bt (float32 [t, y, x]; K for C07/C14, reflectance for C01),
                            cloud (uint8 ACM: 0 clear, 1 prob. clear, 2 prob. cloudy, 3 cloudy, 255 missing)
  signal_<sat>.csv          per frame at the site pixel: t_utc, bt7, bt14, dT, background_pred, z, u, cusum,
                            cloud_flag, fdc_mask
  detections.csv            method, sat, t_utc (empty = not detected), note
Day 0 window only ([T0 - 12 h, T0 + 2 h]); boxes are 40 x 40 (2 km bands) and 40 x 40 at 1 km (band 1, central area).
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import signal as sg
from .extract import HALF, NDAYS, load_series
from .traceback import series_meta


def _iso(t):
    return "" if t is None or not np.isfinite(t) else datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def export_fire(fire: dict, out_root: Path, detections: list[dict]):
    fid = fire["fire_id"]
    meta = series_meta(fid)
    d = out_root / fid
    d.mkdir(parents=True, exist_ok=True)
    info = {"fire_id": fid, "name": fire.get("name"), "final_acres": float(fire["acres"]), "state": fire.get("state"),
            "lat": meta["lat"], "lon": meta["lon"], "discovery_utc": _iso(meta["discovery_t"]),
            "T0_utc": _iso(meta["T0"]), "T0_source": meta["T0_source"], "satellites": {}}
    for sat, sm in meta["sats"].items():
        s = load_series(fid, sat)
        info["satellites"][sat] = {"role": sm["role"], "pixel_rc_2km": [sm["r"], sm["c"]], "box_origin_2km": [sm["box_r0"], sm["box_c0"]],
                                   "box_origin_1km": [sm["box1_r0"], sm["box1_c0"]], "box_size": 40}
        t = np.nan_to_num(s["tscan"][0], nan=0).astype(np.int64)
        cloud = s["ACM"][0]
        for band, arr in (("C07", s["BT7"][0]), ("C14", s["BT14"][0]), ("C01", s["REF1"][0])):
            np.savez_compressed(d / f"frames_{sat}_{band}.npz", t=t, bt=arr.astype(np.float32),
                                cloud=cloud if band != "C01" else np.repeat(np.repeat(cloud, 2, 1), 2, 2)[:, 20:60, 20:60])
        f = sg.feature(s, "dT")
        r = sg.residual(f)
        med, sc = sg.history_stats(r, sg.bg_days(0, NDAYS))
        z = sg.scene_filter(((r[0] - med) / sc)[None])[0]
        u = sg.site_u(z[None])[0]
        S, _ = sg.cusum(u[:, HALF, HALF][:, None], 0.5)
        dT = s["BT7"][0] - s["BT14"][0]
        nb = dT[:, HALF, HALF] - r[0, :, HALF, HALF]       # neighbour median
        with open(d / f"signal_{sat}.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["t_utc", "bt7", "bt14", "dT", "background_pred", "z", "u", "cusum", "cloud_flag", "fdc_mask"])
            for k in range(len(t)):
                bp = nb[k] + med[k, HALF, HALF]
                w.writerow([_iso(s["tscan"][0, k]), _r(s["BT7"][0, k, HALF, HALF]), _r(s["BT14"][0, k, HALF, HALF]),
                            _r(dT[k, HALF, HALF]), _r(bp), _r(z[k, HALF, HALF]), _r(u[k, HALF, HALF]), _r(S[k, 0]),
                            int(not sg.clear_mask(cloud[k])[HALF, HALF]), int(s["FDC"][0, k, HALF, HALF])])
    (d / "fire.json").write_text(json.dumps(info, indent=1))
    with open(d / "detections.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["method", "sat", "t_utc", "note"])
        w.writeheader()
        w.writerows(detections)
    return d


def _r(x):
    return "" if x is None or not np.isfinite(x) else round(float(x), 3)

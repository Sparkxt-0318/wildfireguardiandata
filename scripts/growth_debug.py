"""Diagnostics on raw growth arrays (no growth value printed): per day, ACM missing / clear, BT7 valid, and where the
fire-power background is undefined. Usage: python scripts/growth_debug.py RAWDIR FIRE_ID SAT"""
import json, sys
from pathlib import Path
import numpy as np
from firewitness.live.extract import load_series
from firewitness.live import signal as sg
from firewitness.live.growth import series as gs

d, fid, sat = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
s = load_series(fid, sat, d)
for k in ("ACM", "BT7", "BT14", "tscan"):
    print(k, s[k].shape, s[k].dtype)
for day in range(s["BT7"].shape[0]):
    a = s["ACM"][day]
    print(f"day {day}: frames {int(np.isfinite(s['tscan'][day]).sum())} acm255 {float((a == 255).mean()):.3f} "
          f"acmclear {float((a < 2).mean()):.3f} bt7 {float(np.isfinite(s['BT7'][day]).mean()):.3f} "
          f"bt14 {float(np.isfinite(s['BT14'][day]).mean()):.3f}")
f = sg.feature(s, "bt7")
r = sg.residual(f)
print("feature valid by day", [round(float(np.isfinite(f[i]).mean()), 3) for i in range(f.shape[0])])
print("residual valid by day", [round(float(np.isfinite(r[i]).mean()), 3) for i in range(r.shape[0])])
med, sc = sg.history_stats(r, sg.bg_days(0, r.shape[0]))
print("hist med valid day0", round(float(np.isfinite(med).mean()), 3), "sc valid", round(float(np.isfinite(sc).mean()), 3))
print("lat/lon finite", bool(np.isfinite(s["lat"]).all()), bool(np.isfinite(s["lon"]).all()), float(s["lat"][20, 20]), float(s["lon"][20, 20]))
from firewitness.live.traceback_v02 import pixel_area_m2
A = pixel_area_m2(s["lat"].astype(float), s["lon"].astype(float))
print("area finite", float(np.isfinite(A).mean()), float(np.nanmedian(A)))

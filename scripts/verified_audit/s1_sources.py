"""Verified-tier audit, step 1: fetch and derive the non-imagery evidence sources with the frozen loaders.

Run with FIREWITNESS_RAW pointing at a scratch folder. MCD64A1 is NOT loaded nationally here (it would move every
monthly tile); it is read per candidate window in step 3 instead (protocol/VERIFIED_AUDIT_RUBRIC.md section 2).
"""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from firewitness.caught import hms, perimeters, records, standard
from firewitness.caught.fetch import fetch


def prefetch_hms(y0=2018, y1=2020):
    days = []
    d = date(y0, 1, 1) - timedelta(days=1)
    while d <= date(y1, 12, 31) + timedelta(days=1):
        days.append(d)
        d += timedelta(days=1)

    def one(d):
        out = []
        for url, rel in [(f"{hms.BASE}/Fire_Points/Text/{d:%Y}/{d:%m}/hms_fire{d:%Y%m%d}.txt", f"hms/fire/hms_fire{d:%Y%m%d}.txt"),
                         (f"{hms.BASE}/Smoke_Polygons/Shapefile/{d:%Y}/{d:%m}/hms_smoke{d:%Y%m%d}.zip", f"hms/smoke/hms_smoke{d:%Y%m%d}.zip")]:
            try:
                fetch(url, rel)
            except FileNotFoundError:
                out.append(rel)
            except Exception as e:  # reported, the loader retries
                out.append(f"{rel} {type(e).__name__}")
        return out

    with ThreadPoolExecutor(12) as ex:
        miss = [m for r in ex.map(one, days) for m in r]
    print("HMS missing:", miss, flush=True)


def main():
    cfg = records.region()
    which = sys.argv[1:] or ["firms", "hms", "mtbs", "perims", "states"]
    if "firms" in which:
        f = standard.load_firms([2018, 2019, 2020], cfg)
        print("firms", len(f), flush=True)
    if "hms" in which:
        prefetch_hms()
        print("hms fire", len(hms.load_fire(2018, 2020)), flush=True)
        print("hms smoke", len(hms.load_smoke(2018, 2020)), flush=True)
    if "mtbs" in which:
        print("mtbs", len(standard.load_mtbs(cfg)), flush=True)
    if "perims" in which:
        p = perimeters.load_all(2018, 2020)
        print("perims", p.source.value_counts().to_dict(), flush=True)
    if "states" in which:
        print("states", len(perimeters.states()), flush=True)


if __name__ == "__main__":
    main()

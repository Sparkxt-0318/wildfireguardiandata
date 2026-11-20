"""The 29-fire set: fetch independent layers, run the agent (LF2016 map), rule R3b, release overlays and the spread stretch."""
from __future__ import annotations
import json
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .fetch.area import fetch_area
from .fetch.rawindex import RAW_ROOT
from .grid import Grid

FIRES = RAW_ROOT / "fires29"
CATALOG = Path(__file__).parent / "fires29" / "catalog.json"


def fire_ids():
    return [f["id"] for f in json.loads(CATALOG.read_text())]


def fire_grid(fid):
    return Grid.from_dict(json.loads((FIRES / fid / "meta.json").read_text())["grid"])


def fetch_all(workers=3):
    def one(fid):
        try:
            fetch_area("F_" + fid, fire_grid(fid), maps=(2016,))
            print("done", fid, flush=True)
        except Exception:  # noqa: BLE001
            print("FAILED", fid, traceback.format_exc()[-500:], flush=True)
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, fire_ids()))


if __name__ == "__main__":
    fetch_all()


def run_all(out_json: Path | None = None):
    import numpy as np
    import rasterio
    from . import r3b, runner, spread, stretch
    cfg = runner.region_cfg()
    rows = []
    for fid in fire_ids():
        name = "F_" + fid
        d = FIRES / fid
        from .areas import area_dir
        try:
            fb = rasterio.open(area_dir(name) / "fbfm40_lf2016.tif").read(1)
            viol = ros = None
            r3b_ok = spread.available()
            if r3b_ok:
                viol, ros, _ = r3b.r3b_mask(d, fb, cfg)
            man = runner.run_area(name, "M16", cfg, arrival=viol)
            od = runner.OUT_ROOT / "M16" / name
            verdict = rasterio.open(od / "verdict.tif").read(1)
            sug = rasterio.open(od / "suggest.tif").read(1)
            rep = (verdict == 3) & (sug > 0)
            fb2 = np.where(rep, sug, fb).astype(np.int16)
            row = {"id": fid, "counts": man["counts"], "rule_counts": man["rule_counts"], "replaced_cells": int(rep.sum()),
                   "r3b_evaluated": r3b_ok}
            if r3b_ok:
                row["stretch"] = stretch.run_fire(d, fb, fb2, cfg)
            rows.append(row)
            print("fire", fid, row["counts"], "replaced", row["replaced_cells"], flush=True)
        except Exception:  # noqa: BLE001
            rows.append({"id": fid, "error": traceback.format_exc()[-400:]})
            print("FAILED", fid, flush=True)
    out_json = out_json or Path(__file__).resolve().parents[2] / "results" / "stretch_fires.json"
    out_json.write_text(json.dumps(rows, indent=1, default=str))
    return rows

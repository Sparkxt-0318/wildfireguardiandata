"""Per-fire worker: extraction, frozen trace-back, start time t0, fire and placebo series (protocol §1-§5).

Writes one compact npz + JSON per fire and satellite under <out>/<open|sealed>/. Sealed Set B fires go to a separate
folder so their series are never read before the single opening (protocol §6).
"""
from __future__ import annotations

import json
import time
import traceback as _tb
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .common import CFG


def iso(t):
    return None if t is None else datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() if s else None


class Firms:
    """Polar detections 2020 and 2023-2025: `.idx` (GridIndex) and `.clean` for the frozen trace-back placebo."""

    def __init__(self):
        from ..firelist import GridIndex, load_firms
        self.idx = GridIndex(load_firms(years=(2020, 2023, 2024, 2025)))

    def clean(self, lat, lon, t0, t1, km=5.0):
        return len(self.idx.near(lat, lon, km, t0 - 86400, t1 + 86400)) == 0


def start_time(fire, meta, label):
    """t0 = earlier of the frozen trace-back onset and the first standard detection T0 (protocol §1)."""
    if fire["set"] == "A":
        T0 = pts(fire["frozen_T0"])
        onset = pts(fire["frozen_onset"]) if fire["frozen_onset"] else None
        src = "polar" if abs(T0 - float(fire["polar_first_t"])) < 60 else "fdc"
    else:
        T0 = meta["T0"]
        onset = pts(label.get("onset_utc")) if label.get("onset_utc") else None
        src = meta["T0_source"]
    if onset is not None and onset <= T0:
        return onset, "onset_traceback", T0, src
    return T0, f"first_detection_{src}", T0, src


def process(fire: dict, region_cfg: dict, pool, firms: Firms, out: Path) -> dict:
    from .. import pipeline as pl, traceback as tb
    from ..extract import load_series
    from . import series as gs
    from .extract import extract_fire, series_dir
    fid = fire["fire_id"]
    sub = out / ("sealed" if fire["split"] == "sealed" else "open")
    sub.mkdir(parents=True, exist_ok=True)
    done = sub / f"{fid}.json"
    if done.is_file():
        return json.loads(done.read_text())
    t_start = time.time()
    meta = extract_fire(fire, region_cfg, pool)
    h = CFG["onset"]["h_A"]
    recs = []
    for sat in meta["sats"]:
        rec = tb.process_fire_sat(meta, sat, firms, nboot=CFG["onset"]["nboot"], variant=CFG["onset"]["variant"])
        rec["meta"] = {k: v for k, v in meta.items() if k != "sats"}
        recs.append(rec)
    thr = {role: {"h": float(h[role])} for role in ("east", "west")}
    rows = pl.traceback_table(recs, thr) if recs else []
    fd = {fid: {"name": fire.get("name", ""), "state": fire.get("state", ""), "acres": fire["acres"],
                "size_class": fire["size_class"], "split": fire["split"]}}
    label = pl.fire_labels(rows, fd)[0] if rows else {}
    res = {"fire_id": fid, "set": fire["set"], "split": fire["split"], "size_class": int(fire["size_class"]),
           "acres": float(fire["acres"]), "state": fire.get("state", ""), "lat": meta["lat"], "lon": meta["lon"],
           "discovery": iso(meta["discovery_t"]), "T0_recomputed": iso(meta["T0"]),
           "T0_source_recomputed": meta["T0_source"], "label_recomputed": {k: label.get(k) for k in
           ("label_kind", "onset_utc", "onset_sat", "e2_agree")}, "sats": {}}
    if not meta["sats"]:
        res["status"] = "no satellite sees the site"
    else:
        t0, kind, T0, src = start_time(fire, meta, label)
        res.update({"t0": iso(t0), "t0_kind": kind, "T0": iso(T0), "T0_source": src})
        for row, rec in zip(rows, recs):
            sat = rec["sat"]
            sm = meta["sats"][sat]
            s = load_series(fid, sat, series_dir())
            fs, ps = gs.compute(s, meta, sat, t0, firms.idx)
            npz = {f"f_{k}": np.asarray(v) for k, v in fs.items()}
            if ps:
                npz.update({"p_day": np.array([p["day"] for p in ps]), "p_di": np.array([p["di"] for p in ps]),
                            "p_dj": np.array([p["dj"] for p in ps]),
                            "p_kind": np.array([p["kind"] == "temporal" for p in ps]),
                            "p_tau_min": np.stack([p["tau_min"] for p in ps]).astype(np.float32),
                            "p_P": np.stack([p["P"] for p in ps]).astype(np.float32),
                            "p_N": np.stack([p["N"] for p in ps]).astype(np.float32)})
            np.savez_compressed(sub / f"{fid}_{sat}.npz", **npz)
            acm = s["ACM"][0]
            qc = {"acm_missing": float((acm == 255).mean()), "acm_clear": float((acm < 2).mean()),
                  "bt7_valid": float(np.isfinite(s["BT7"][0]).mean()), "bt14_valid": float(np.isfinite(s["BT14"][0]).mean()),
                  "frames_day0": int(np.isfinite(s["tscan"][0]).sum()),
                  "fire_frames_clear": int(np.asarray(fs["clear"]).sum()), "fire_frames": int(len(fs["clear"]))}
            res["sats"][sat] = {
                "role": sm["role"], "site_r": sm["r"], "site_c": sm["c"],
                "site_lat": float(s["lat"][20, 20]), "site_lon": float(s["lon"][20, 20]),
                "onset_recomputed": row["t_D"], "S_pre": row["S_pre"],
                "fdc_first": iso(sm["fdc_first"][0]) if sm["fdc_first"] else None,
                "fdc_first_power_mw": sm.get("fdc_first_power_mw"), "fdc_first_npix": sm.get("fdc_first_npix"),
                "n_files": sm["n_jobs"], "n_files_failed": sm["n_fail"], "n_placebo_anchors": len(ps), "qc": qc}
            print(f"  qc {fid} {sat} " + json.dumps(qc), flush=True)
        res["status"] = "ok"
    res["seconds"] = round(time.time() - t_start, 1)
    done.write_text(json.dumps(res, indent=1, default=str))
    return res


def run_shard(fires: list[dict], out: Path, procs: int = 32, raw_keep: bool = True) -> list:
    from multiprocessing import get_context
    from .common import load_region
    region = load_region()
    firms = Firms()
    errs = []
    with get_context("fork").Pool(procs) as pool:
        for i, f in enumerate(fires):
            t = time.time()
            try:
                r = process(f, region, pool, firms, out)
                msg = r.get("status")
            except Exception as e:  # noqa: BLE001
                errs.append({"fire_id": f["fire_id"], "error": repr(e), "trace": _tb.format_exc()[-2000:]})
                msg = "ERROR " + repr(e)[:200]
            print(f"[{i + 1}/{len(fires)}] {f['fire_id']} {f['split']} {msg} {time.time() - t:.0f}s", flush=True)
    (out / "errors.json").write_text(json.dumps(errs, indent=1))
    return errs

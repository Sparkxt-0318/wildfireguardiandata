"""Tool 2 on the raw ICS-209 incident tables (the tables ICS-209-PLUS was built from).

Run BEFORE the published cleaning of those tables is opened (see protocol section 5). Writes patches and a
findings summary; the findings file is committed first, the published cleaning is read afterwards.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ..core import PatchSet, hash_inputs, load_region
from . import geo, locate, paths


def run(out_dir: Path, params: locate.Params | None = None, limit_years: list[str] | None = None) -> dict:
    t0 = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = load_region(paths.REPO / "firewitness" / "records", "us")
    P = params or locate.Params()
    d = pd.read_parquet(paths.CANON / "ics_raw_all.parquet")
    if limit_years:
        d = d[d.file_year.isin(limit_years)]
    d = d.reset_index(drop=True)
    ev = locate.Evidence(geo.Admin(cfg), geo.Detections(), geo.Scars())
    fit_mask = (d["src"] == "ics209_2014").to_numpy()
    cand, (wit, pri), (lat, lon, start) = locate.repair_locations(d, ev, cfg, P, fit_on=fit_mask)
    dec = locate.decide(cand, len(d), P)
    lpatches = locate.location_patches(d, dec)
    lat2, lon2 = lat.copy(), lon.copy()
    r = (dec["action"] == "repair").to_numpy()
    lat2[r], lon2[r] = dec["alt_lat"].to_numpy()[r], dec["alt_lon"].to_numpy()[r]
    tcand, (twit, tpri), _ = locate.repair_times(d, ev, lat2, lon2, cfg, P, fit_mask=fit_mask)
    tdec = locate.decide_time(tcand, len(d), P)
    tpatches = locate.time_patches(d, tdec)
    ps = PatchSet(input_sha256=hash_inputs([paths.CANON / "ics_raw_all.parquet"])[str(paths.CANON / "ics_raw_all.parquet")]["sha256"],
                  tool="records.locate", meta={"params": P.__dict__ | {"enable": list(P.enable)}})
    ps.extend(lpatches + tpatches)
    ps.write(out_dir / "tool2_raw_ics.patches.jsonl")
    dec.assign(rid=d["rid"], file_year=d["file_year"], src=d["src"]).to_parquet(out_dir / "tool2_raw_ics.location_decisions.parquet")
    tdec.assign(rid=d["rid"], file_year=d["file_year"]).to_parquet(out_dir / "tool2_raw_ics.time_decisions.parquet")
    summary = {
        "n_records": int(len(d)),
        "location": {
            "reliabilities": {w.name: {"m": round(w.m, 4), "u": round(w.u, 4)} for w in wit}, "priors": pri,
            "actions": dec["action"].value_counts().to_dict(),
            "repair_kinds": dec.loc[dec["action"] == "repair", "alt_kind"].value_counts().to_dict(),
            "by_file_year": dec.assign(fy=d["file_year"]).groupby("fy")["action"].value_counts().unstack(fill_value=0).to_dict("index"),
        },
        "time": {
            "reliabilities": {w.name: {"m": round(w.m, 4), "u": round(w.u, 4)} for w in twit}, "priors": tpri,
            "actions": tdec["action"].value_counts().to_dict(),
            "repair_kinds": tdec.loc[tdec["action"] == "repair", "alt_kind"].value_counts().to_dict(),
        },
        "n_patches": len(ps), "seconds": round(time.time() - t0, 1),
        "inputs": hash_inputs([paths.CANON / "ics_raw_all.parquet"]),
        "patch_chain": ps.chain_hash(),
    }
    (out_dir / "tool2_raw_ics.summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    import sys
    print(json.dumps(run(paths.OUT / "tool2"), indent=1, default=str)[:4000])

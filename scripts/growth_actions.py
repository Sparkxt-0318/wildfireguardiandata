"""Steps of the growth track that run on GitHub Actions (.github/workflows/growth.yml), where the NOAA S3 buckets are
fast. Public data only, no key. Usage:

  python scripts/growth_actions.py inputs  --out DIR          # WFIGS snapshot, FIRMS archive, G19 constants
  python scripts/growth_actions.py lists   --inputs DIR --out DIR   # Set A file, Set B sample, crosswalk ids
  python scripts/growth_actions.py shard   --i K --n N --out DIR    # extract + series for one shard of the fires
  python scripts/growth_actions.py collect --in DIR --part open|sealed --out DIR   # compact release files
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np


def cmd_inputs(a):
    from firewitness.live.growth import firelist as gf
    from firewitness.live.growth.common import CFG
    from firewitness.live.growth.extract import band7_planck
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    w = gf.fetch_wfigs(CFG["set_b"]["period"], out / "wfigs_incidents_ge10ac_20230110_20251231.json")
    firms = gf.fetch_firms((2020, 2023, 2024, 2025))
    pl = band7_planck("noaa-goes19", "ABI-L1b-RadC", "G19", gf.ts("2025-07-01T18:00:00Z"))
    info = {"wfigs_file": w.name, "wfigs_sha256": gf.sha256_file(w), "firms_sha256": firms, "planck_band7_G19": pl}
    (out / "inputs.json").write_text(json.dumps(info, indent=1) + "\n")
    print(json.dumps(info, indent=1))


def cmd_lists(a):
    from firewitness.live.growth import firelist as gf
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    w = Path(a.inputs) / "wfigs_incidents_ge10ac_20230110_20251231.json"
    sb = gf.build_set_b(out, w)
    sa = gf.write_set_a(out / "growth_fires_set_a.csv")
    # permanent ids: the records crosswalk (release records-v0.1) holds FPA FOD, MTBS and ICS-209-PLUS ids
    import pandas as pd
    xw = pd.read_parquet(a.crosswalk)
    rows = []
    for r in csv.DictReader(open(out / "growth_fires_set_a.csv")):
        pid, how = "", "not linkable: the crosswalk covers FPA FOD, MTBS and ICS-209-PLUS ids (to 2020), not WFIGS/IRWIN"
        if r["fire_id"].startswith("CAUGHT-FOD"):
            fod = r["fire_id"].split("CAUGHT-FOD", 1)[1]
            m = xw[(xw.source.astype(str) == "fpa_fod") & (xw.source_id.astype(str) == fod)]
            pid, how = (m.perm_id.iloc[0], "crosswalk fpa_fod " + fod) if len(m) else ("", "FOD id not in crosswalk")
        rows.append({"fire_id": r["fire_id"], "perm_id": pid, "link": how})
    for r in csv.DictReader(open(out / "growth_fires_set_b.csv")):
        rows.append({"fire_id": r["fire_id"], "perm_id": "",
                     "link": "not linkable: the crosswalk covers FPA FOD, MTBS and ICS-209-PLUS ids (to 2020), not WFIGS/IRWIN"})
    with open(out / "growth_perm_ids.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["fire_id", "perm_id", "link"])
        wr.writeheader()
        wr.writerows(rows)
    print(json.dumps({"set_a": sa, "set_b": {k: sb[k] for k in ("n", "by_split_class", "pool_eligible_by_class",
                                                                  "excluded_after_pool", "by_east_satellite")}}, indent=1))


def cmd_shard(a):
    from firewitness.live.growth.firelist import all_fires
    from firewitness.live.growth.run import run_shard
    fires = all_fires()
    if a.only:
        fires = [f for f in fires if f["fire_id"] in set(a.only.split(","))]
    mine = [f for i, f in enumerate(fires) if i % a.n == a.i]
    print(f"shard {a.i}/{a.n}: {len(mine)} fires", flush=True)
    errs = run_shard(mine, Path(a.out), procs=a.procs)
    print(f"errors: {len(errs)}")
    for e in errs:
        print(e["fire_id"], e["error"])


def cmd_collect(a):
    """Combine the per-fire outputs of one part (open = Set A + Set B dev; sealed = Set B sealed) into release files."""
    import pandas as pd
    from firewitness.live.growth.firelist import all_fires
    src = Path(a.inp)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fl = {f["fire_id"]: f for f in all_fires()}
    perm = {r["fire_id"]: r["perm_id"] for r in csv.DictReader(open("protocol/growth_perm_ids.csv"))}
    metas = [json.loads(Path(p).read_text()) for p in sorted(glob.glob(str(src / "**" / a.part / "*.json"), recursive=True))]
    fires, ser, pla, runs = [], [], [], []
    for m in metas:
        runs.append({k: m.get(k) for k in ("fire_id", "set", "split", "status", "T0", "T0_source", "t0", "t0_kind",
                                           "T0_recomputed", "T0_source_recomputed", "seconds")}
                    | {"label_recomputed": json.dumps(m.get("label_recomputed"))})
        for sat, s in m.get("sats", {}).items():
            f = fl[m["fire_id"]]
            fires.append({"fire_id": m["fire_id"], "perm_id": perm.get(m["fire_id"], ""), "sat": sat, "role": s["role"],
                          "set": m["set"], "split": m["split"], "size_class": m["size_class"], "acres": m["acres"],
                          "state": m["state"], "name": f.get("name", ""), "discovery": m["discovery"],
                          "t0": m["t0"], "t0_kind": m["t0_kind"], "T0": m["T0"], "T0_source": m["T0_source"],
                          "site_lat": s["site_lat"], "site_lon": s["site_lon"], "fdc_first": s["fdc_first"],
                          "fdc_first_power_mw": s["fdc_first_power_mw"], "fdc_first_npix": s["fdc_first_npix"],
                          "onset_recomputed": s["onset_recomputed"], "S_pre": s["S_pre"],
                          "n_files": s["n_files"], "n_files_failed": s["n_files_failed"],
                          "n_placebo_anchors": s["n_placebo_anchors"]})
            hits = glob.glob(str(src / "**" / a.part / f"{m['fire_id']}_{sat}.npz"), recursive=True)
            z = np.load(hits[0])
            n = len(z["f_tau_min"])
            ser.append(pd.DataFrame({"fire_id": [m["fire_id"]] * n, "sat": [sat] * n,
                                     "t_scan": np.round(z["f_t_scan"], 1), "have_frame": z["f_have_frame"],
                                     "tau_min": np.round(z["f_tau_min"], 2).astype(np.float32),
                                     "P": z["f_P"].astype(np.float32), "P_lo": z["f_P_lo"].astype(np.float32),
                                     "P_hi": z["f_P_hi"].astype(np.float32), "N": z["f_N"].astype(np.float32),
                                     "fdc_n": z["f_fdc_n"].astype(np.int16), "fdc_npow": z["f_fdc_npow"].astype(np.int16),
                                     "fdc_P": z["f_fdc_P"].astype(np.float32)}))
            if "p_P" in z.files:
                na, nt = z["p_P"].shape
                pla.append(pd.DataFrame({
                    "fire_id": [m["fire_id"]] * (na * nt), "sat": [sat] * (na * nt),
                    "day": np.repeat(z["p_day"], nt).astype(np.int8), "di": np.repeat(z["p_di"], nt).astype(np.int8),
                    "dj": np.repeat(z["p_dj"], nt).astype(np.int8),
                    "kind": np.where(np.repeat(z["p_kind"], nt), "temporal", "spatial"),
                    "tau_min": np.round(z["p_tau_min"].ravel(), 2).astype(np.float32),
                    "P": z["p_P"].ravel().astype(np.float32), "N": z["p_N"].ravel().astype(np.float32)}))
    tag = a.part
    pd.DataFrame(fires).to_csv(out / f"growth_fires_{tag}.csv", index=False)
    pd.DataFrame(runs).to_csv(out / f"growth_runs_{tag}.csv", index=False)
    if ser:
        pd.concat(ser, ignore_index=True).to_parquet(out / f"growth_series_{tag}.parquet", index=False, compression="zstd")
    if pla:
        pd.concat(pla, ignore_index=True).to_parquet(out / f"growth_placebo_{tag}.parquet", index=False, compression="zstd")
    print(json.dumps({"part": tag, "fires": len(metas), "fire_satellites": len(fires),
                      "status": {s: sum(1 for m in metas if m.get("status") == s) for s in {m.get("status") for m in metas}}}))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("inputs"); s.add_argument("--out", required=True); s.set_defaults(f=cmd_inputs)
    s = sub.add_parser("lists"); s.add_argument("--inputs", required=True); s.add_argument("--out", required=True)
    s.add_argument("--crosswalk", required=True); s.set_defaults(f=cmd_lists)
    s = sub.add_parser("shard"); s.add_argument("--i", type=int, required=True); s.add_argument("--n", type=int, required=True)
    s.add_argument("--out", required=True); s.add_argument("--procs", type=int, default=32); s.add_argument("--only", default="")
    s.set_defaults(f=cmd_shard)
    s = sub.add_parser("collect"); s.add_argument("--in", dest="inp", required=True); s.add_argument("--part", required=True)
    s.add_argument("--out", required=True); s.set_defaults(f=cmd_collect)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()

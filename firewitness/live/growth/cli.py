"""`firewitness live growth`: the early growth rate (protocol/GROWTH_PROTOCOL.md).

  firewitness live growth [table]      table + numbers from the released series (no network, no key)
  firewitness live growth figure       the slide figure from the released series
  firewitness live growth recompute    recompute every number of results/GROWTH_RESULTS.md and compare
  firewitness live growth extract      new fires: says what it needs; with --run, extracts them (network)
  firewitness live growth open-sealed  the sealed half, once (maintainers; needs the sealed artifact)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DEFAULT_DIR = "release/growth-v0.1"


def register(p):
    p.add_argument("action", nargs="?", default="table",
                   choices=["table", "figure", "recompute", "extract", "open-sealed", "thresholds"])
    p.add_argument("--release", default=DEFAULT_DIR, help="folder with the released growth files")
    p.add_argument("--out", default="growth_out", help="where to write the table and numbers")
    p.add_argument("--fires", default=None, help="extract: CSV of fires in the protocol/live_fires.csv format")
    p.add_argument("--run", action="store_true", help="extract: really read GOES from NOAA S3 (network)")
    p.add_argument("--sealed-dir", default=None, help="open-sealed: folder with the growth-sealed artifact")
    p.add_argument("--i-am-opening-the-sealed-half", action="store_true", dest="open_sealed")
    p.set_defaults(func=cmd)


NEEDS = """Extracting new fires needs (nothing else, no key):
  - network access to the public NOAA buckets noaa-goes16 / noaa-goes17 / noaa-goes18 / noaa-goes19
    (only the HDF5 chunks of a 40 x 40 pixel box are read: about 8,000 range reads per fire and satellite);
  - the FIRMS country archive CSVs (VIIRS S-NPP and MODIS, public) for the fire years, in $FIREWITNESS_RAW/live/firms/,
    used to keep placebo anchors away from other fires;
  - pip install -e . numpy scipy h5py requests pandas pyarrow;
  - a fires CSV with the columns of protocol/live_fires.csv plus set, frozen_T0, frozen_onset (empty for new fires);
  - time: about 2-4 minutes per fire and satellite with 32 processes on a fast link (it was run on GitHub Actions,
    .github/workflows/growth.yml; a slow home link is not practical).
Then: firewitness live growth extract --fires my_fires.csv --out my_out --run
The output folder holds one npz + json per fire; scripts/growth_actions.py collect turns it into release-format files."""


def cmd(a):
    from . import report as rp
    if a.action == "extract":
        if not a.run or not a.fires:
            print(NEEDS)
            return 0 if not a.run else 2
        import csv
        from .run import run_shard
        fires = list(csv.DictReader(open(a.fires)))
        for f in fires:
            f.setdefault("set", "B"); f.setdefault("split", "new")
        errs = run_shard(fires, Path(a.out))
        print(json.dumps({"fires": len(fires), "errors": len(errs)}))
        return 0 if not errs else 1
    rel = Path(a.release)
    if not (rel / "growth_series_fire.parquet").is_file():
        print(f"no released series in {rel}: download release growth-v0.1 (all files) into that folder, or use --release")
        return 2
    if a.action == "open-sealed":
        return rp.open_sealed(a)
    if a.action == "thresholds":
        print(json.dumps(rp.thresholds_from_release(rel), indent=1))
        return 0
    if a.action == "recompute":
        return rp.recompute_main(rel, Path(a.out))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = rp.compute(rel)
    rp.write_outputs(res, out)
    if a.action == "figure":
        rp.figure(res["curves"], out / "growth_curves_sealed.png")
    print(json.dumps(res["numbers"]["headline"], indent=1, default=str))
    print(f"table and numbers written to {out}/")
    return 0

"""Coverage flags and the summary numbers."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import coverage, paths


def write(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    fod = pd.read_parquet(paths.CANON / "fod.parquet")
    mt = pd.read_parquet(paths.CANON / "mtbs.parquet")
    # covered = linked to an MTBS event (published link hidden is not needed here: use the re-derived links)
    from . import link_tasks as LT
    T, pairs, X, dec, _ = LT.decide_all("fod_mtbs")
    l = dec[dec.outcome == "link"]
    linked = np.zeros(len(fod), bool)
    linked[l.li.to_numpy()] = True
    wf_df, wf_g = coverage.load_wfigs_perimeters()
    inw = coverage.in_perimeter(fod.lat.to_numpy(), fod.lon.to_numpy(), fod.year.to_numpy(), wf_df, wf_g)
    covered = linked | inw
    flags = coverage.coverage_flags(fod, covered)
    flags.to_csv(out / "coverage_flags.csv", index=False)
    big = fod.acres >= 1000
    s = {"large_fires": int(big.sum()), "covered_by_mtbs_link": int((linked & big).sum()), "covered_by_wfigs": int((inw & big).sum()),
         "covered_any": int((covered & big).sum()), "uncovered": int((~covered & big).sum()), "flag_counts": flags.flag.value_counts().to_dict()}
    (out / "coverage_summary.json").write_text(json.dumps(s, indent=1))
    print(json.dumps(s, indent=1))

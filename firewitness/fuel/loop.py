"""One improvement-loop round (protocol section 9): apply ONE change, run dev, keep only if F1 ratio rises and F2 share does not rise."""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

from . import devloop, runner

CFG_PATH = Path(__file__).parent / "config" / "us.json"
LOG = devloop.RESULTS.parent / "ROUNDS_fuel.md"


def _score(o):
    return o["F1"]["ratio"], o["F2"]["share"], o["F1"]["n_a"], o["F2"]["k_contradicted"]


def round_(n: int, cause: str, change: str, mutate, baseline_label: str, base: dict | None = None):
    base = base or json.loads((devloop.RESULTS / f"dev_{baseline_label}_M22.json").read_text())
    orig = CFG_PATH.read_text()
    cfg = json.loads(orig)
    mutate(cfg)
    CFG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")
    out, _ = devloop.run_dev(f"r{n}", "M22")
    r0, f0, nc0, k0 = _score(base)
    r1, f1_, nc1, k1 = _score(out)
    keep = (r1 > r0) and (f1_ <= f0) and (nc1 >= 25)
    if not keep:
        CFG_PATH.write_text(orig)
    line = (f"| {n} | {cause} | {change} | F1 {r0:.2f} -> {r1:.2f} (n_c {nc0}->{nc1}, interval [{out['F1']['lo']:.2f},{out['F1']['hi']:.2f}]); "
            f"F2 {f0:.4f} -> {f1_:.4f} ({k0}->{k1} false alarms) | {'KEPT' if keep else 'REVERTED'} |\n")
    if not LOG.exists():
        LOG.write_text("# ROUNDS_fuel\n\nDev areas only. Keep a change only if the F1 ratio rises and the F2 false-alarm share does not rise (n_c >= 25).\n\n"
                       "| round | cause (read in dev wrong verdicts) | change | numbers (dev, M22, pooled) | decision |\n|---|---|---|---|---|\n")
    with open(LOG, "a") as fh:
        fh.write(line)
    print(line)
    return keep, (out if keep else base)

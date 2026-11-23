#!/usr/bin/env python3
"""growth_recompute.py — recompute every number of GROWTH_RESULTS.md from the release growth-v0.1 files alone.

Usage (in the folder holding the release files, or with --dir):
    pip install numpy pandas scipy pyarrow
    python growth_recompute.py [--dir FOLDER] [--out OUTFOLDER]

Steps: (1) check every file against SHA256SUMS.txt (when present); (2) recompute the placebo thresholds from the placebo
series and compare with growth_thresholds_us.json; (3) rebuild the table early_growth_v0.1 from the fire series;
(4) recompute every gate and headline number; (5) render GROWTH_RESULTS.md and compare it byte for byte with the
released copy, and compare the numbers and the table with the released files. Exit code 0 only if all match.
Needs nothing else: no network, no key, no other repository file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def flat(d, pre=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flat(v, f"{pre}{k}."))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out.update(flat(v, f"{pre}{i}."))
    else:
        out[pre[:-1]] = d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(HERE))
    ap.add_argument("--out", default="growth_recomputed")
    a = ap.parse_args()
    rel, out = Path(a.dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ok = True
    sums = rel / "SHA256SUMS.txt"
    if sums.is_file():
        bad = 0
        for line in sums.read_text().splitlines():
            h, name = line.split(None, 1)
            name = name.strip().lstrip("*")
            if (rel / name).is_file() and sha(rel / name) != h:
                print(f"CHECKSUM MISMATCH {name}")
                bad += 1
        print(f"checksums: {'all match' if not bad else f'{bad} mismatches'}")
        ok &= bad == 0
    try:
        import growth_report as rp
    except ImportError:
        from firewitness.live.growth import report as rp
    res = rp.compute(rel)
    rp.write_outputs(res, out)
    n = res["numbers"]
    print(f"thresholds recomputed from the placebo series equal the frozen file: {n['thresholds_recomputed_match_frozen']}")
    ok &= bool(n["thresholds_recomputed_match_frozen"])
    md = rp.render(n, res["prov"])
    (out / "GROWTH_RESULTS.md").write_text(md)
    ref = rel / "GROWTH_RESULTS.md"
    if ref.is_file():
        same = ref.read_text() == md
        print(f"GROWTH_RESULTS.md rendered from the recomputed numbers is byte-identical to the released file: {same}")
        if not same:
            import difflib
            for l in list(difflib.unified_diff(ref.read_text().splitlines(), md.splitlines(), "released", "recomputed", lineterm=""))[:40]:
                print(l)
        ok &= same
    refn = rel / "growth_numbers.json"
    if refn.is_file():
        A, B = flat(json.loads(refn.read_text())), flat(json.loads((out / "growth_numbers.json").read_text()))
        diff = [k for k in set(A) | set(B) if A.get(k) != B.get(k)]
        print(f"numbers: {len(A) - len([k for k in diff if k in A])} of {len(A)} values identical" + (f"; differ: {sorted(diff)[:10]}" if diff else ""))
        ok &= not diff
    reft = rel / "early_growth_v0.1.csv"
    if reft.is_file():
        same = sha(reft) == sha(out / "early_growth_v0.1.csv")
        print(f"table early_growth_v0.1.csv identical: {same}")
        ok &= same
    print("RECOMPUTE: " + ("ALL MATCH" if ok else "MISMATCH"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

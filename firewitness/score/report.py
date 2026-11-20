"""Render results/SCORE_RESULTS.md from gate outputs (so numbers are never retyped)."""
from __future__ import annotations

import json
import sys

from . import card as cardmod


def _j(x):
    return json.dumps(x, sort_keys=True)


def section(name, r):
    L = [f"## {name}", "", f"Dataset `{r['dataset']}`: {r['summary']['fires']} fires, {r['summary']['cell_days']:,} cell-days, "
         f"fire {r['summary']['fire']:,} ({100 * r['summary']['fire'] / r['summary']['cell_days']:.2f}%), unknown {r['summary']['unknown']:,}. "
         f"Split `{r['split']['sha256'][:12]}` folds {r['split']['folds']}, {r['split']['dropped']} fires dropped by the buffer.", ""]
    n1, n2, n3, n4, n5 = (r[k] for k in ("N1", "N2", "N3", "N4", "N5"))
    L += ["| gate | outcome | key numbers |", "|---|---|---|"]
    L.append(f"| N1 location memoriser | {'PASS' if n1['passed'] else 'FAIL'} | blocked strict F1 {n1['blocked_memoriser_f1_strict']} vs persistence {n1['blocked_persistence_f1_strict']} "
             f"(lift CI {n1['blocked_lift_strict_strict']['ci95']}); same model on random cell-day split F1 {n1['random_rows_memoriser']['f1']} ({n1['inflation_ratio_random_over_blocked_f1']}x inflation); "
             f"neighbour-day interpolator on random rows F1 {n1['interpolator_random_rows']['f1']} vs persistence {n1['random_rows_persistence']['f1']} |")
    L.append(f"| N2 flag everything | {'PASS' if n2['passed'] else 'FAIL'} | strict F1 {n2['f1_flag_everything_strict']} vs persistence {n2['f1_persistence_strict']}; area ratio {n2['area_ratio']}; loose-tolerance F1 {n2['f1_flag_everything_loose']} vs {n2['f1_persistence_loose']}; warning printed: {n2['over_prediction_warning_printed']} |")
    s3 = "; ".join(f"{k}: {v['status']}" for k, v in n3.items() if isinstance(v, dict) and "status" in v)
    L.append(f"| N3 leaks | {'PASS' if n3['passed'] else 'FAIL'} | {s3} |")
    L.append(f"| N4 order and re-run | {'PASS' if n4['passed'] else 'FAIL'} | card hashes: {_j(n4['hashes'])} |")
    def a(k, t):
        return n5[k][t]["area_ratio_top_danger"]
    L.append(f"| N5 matched vs random negatives (weather-only logistic) | {'PASS' if n5['passed'] else 'FAIL'} | top-danger predicted/true area at validation threshold: matched {a('matched', 'validation_threshold')} vs random {a('random', 'validation_threshold')} (pre-registered limit {n5['pre_registered_ratio_limit']}); at raw probability 0.5: matched {a('matched', 'fixed_0.5')} vs random {a('random', 'fixed_0.5')} |")
    if "N5_prox" in r:
        p = r["N5_prox"]
        L.append(f"| N5 variant: with proximity features | {'PASS' if p['passed'] else 'FAIL'} | validation threshold: matched {p['matched']['validation_threshold']['area_ratio_top_danger']} vs random {p['random']['validation_threshold']['area_ratio_top_danger']}; at 0.5: matched {p['matched']['fixed_0.5']['area_ratio_top_danger']} vs random {p['random']['fixed_0.5']['area_ratio_top_danger']} |")
    L.append("")
    return L


def main(argv):
    out = []
    for name, path in (a.split("=", 1) for a in argv[1:]):
        out += section(name, json.load(open(path)))
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv)

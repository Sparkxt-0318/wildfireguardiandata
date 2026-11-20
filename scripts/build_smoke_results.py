"""Builds the number tables of results/SMOKE_RESULTS.md from results/smoke/*.json (no number is typed by hand).
usage: python scripts/build_smoke_results.py > results/smoke/tables.md"""
import json, os, sys
import numpy as np

R = os.path.join(os.path.dirname(__file__), "..", "results", "smoke")


def load(n):
    p = os.path.join(R, n)
    return json.load(open(p)) if os.path.exists(p) else None


def ci(v, pct=False, d=3):
    if v is None:
        return "n/a"
    f = (lambda x: f"{100 * x:.1f}%") if pct else (lambda x: f"{x:.{d}f}")
    if isinstance(v, (list, tuple)) and len(v) == 3:
        return f"{f(v[0])} [{f(v[1])}, {f(v[2])}]"
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return f"[{f(v[0])}, {f(v[1])}]"
    return f(v)


def s1_table(name, d):
    s = d["s1"]; rows = [r for r in d["s1_rows"] if not r.get("excluded")]
    out = [f"### S1 known truth, {name}: {s['n_cases']} composites over {s['n_sequences']} sequences ({s['n_excluded']} excluded)", "",
           f"Source: `results/smoke/{name}_final.json` (`s1`, `s1_rows`). Intervals: 95% bootstrap over sequences.", "",
           "| quantity | value | target | met |", "|---|---|---|---|"]
    out.append(f"| opacity MAE where truth >= 0.10 | {ci(s['mae'])} | <= 0.10 | {'yes' if s['mae'][0] <= 0.10 else 'no'} |")
    out.append(f"| opacity bias | {ci(s['bias'])} | abs <= 0.05 | {'yes' if abs(s['bias'][0]) <= 0.05 else 'no'} |")
    for lv in ["L0", "0.10", "0.20", "0.40", "0.60"]:
        v = s.get(f"edge_{lv}_median")
        tgt = "<= 4 px" if lv in ("0.20", "0.40") else "report"
        met = ("yes" if v is not None and v <= 4 else "no") if lv in ("0.20", "0.40") else "-"
        out.append(f"| edge position error at {'noise level' if lv == 'L0' else lv}, median over composites (px at 512 x 384), n = {s.get(f'edge_{lv}_n')} | {ci(v, d=2)} | {tgt} | {met} |")
    out.append(f"| detection, all composites | {ci(s['detect_all'], pct=True)} | report | - |")
    out.append(f"| detection, alpha_max >= 0.6 | {ci(s['detect_amax>=0.6'], pct=True)} | >= 90% | {'yes' if s['detect_amax>=0.6'][0] >= 0.9 else 'no'} |")
    out.append(f"| first-smoke error, median abs (frames), n = {s.get('first_err_n')} | {ci(s.get('first_err_abs_median_frames'), d=1)} | <= 2 | {'yes' if (s.get('first_err_abs_median_frames') is not None and s['first_err_abs_median_frames'] <= 2) else 'no'} |")
    out.append(f"| planted-plume-free false smoke chains per composite | {s['false_smoke_chains_mean']:.2f} | report | - |")
    out += ["", "By smoke colour (the effect of an unknown endmember):", "", "| true smoke colour | n | MAE | bias | detection |", "|---|---|---|---|---|"]
    for e, v in s["by_endmember"].items():
        out.append(f"| {e} | {v['n']} | {v['mae']:.3f} | {v['bias']:+.3f} | {100 * v['detect']:.0f}% |")
    out += ["", "By planted opacity:", "", "| alpha_max | n | MAE | bias | detection |", "|---|---|---|---|---|"]
    for e, v in s["by_amax"].items():
        out.append(f"| {e} | {v['n']} | {v['mae']:.3f} | {v['bias']:+.3f} | {100 * v['detect']:.0f}% |")
    bins = [(0.1, "0.1-0.3"), (0.3, "0.3-0.5"), (0.5, "0.5-0.7"), (0.7, "0.7-1.0")]
    out += ["", "Bias by true opacity bin (measured minus planted, mean over composites that have pixels in the bin):", "", "| true opacity | n | bias | MAE |", "|---|---|---|---|"]
    for lo, lab in bins:
        b = np.array([r.get(f"bias_{lo:.1f}", np.nan) for r in rows], float); m = np.array([r.get(f"mae_{lo:.1f}", np.nan) for r in rows], float)
        out.append(f"| {lab} | {int(np.isfinite(b).sum())} | {np.nanmean(b):+.3f} | {np.nanmean(m):.3f} |")
    return "\n".join(out)


def s23_table(name, d):
    s = d["s2_s3"]
    out = [f"### S2 placebo and S3 first smoke, {name}", "", f"Source: `results/smoke/{name}_final.json` (`s2_s3`, `s2_s3_rows`).", ""]
    out.append(f"- Sequences: {s['n_sequences']} ({s['n_excluded']} excluded: {s['excluded'] if s['excluded'] else 'none'}).")
    out.append(f"- **S2**: {s['placebo_false_frames']} of {s['placebo_frames']} pre-ignition frames show a smoke region = {100 * s['placebo_rate']:.1f}% (95% bootstrap over sequences {ci(s['placebo_rate_pooled_ci'], pct=True)}); {s['sequences_with_false_frames']} of {s['n_sequences'] - s['n_excluded']} sequences have at least one false frame. Gate: at most 1%.")
    if s.get("s3_median_s") is not None:
        q = s["s3_q"]
        out.append(f"- **S3**: smoke confirmed in {s['detected']} of {s['n_sequences'] - s['n_excluded']} sequences ({100 * s['detected_share']:.0f}%; target at least 80%). Method time minus human offset (s), over the detected: median {q[2]:+.0f}, quartiles {q[1]:+.0f} to {q[3]:+.0f}, 10th to 90th percentile {q[0]:+.0f} to {q[4]:+.0f}. Earlier than the human label in {100 * s['s3_share_before_human']:.0f}%, later in {100 * s['s3_share_after_human']:.0f}%, within five minutes either way in {100 * s['s3_share_within_5min']:.0f}%.")
    return "\n".join(out)


def s5_table(name, d):
    s = d["s5"]
    out = [f"### S5 re-run and background window, {name}", "", f"Source: `results/smoke/{name}_final.json` (`s5`).", "",
           f"- Re-run identity: {s['identical']} of {s['n_identity']} sequences give byte-identical outputs (hash over every output file; the opacity archive by its decompressed arrays). Gate: all.", "",
           "| background window | sequences | detected in both runs | lost detection | first-smoke shift, median abs (s) | median (s), IQR | edge shift at 0.20, median (px), n |", "|---|---|---|---|---|---|---|"]
    for k, v in s.items():
        if not k.startswith("end"):
            continue
        out.append(f"| {k.replace('_', ', ')} | {v['n']} | {v['detected_in_both']} | {v['lost_detection']} | {ci(v['first_shift_median_abs_s'], d=0)} | {ci(v['first_shift_median_s'], d=0)}, {ci(v['first_shift_iqr_s'], d=0)} | {ci(v['edge_shift_median_px'], d=2)}, {v['edge_n']} |")
    return "\n".join(out)


def s4_table(d):
    out = ["### S4 human boxes on the opacity scale", "", "Source: `results/smoke/s4_final.json`. The effective level of a box is the level (noise level, 0.10, 0.20, 0.40, 0.60) whose region, grown from inside the box, has the bounding box with the best IoU against the human box.", ""]
    for key, title in [("hpwren", "HPWREN-BB boxes (9 fires, FIgLib frames)"), ("pyro", "Pyro-SDIS boxes (relaxed background, protocol A2)")]:
        v = d.get(key)
        if not v:
            continue
        s = v["summary"]
        out.append(f"**{title}**: n = {s['n']} boxes.")
        if s["n"]:
            lc = s["effective_level_counts"]
            out.append(f"- effective level counts: " + ", ".join(f"{k}: {n}" for k, n in lc.items()) + f", no region: {s['no_region']}")
            out.append(f"- best IoU: median {s['best_iou_median']:.2f}, quartiles {s['best_iou_quartiles'][0]:.2f} to {s['best_iou_quartiles'][1]:.2f}; median IoU at each level: " + ", ".join(f"{k}: {s[f'iou_{k}_median']:.2f}" for k in lc))
            out.append(f"- median opacity inside the box {s['alpha_median_in_box_median']:.2f}; share of the box above the noise level, median {s['share_box_above_noise_median']:.2f}")
        if key == "hpwren":
            out.append("- per fire (n boxes, median best IoU, level counts): " + "; ".join(f"{k[:24]} ({v2['n']}, {v2.get('best_iou_median', float('nan')):.2f}, {v2.get('effective_level_counts')})" for k, v2 in v["per_sequence"].items() if v2["n"]))
            if v.get("excluded"):
                out.append(f"- excluded: {v['excluded']}")
        else:
            out.append(f"- usable events processed: {v['n_events_usable']}; skipped: {v['skipped']}")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    for name in ("dev", "sealed"):
        d = load(f"{name}_final.json")
        if not d:
            continue
        print(f"## {name.capitalize()} sequences\n")
        print(s23_table(name, d)); print()
        print(s1_table(name, d)); print()
        if "s5" in d:
            print(s5_table(name, d)); print()
    d = load("s4_final.json")
    if d:
        print(s4_table(d))

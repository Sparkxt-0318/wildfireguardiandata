"""Pipelines: Part A trace-back tables and gates, Part B fit / replay tables. Results go to results/live/."""
from __future__ import annotations

import csv
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import traceback as tb
from .extract import SERIES_DIR, load_fires

TOL_MIN = 30.0


def iso(t):
    return None if t is None or (isinstance(t, float) and not math.isfinite(t)) else \
        datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, c - w), min(1.0, c + w))


def boot_median(x, n=2000, seed=0):
    x = np.asarray([v for v in x if v is not None], float)
    if not len(x):
        return (float("nan"),) * 3
    rng = np.random.default_rng(seed)
    meds = np.median(x[rng.integers(0, len(x), (n, len(x)))], 1)
    return (float(np.median(x)), float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5)))


# ---------------------------------------------------------------- Part A
def _proc(fid):
    firms = _proc.firms
    try:
        tb.run_fire(fid, firms, variant=_proc.variant)
        return fid, None
    except Exception as e:  # noqa: BLE001
        return fid, repr(e)


def process_fires(fids, procs=3, variant="A0"):
    from multiprocessing import get_context
    _proc.firms = tb.FirmsClean()
    _proc.variant = variant
    todo = [f for f in fids if tb.series_meta(f) is not None]
    with get_context("fork").Pool(procs) as pool:
        errs = [r for r in pool.imap_unordered(_proc, todo) if r[1]]
    return todo, errs


def threshold_by_role(recs, q=99.0):
    out = {}
    for role in ("east", "west"):
        S = [p["S_pre"] for r in recs if r["role"] == role for p in r["placebo"]]
        out[role] = {"h": tb.threshold(S, q), "n_placebo": len(S)}
    return out


def traceback_table(recs, thr):
    rows = []
    for r in recs:
        h = thr[r["role"]]["h"]
        f = tb.finalize(r, h)
        m = r["meta"]
        fd = r["fdc_first"]
        row = {"fire_id": r["fire_id"], "sat": r["sat"], "role": r["role"], "T0": iso(r["T0"]),
               "S_pre": round(f["S_pre"], 2), "h_A": round(h, 2), "onset": f["onset"],
               "t_D": iso(f.get("t_D")), "t_D_lo": iso(f.get("t_D_lo")), "t_D_hi": iso(f.get("t_D_hi")),
               "tau": iso(f.get("tau")), "boot_share": f.get("boot_share"),
               "fdc_first_this_sat": iso(fd[0]) if fd else None, "fdc_first_low_this_sat": iso(r["fdc_first_low"][0]) if r["fdc_first_low"] else None,
               "polar_first": iso(m["polar_first_t"]), "discovery": iso(m["discovery_t"]),
               "n_pre_frames": r["n_pre"], "n_clear_pre": r["n_clear_pre"]}
        tD = f.get("t_D")
        for ref, val in (("T0", r["T0"]), ("fdc_this_sat", fd[0] if fd else None), ("polar", m["polar_first_t"]),
                         ("discovery", m["discovery_t"])):
            row[f"lead_vs_{ref}_min"] = round((val - tD) / 60, 1) if (tD is not None and val is not None) else None
        row["_t"] = {"t_D": tD, "lo": f.get("t_D_lo"), "hi": f.get("t_D_hi")}
        rows.append(row)
    return rows


def fire_labels(rows, fires_by_id):
    """Combine satellites per fire (protocol §4 label; E2)."""
    by = {}
    for r in rows:
        by.setdefault(r["fire_id"], []).append(r)
    out = []
    for fid, rs in by.items():
        f = fires_by_id[fid]
        T0 = rs[0]["T0"]
        ons = [r for r in rs if r["onset"] and r["_t"]["t_D"] is not None]
        lab = {"fire_id": fid, "name": f["name"], "state": f["state"], "acres": float(f["acres"]),
               "size_class": int(f["size_class"]), "split": f["split"], "T0": T0, "n_sats": len(rs),
               "sats": "+".join(r["sat"] for r in rs)}
        agree = None
        if len(ons) == 2:
            a, b = ons
            d = abs(a["_t"]["t_D"] - b["_t"]["t_D"]) / 60
            ov = (a["_t"]["lo"] is not None and b["_t"]["lo"] is not None and
                  a["_t"]["lo"] <= b["_t"]["hi"] and b["_t"]["lo"] <= a["_t"]["hi"])
            agree = d <= TOL_MIN or ov
            lab["e2_abs_diff_min"] = round(d, 1)
            lab["e2_agree"] = agree
            pick = min(ons, key=lambda r: r["_t"]["t_D"]) if agree else max(ons, key=lambda r: r["_t"]["t_D"])
            lab["label_kind"] = "two witnesses" if agree else "witnesses disagree"
        elif len(ons) == 1:
            pick = ons[0]
            lab["label_kind"] = "one witness" + (" (other satellite: no onset)" if len(rs) == 2 else "")
        else:
            pick = None
            lab["label_kind"] = "no earlier onset (anchor kept)"
        if pick:
            lab.update({"onset_utc": pick["t_D"], "onset_lo": pick["t_D_lo"], "onset_hi": pick["t_D_hi"],
                        "evidence_start": pick["tau"], "onset_sat": pick["sat"],
                        "lead_vs_T0_min": pick["lead_vs_T0_min"], "lead_vs_polar_min": pick["lead_vs_polar_min"],
                        "lead_vs_discovery_min": pick["lead_vs_discovery_min"]})
            fdcs = [r["fdc_first_this_sat"] for r in rs if r["fdc_first_this_sat"]]
            if fdcs:
                fd = min(fdcs)
                lab["fdc_first"] = fd
                lab["lead_vs_fdc_min"] = round((datetime.fromisoformat(fd.replace("Z", "+00:00")).timestamp()
                                                - min(r["_t"]["t_D"] for r in [pick])) / 60, 1)
        else:
            fdcs = [r["fdc_first_this_sat"] for r in rs if r["fdc_first_this_sat"]]
            lab["fdc_first"] = min(fdcs) if fdcs else None
        lab["polar_first"] = rs[0]["polar_first"]
        lab["discovery"] = rs[0]["discovery"]
        out.append(lab)
    return out


def e1_cv(recs, folds=5, q=99.0, seed=51):
    """False-onset rate on held-out placebo anchors with h from the other folds (by fire)."""
    fids = sorted({r["fire_id"] for r in recs})
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(fids))
    fold = {fids[i]: k % folds for k, i in enumerate(perm)}
    res = {}
    for role in ("east", "west"):
        k_false = n_pl = 0
        k_on = n_f = 0
        for f in range(folds):
            tr = [p["S_pre"] for r in recs if r["role"] == role and fold[r["fire_id"]] != f for p in r["placebo"]]
            if not tr:
                continue
            h = tb.threshold(tr, q)
            te = [r for r in recs if r["role"] == role and fold[r["fire_id"]] == f]
            for r in te:
                for p in r["placebo"]:
                    n_pl += 1
                    k_false += p["S_pre"] >= h
                n_f += 1
                k_on += tb.finalize(r, h)["onset"]
        fp = wilson(k_false, n_pl)
        on = wilson(k_on, n_f)
        res[role] = {"placebo_false_onset": [k_false, n_pl, *fp], "fire_onset": [k_on, n_f, *on],
                     "pass": (n_pl > 0 and fp[2] <= 0.02 and on[1] > fp[2])}
    return res


def e2_stats(labels):
    d = [l for l in labels if l.get("e2_agree") is not None]
    k = sum(l["e2_agree"] for l in d)
    p = wilson(k, len(d))
    med = boot_median([l["e2_abs_diff_min"] for l in d])
    return {"n_dual_onset": len(d), "n_agree": k, "share": p, "median_abs_diff_min": med,
            "pass": bool(len(d) and p[0] >= 0.6 and med[0] <= TOL_MIN)}


def write_csv(path: Path, rows, cols=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    cols = cols or list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def traceback_main(a):
    fires = load_fires(a.fires)
    if a.split != "all":
        fires = [f for f in fires if f["split"] == a.split]
    fids = [f["fire_id"] for f in fires]
    if a.extract:
        from multiprocessing import get_context
        from firewitness.core import load_region
        from . import extract
        cfg = load_region(Path(__file__).parent, "us")
        with get_context("fork").Pool(44) as pool:
            for f in fires:
                extract.extract_fire(f, cfg, pool)
    variant = getattr(a, "variant", "A0")
    done, errs = process_fires(fids, variant=variant)
    recs = tb.load_records(done, variant=variant)
    thr = threshold_by_role(recs)
    rows = traceback_table(recs, thr)
    labels = fire_labels(rows, {f["fire_id"]: f for f in fires})
    out = Path(a.out)
    sfx = f"{a.split}_{variant}"
    write_csv(out / f"traceback_{sfx}_by_satellite.csv", rows)
    write_csv(out / f"onset_labels_{sfx}.csv", labels)
    summ = {"split": a.split, "variant": variant, "feature": tb.VARIANTS[variant], "n_fires_listed": len(fids), "n_fires_processed": len(done), "errors": errs,
            "thresholds": thr, "E1": e1_cv(recs), "E2": e2_stats(labels), "made": iso(time.time())}
    (out / f"traceback_{sfx}_summary.json").write_text(json.dumps(summ, indent=1, default=str))
    print(json.dumps({k: summ[k] for k in ("n_fires_processed", "thresholds", "E1", "E2")}, indent=1, default=str))
    return 0


def replay_main(a):
    from .fit import replay_cmd
    return replay_cmd(a)

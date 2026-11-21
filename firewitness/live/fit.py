"""Part B fit on dev fires and the causal replay tables (protocol §6, amendment 3).

Thresholds come only from placebo series at the budget (no fire outcome enters them). Candidate settings and
features are kept by forward selection only if they raise the replay score; the selection is cross-validated over
dev fires (5 folds by fire) so the reported dev score is held-out. The sealed test is replayed once, by
`replay --split test --i-am-opening-the-sealed-test`, with the frozen detector file.
"""
from __future__ import annotations

import hashlib
import json
import math
import pickle
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from . import detector as dt
from .extract import load_fires
from .traceback import DERIVED, FirmsClean, series_meta

CACHE = DERIVED / "fit_cache"
BUDGET = 1e-4
CURVE = [1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2]


def cfg_hash(cfg: dt.Config) -> str:
    d = cfg.to_json()
    if d.get("site_r", 1) == 1:
        d.pop("site_r", None)          # keep the hashes of caches made before site_r existed
    if not d.get("recur"):
        d.pop("recur", None)
    if not d.get("cal"):
        d.pop("cal", None)
    return hashlib.sha1(json.dumps(d, sort_keys=True).encode()).hexdigest()[:12]


def fire_cached(fid, cfg, firms):
    p = CACHE / cfg_hash(cfg) / f"{fid}.pkl"
    if p.is_file():
        try:
            return pickle.loads(p.read_bytes())
        except Exception:  # noqa: BLE001
            p.unlink(missing_ok=True)
    e = dt.fire_eval(fid, cfg, firms, need_placebo=False)
    if e is None:
        return None
    days, sd = dt.placebo_episodes(fid, cfg, firms)
    e["placebo_days"] = days
    e["site_days"] = sd
    e["placebo_runmax"] = np.concatenate([d[3] for d in days]) if days else np.zeros(0, np.float32)
    p.parent.mkdir(parents=True, exist_ok=True)
    from .goes import atomic_write_bytes
    atomic_write_bytes(p, pickle.dumps(e))
    return e


def _work(args):
    fid, cfgd = args
    cfg = dt.Config.from_json(cfgd)
    try:
        fire_cached(fid, cfg, _work.firms)
        return fid, None
    except Exception as ex:  # noqa: BLE001
        return fid, repr(ex)


def evals_for(fids, cfg, firms, procs=3):
    todo = [f for f in fids if not (CACHE / cfg_hash(cfg) / f"{f}.pkl").is_file()]
    if todo:
        from multiprocessing import get_context
        _work.firms = firms
        with get_context("fork").Pool(procs) as pool:
            errs = [r for r in pool.imap_unordered(_work, [(f, cfg.to_json()) for f in todo]) if r[1]]
        for e in errs:
            print("eval error", e, flush=True)
    return [e for e in (fire_cached(f, cfg, firms) for f in fids) if e is not None]


def clustered_rate(evals, h):
    n = 0
    for e in evals:
        for d in e["placebo_days"]:
            if (d[3] >= h).any():
                n += dt.count_clusters(*d, h)
    sd = sum(e["site_days"] for e in evals)
    return n / sd, n, sd


def unclustered_rate(evals, h):
    n = sum(int((e["placebo_runmax"] >= h).sum()) for e in evals)
    sd = sum(e["site_days"] for e in evals)
    return n / sd, n, sd


def h_for_budget(evals, budget=BUDGET, clustered=True):
    """Smallest h whose placebo false-alert rate is <= budget (bisection on the sorted episode maxima)."""
    rate = clustered_rate if clustered else unclustered_rate
    vals = np.unique(np.concatenate([e["placebo_runmax"] for e in evals] + [np.zeros(1, np.float32)]))
    lo, hi = 0, len(vals) - 1
    if rate(evals, vals[hi] + 1e-3)[0] > budget:
        return float(vals[hi]) + 1e-3
    while lo < hi:
        mid = (lo + hi) // 2
        if rate(evals, vals[mid] + 1e-3)[0] <= budget:
            hi = mid
        else:
            lo = mid + 1
    return float(vals[lo]) + 1e-3


def leads(evals, h):
    return {e["fid"]: dt.lead(e, h) for e in evals}


def score(evals, h, fids=None):
    L = leads(evals, h)
    return dt.clipped_mean([L[f] for f in (fids or L)])


# ---------------------------------------------------------------- candidates and forward selection
def candidates(cur: dt.Config, k_label: float):
    """One-step changes from the current settings (protocol §6 candidates)."""
    out = []
    for u in ("dT", "dT_c4", "dTd", "dTd_c4", "bt7_c4"):
        if u != cur.ukey:
            out.append(("feature " + u, replace(cur, ukey=u)))
    for c in (4.0, 8.0, 20.0, 40.0):
        if c != cur.cap:
            out.append((f"cap {c:g}", replace(cur, cap=c)))
    for k in sorted({0.5, 1.0, 2.0, 4.0, round(k_label, 2)}):
        if k != cur.k:
            out.append((f"k {k:g}", replace(cur, k=k)))
    for r in (1.0, 1.5, 2.0, math.inf):
        if r != cur.rho:
            out.append((f"rho {r:g}", replace(cur, rho=r)))
    for w in (0.0, 0.5):
        if w != cur.vis_weight:
            out.append((f"visible weight {w:g}", replace(cur, vis_weight=w)))
    for dcy in (1.0, 0.9):
        if dcy != cur.decay:
            out.append((f"cloud decay {dcy:g}", replace(cur, decay=dcy)))
    return out


class Evaluator:
    def __init__(self, fids, firms, budget=BUDGET, log=print):
        self.fids, self.firms, self.budget, self.log = fids, firms, budget, log
        self.memo = {}

    def get(self, cfg):
        k = cfg_hash(cfg)
        if k not in self.memo:
            t = time.time()
            ev = evals_for(self.fids, cfg, self.firms)
            h = h_for_budget(ev, self.budget)
            self.memo[k] = (ev, h)
            self.log(f"  evaluated {k} {cfg.to_json()} h={h:.1f} ({time.time() - t:.0f}s)")
        return self.memo[k]

    def score(self, cfg, fids):
        ev, h = self.get(cfg)
        evd = {e["fid"]: e for e in ev}
        return dt.clipped_mean([dt.lead(evd[f], h) for f in fids if f in evd])


def forward_select(E: Evaluator, base: dt.Config, fids, k_label, max_steps=6, log=print):
    cur = base
    best = E.score(cur, fids)
    steps = [{"step": 0, "config": cur.to_json(), "score": best, "change": "base"}]
    for s in range(1, max_steps + 1):
        trial = [(name, c, E.score(c, fids)) for name, c in candidates(cur, k_label)]
        name, c, sc = max(trial, key=lambda x: x[2])
        log(f" step {s}: best change {name} score {sc:.2f} (current {best:.2f})")
        if not sc > best + 1e-9:
            break
        cur, best = c, sc
        steps.append({"step": s, "config": cur.to_json(), "score": best, "change": name,
                      "all": [(n, round(v, 2)) for n, _, v in trial]})
    return cur, best, steps


def cross_validate(E: Evaluator, base, fids, k_label, folds=5, seed=51, log=print):
    rng = np.random.default_rng(seed)
    perm = [fids[i] for i in rng.permutation(len(fids))]
    fold = {f: i % folds for i, f in enumerate(perm)}
    held = {}
    chosen = []
    for k in range(folds):
        tr = [f for f in fids if fold[f] != k]
        te = [f for f in fids if fold[f] == k]
        cfg, sc, _ = forward_select(E, base, tr, k_label, log=log)
        ev, h = E.get(cfg)
        evd = {e["fid"]: e for e in ev}
        for f in te:
            if f in evd:
                held[f] = dt.lead(evd[f], h)
        chosen.append({"fold": k, "config": cfg.to_json(), "train_score": sc,
                       "held_score": dt.clipped_mean([held[f] for f in te if f in held])})
    return held, chosen


# ---------------------------------------------------------------- reporting
def paired_stats(leadmap, seed=0):
    from .pipeline import boot_median, wilson
    L = [v for v in leadmap.values() if v is not None]
    n = len(L)
    earlier = sum(1 for v in L if v > 0)
    med = boot_median([max(min(v, 1e6), -1e6) for v in L], seed=seed)
    return {"n": n, "earlier": earlier, "share_earlier": wilson(earlier, n), "median_lead_min": med,
            "no_alert": sum(1 for v in L if v == -math.inf), "no_operational": sum(1 for v in L if v == math.inf),
            "D1_pass": bool(n and med[1] > 0)}


def curve(evals, fids=None, h_source=None):
    """Lead statistics over budgets. Thresholds come from h_source's placebo series (dev) when given."""
    rows = []
    for b in CURVE:
        h = h_for_budget(h_source if h_source is not None else evals, b)
        L = leads(evals, h)
        if fids:
            L = {f: L[f] for f in fids if f in L}
        st = paired_stats(L)
        rc, nc, sd = clustered_rate(evals, h)
        ru, nu, _ = unclustered_rate(evals, h)
        rows.append({"budget": b, "h": round(h, 2), "false_clustered_per_site_day": rc, "n_false_clustered": nc,
                     "false_per_pixel_per_site_day": ru, "site_days": round(sd, 1), "n": st["n"],
                     "share_earlier": round(st["share_earlier"][0], 3), "median_lead_min": st["median_lead_min"][0],
                     "median_lo": st["median_lead_min"][1], "median_hi": st["median_lead_min"][2]})
    return rows


def k_from_labels(labels_csv: Path):
    """k = half the median mean-u over [t_D, T0) on dev fires with an onset (protocol §6)."""
    import csv
    from .traceback import load_records
    rows = list(csv.DictReader(open(labels_csv)))
    vals = []
    for r in rows:
        if r.get("onset") != "True":
            continue
        for rec in load_records([r["fire_id"]]):
            if rec["sat"] != r["sat"]:
                continue
            u = np.array(rec["u_site"], float)
            ts = np.array(rec["tscan0"], float)
            from datetime import datetime
            tD = datetime.fromisoformat(r["t_D"].replace("Z", "+00:00")).timestamp()
            sel = (ts >= tD - 1) & (ts < rec["T0"]) & np.isfinite(u)
            if sel.sum():
                vals.append(float(np.mean(np.minimum(u[sel], 8))))
    return (0.5 * float(np.median(vals)) if vals else 0.5), len(vals)


def by_class(L, fires):
    out = {}
    for k in sorted({int(f["size_class"]) for f in fires.values()}):
        sub = {f: v for f, v in L.items() if int(fires[f]["size_class"]) == k}
        st = paired_stats(sub)
        out[str(k)] = {"n": st["n"], "earlier": st["earlier"], "share_earlier": st["share_earlier"],
                       "median_lead_min": st["median_lead_min"], "no_alert": st["no_alert"]}
    return out


def replay_cmd(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fires = {f["fire_id"]: f for f in load_fires("protocol/live_fires.csv")}
    if a.split == "test" and not a.open_test:
        print("refusing: the sealed test is opened once, with --i-am-opening-the-sealed-test")
        return 2
    fids = [f for f, r in fires.items() if r["split"] == a.split and series_meta(f) is not None]
    dev = [f for f, r in fires.items() if r["split"] == "dev" and series_meta(f) is not None]
    det_file = Path(a.detector) if a.detector else Path(__file__).parent / "config" / "detector_us.json"
    doc = json.loads(det_file.read_text())
    cfg = dt.Config.from_json(doc["config"])
    firms = FirmsClean()
    ev = evals_for(fids, cfg, firms)
    ev_dev = evals_for(dev, cfg, firms)
    h = float(doc["h"])                     # frozen: from dev placebo series at the budget
    L = leads(ev, h)
    st = paired_stats(L)
    res = {"split": a.split, "detector_file": str(det_file), "detector_sha256": hashlib.sha256(det_file.read_bytes()).hexdigest(),
           "h": h, "budget": BUDGET, "n_fires": len(fids), "stats": st, "by_size_class": by_class(L, fires),
           "curve_thresholds_from_dev": curve(ev, h_source=ev_dev),
           "false_rate_at_h_this_split_clustered": clustered_rate(ev, h),
           "false_rate_at_h_this_split_per_pixel": unclustered_rate(ev, h),
           "made": _iso(__import__("time").time())}
    (out / f"replay_{a.split}.json").write_text(json.dumps(res, indent=1, default=str))
    rows = []
    for e in ev:
        i = e["info"]
        al = dt.alert_time(e, h)
        v = L[e["fid"]]
        rows.append({"fire_id": e["fid"], "size_class": fires[e["fid"]]["size_class"], "acres": fires[e["fid"]]["acres"],
                     "alert_utc": _iso(al), "operational_utc": _iso(i["op"]),
                     "lead_min": None if v is None else (round(v, 1) if math.isfinite(v) else ("+inf" if v > 0 else "-inf")),
                     "T0": _iso(i["T0"]), "polar_first": _iso(i["polar_first_t"]), "discovery": _iso(i["discovery_t"])})
    from .pipeline import write_csv
    write_csv(out / f"replay_{a.split}_by_fire.csv", rows)
    print(json.dumps({k: res[k] for k in ("h", "stats", "by_size_class")}, indent=1, default=str))
    return 0


def _iso(t):
    from .pipeline import iso
    return iso(t)


def fit_dev(out: Path, labels_csv: Path, variant_note: str = "", budget=BUDGET, freeze=False, rounds_note=None):
    """Fit Part B on dev: k from Part A labels, cross-validated forward selection, final selection on all dev,
    curve and paired stats from held-out leads. Writes fit_dev.json; with freeze=True writes config/detector_us.json."""
    out.mkdir(parents=True, exist_ok=True)
    fires = load_fires("protocol/live_fires.csv")
    fids = [f["fire_id"] for f in fires if f["split"] == "dev" and series_meta(f["fire_id"]) is not None]
    firms = FirmsClean()
    k_label, n_k = k_from_labels(labels_csv)
    log_lines = []

    def log(x):
        print(x, flush=True)
        log_lines.append(x)
    E = Evaluator(fids, firms, budget, log=log)
    base = dt.Config(ukey="dT", cap=8.0, k=round(k_label, 2), rho=1.5, m=1.0)
    held, chosen = cross_validate(E, base, fids, k_label, log=log)
    final, final_score, steps = forward_select(E, base, fids, k_label, log=log)
    ev, h = E.get(final)
    res = {"n_dev_fires": len(fids), "k_label": k_label, "n_k_label": n_k, "budget": budget, "base": base.to_json(),
           "cv_folds": chosen, "cv_held_out_score": dt.clipped_mean(list(held.values())),
           "cv_held_out_stats": paired_stats(held), "final_config": final.to_json(), "final_h": h,
           "final_dev_score_in_sample": final_score, "selection_steps": steps,
           "final_dev_stats_in_sample": paired_stats(leads(ev, h)), "curve_dev": curve(ev),
           "false_rate_at_h": clustered_rate(ev, h), "unclustered_rate_at_h": unclustered_rate(ev, h),
           "log": log_lines, "variant_note": variant_note}
    (out / "fit_dev.json").write_text(json.dumps(res, indent=1, default=str))
    if freeze:
        doc = {"frozen": True, "note": rounds_note or "Frozen Part B settings fitted on dev fires (results/live/fit_dev.json).",
               "config": final.to_json(), "h": h, "budget_per_pixel_site_day": budget,
               "fitted_on": "dev fires and dev placebo series", "n_dev_fires": len(fids)}
        (Path(__file__).parent / "config" / "detector_us.json").write_text(json.dumps(doc, indent=1))
    return res

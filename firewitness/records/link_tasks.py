"""The three published links of gate R1, re-derived with the published link fields hidden."""
from __future__ import annotations

import ast
import re
import json
import time

import numpy as np
import pandas as pd

from ..core import load_region
from . import link as L, paths


def _cfg():
    return load_region(paths.REPO / "firewitness" / "records", "us")


def split_of(year: pd.Series, cfg) -> pd.Series:
    t = set(cfg["split"]["test_years"]); h = cfg["split"]["heldout_year"]
    return year.map(lambda y: "test" if y in t else "heldout" if y == h else "dev")


def parse_list(x) -> list:
    if not isinstance(x, str) or not x.strip():
        return []
    try:
        v = ast.literal_eval(x)
        return list(v) if isinstance(v, (list, tuple)) else [v]
    except Exception:
        return re.findall(r"[\w-]+", x)


def load_tables():
    C = paths.CANON
    return pd.read_parquet(C / "fod.parquet"), pd.read_parquet(C / "mtbs.parquet"), pd.read_parquet(C / "ics_inc.parquet")


# ------------------------------------------------------------------ task definitions
SETTINGS = {"mtbs_radius_mult": 4.0, "mtbs_radius_floor": 10.0, "ics_radius_mult": 3.0, "ics_radius_floor": 10.0, "hi": 0.95, "margin": 0.25}
# decision thresholds per task, chosen on dev years only (see results/ROUNDS_records.md)
TASK_DECISION = {"fod_mtbs": {"hi": 0.7, "margin": 0.1}, "fod_ics": {"hi": 0.8, "margin": 0.1}, "ics_fired": {"hi": 0.5, "margin": 0.0}}


def _dec(name):
    return TASK_DECISION.get(name, {"hi": SETTINGS["hi"], "margin": SETTINGS["margin"]})


def task_fod_mtbs(fod, mtbs, ics, cfg):
    left = fod.reset_index(drop=True)
    right = mtbs.reset_index(drop=True)
    rad = SETTINGS["mtbs_radius_floor"] + SETTINGS["mtbs_radius_mult"] * np.sqrt(np.nan_to_num(right.acres.to_numpy(), nan=100.0) * 0.00405 / np.pi)
    truth = set(zip(left.fid[left.pub_mtbs.isin(set(right.mid))], left.pub_mtbs[left.pub_mtbs.isin(set(right.mid))]))
    return dict(name="fod_mtbs", left=left, right=right, radius=rad, day_window=30, lid="fid", rid="mid", truth=truth,
                left_year="year", left_state="state", fields=L.FIELDS, side="left")


def task_fod_ics(fod, mtbs, ics, cfg):
    left = fod.reset_index(drop=True)
    right = ics.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    rad = SETTINGS["ics_radius_floor"] + SETTINGS["ics_radius_mult"] * np.sqrt(np.nan_to_num(right.acres.to_numpy(), nan=100.0) * 0.00405 / np.pi)
    ids = set(right.iid)
    t1 = set(zip(left.fid[left.pub_ics.isin(ids)], left.pub_ics[left.pub_ics.isin(ids)]))
    t2 = set()
    for iid, lst in zip(right.iid, right.pub_fod_list):
        for f in parse_list(lst):
            try:
                t2.add((int(f), iid))
            except (TypeError, ValueError):
                pass
    return dict(name="fod_ics", left=left, right=right, radius=rad, day_window=30, lid="fid", rid="iid", truth=t1 | t2,
                left_year="year", left_state="state", fields=L.FIELDS, side="left")


def task_ics_fired(fod, mtbs, ics, cfg):
    """FIRED events are known here only through the attributes joined into ICS-209-PLUS (the FIRED download was
    blocked), so candidate events are those carried by some incident: a restricted pool, reported as such."""
    left = ics.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    pool = ics.dropna(subset=["pub_fired", "fired_lat", "fired_lon"]).drop_duplicates("pub_fired")
    right = pd.DataFrame({"fid_": pool.pub_fired.astype(int).astype(str), "lat": pool.fired_lat.to_numpy(), "lon": pool.fired_lon.to_numpy(),
                          "acres": pool.fired_acres.to_numpy(), "day": np.nan, "name": None, "state": None}).reset_index(drop=True)
    truth = set(zip(left.iid[left.pub_fired.notna()], left.pub_fired[left.pub_fired.notna()].astype(int).astype(str)))
    return dict(name="ics_fired", left=left, right=right, radius=25.0, day_window=None, lid="iid", rid="fid_", truth=truth,
                left_year="year", left_state="state", fields=["rdist", "dist", "size"], side="left")


TASKS = {"fod_mtbs": task_fod_mtbs, "fod_ics": task_fod_ics, "ics_fired": task_ics_fired}


# ------------------------------------------------------------------ run
def _f1(tp, npred, ntruth):
    p = tp / max(npred, 1); r = tp / max(ntruth, 1)
    return 2 * p * r / (p + r) if p + r else 0.0


def run_task(name: str, split: str = "dev", model=None, rule=None, n_boot=1000, seed=0, verbose=True):
    cfg = _cfg()
    fod, mtbs, ics = load_tables()
    T = TASKS[name](fod, mtbs, ics, cfg)
    left, right = T["left"], T["right"]
    t0 = time.time()
    log = (lambda *a: print(f"[{name} {time.time()-t0:5.0f}s]", *a, flush=True)) if verbose else (lambda *a: None)
    pairs = L.candidate_pairs(left, right, T["radius"], T["day_window"])
    log("pairs", len(pairs))
    NR = len(right)
    lpos = {k: i for i, k in enumerate(left[T["lid"]].to_numpy())}
    rpos = {k: i for i, k in enumerate(right[T["rid"]].to_numpy())}
    tcode = np.array(sorted({lpos[a] * NR + rpos[b] for a, b in T["truth"] if a in lpos and b in rpos}), dtype=np.int64)
    lsplit = split_of(left[T["left_year"]], cfg).to_numpy()
    in_dev = lsplit == "dev"
    in_sel = lsplit == split
    X = L.compare(left, right, pairs, T["fields"])
    log("compared")
    pdev = in_dev[pairs.li.to_numpy()]
    if model is None:
        model = L.fit_fs(X[pdev], T["fields"])
    log("fit prior", round(model.prior, 4), "iters", model.iters)
    dec = L.decide(pairs, model.posterior(X), **_dec(name), side=T["side"])
    code = lambda d: d.li.to_numpy().astype(np.int64) * NR + d.ri.to_numpy()
    truth_sel = tcode[in_sel[tcode // NR]]
    truth_dev = tcode[in_dev[tcode // NR]]
    ours_code = code(dec[(dec.outcome == "link")])
    ours_code = ours_code[in_sel[ours_code // NR]]
    res = {"task": name, "split": split, "n_pairs": int(len(pairs)), "n_truth": int(len(truth_sel)), "prior": float(model.prior)}
    res["ours"] = L.prf(set(ours_code.tolist()), set(truth_sel.tolist()))
    res["undecided"] = int((dec.outcome == "undecided").sum())
    # best fixed rule: chosen on dev only
    best = rule
    cache = {}
    for dl in range(5):
        for tl in (range(5) if "day" in T["fields"] else [4]):
            r = L.fixed_rule(pairs[pdev], X[pdev], T["fields"], dl, tl)
            c = code(r)
            cache[(dl, tl)] = c
            tp = np.isin(c, truth_dev).sum()
            f = _f1(tp, len(c), len(truth_dev))
            if best is None or (rule is None and f > best[0]):
                best = (f, dl, tl)
    rr = L.fixed_rule(pairs, X, T["fields"], best[1], best[2])
    base_code = code(rr)
    base_code = base_code[in_sel[base_code // NR]]
    res["fixed_rule"] = {"dist_level": int(best[1]), "day_level": int(best[2]), "dev_f1": float(best[0])} | L.prf(set(base_code.tolist()), set(truth_sel.tolist()))
    log("scored", res["ours"], res["fixed_rule"])
    # bootstrap resampling whole state-years of the left record
    lkey = (left[T["left_state"]].astype(str) + "|" + left[T["left_year"]].astype(str)).to_numpy().astype(str)
    codes, inv = np.unique(lkey, return_inverse=True)
    def per_cluster(c):
        return np.bincount(inv[c // NR], minlength=len(codes)).astype(float)
    nt, no, nb = per_cluster(truth_sel), per_cluster(ours_code), per_cluster(base_code)
    to, tb = per_cluster(ours_code[np.isin(ours_code, truth_sel)]), per_cluster(base_code[np.isin(base_code, truth_sel)])
    use = np.flatnonzero((nt + no + nb) > 0)
    rng = np.random.default_rng(seed)
    d, fo = [], []
    for _ in range(n_boot):
        sidx = use[rng.integers(0, len(use), len(use))]
        a = _f1(to[sidx].sum(), no[sidx].sum(), nt[sidx].sum()); b = _f1(tb[sidx].sum(), nb[sidx].sum(), nt[sidx].sum())
        d.append(a - b); fo.append(a)
    res["bootstrap"] = {"n_clusters": int(len(use)), "f1_diff": float(_f1(to.sum(), no.sum(), nt.sum()) - _f1(tb.sum(), nb.sum(), nt.sum())),
                        "f1_diff_lo": float(np.percentile(d, 2.5)), "f1_diff_hi": float(np.percentile(d, 97.5)),
                        "f1_ours_lo": float(np.percentile(fo, 2.5)), "f1_ours_hi": float(np.percentile(fo, 97.5))}
    res["seconds"] = round(time.time() - t0, 1)
    return res, model, (pairs, X, dec)


if __name__ == "__main__":
    import sys
    for n in (sys.argv[1:] or list(TASKS)):
        r, m, _ = run_task(n)
        print(json.dumps(r, indent=1, default=float))


def decide_all(name: str, model=None):
    """Fit on dev years only (frozen model), decide every candidate pair of every year. Returns T, pairs, X, dec, model."""
    cfg = _cfg()
    fod, mtbs, ics = load_tables()
    T = TASKS[name](fod, mtbs, ics, cfg)
    left, right = T["left"], T["right"]
    pairs = L.candidate_pairs(left, right, T["radius"], T["day_window"])
    X = L.compare(left, right, pairs, T["fields"])
    dev = (split_of(left[T["left_year"]], cfg).to_numpy() == "dev")[pairs.li.to_numpy()]
    if model is None:
        model = L.fit_fs(X[dev], T["fields"])
    dec = L.decide(pairs, model.posterior(X), **_dec(name), side=T["side"])
    return T, pairs, X, dec, model


def model_to_json(model) -> dict:
    return {"fields": model.fields, "prior": model.prior, "m": [list(map(float, a)) for a in model.m], "u": [list(map(float, a)) for a in model.u]}


def model_from_json(d) -> L.FSModel:
    return L.FSModel(d["fields"], [np.array(a) for a in d["m"]], [np.array(a) for a in d["u"]], d["prior"])

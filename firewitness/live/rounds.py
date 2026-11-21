"""Improvement loop (protocol §9): one named cause, one change, replay on dev at the same budget, keep if better."""
from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import detector as dt
from . import fit
from .extract import load_fires
from .traceback import FirmsClean, series_meta

ROUNDS_JSON = Path("results/live/rounds.json")
ROUNDS_MD = Path("results/ROUNDS_live.md")


def dev_fids():
    return [f["fire_id"] for f in load_fires("protocol/live_fires.csv")
            if f["split"] == "dev" and series_meta(f["fire_id"]) is not None]


def evaluate(cfg, fids, firms, budget=fit.BUDGET):
    ev = fit.evals_for(fids, cfg, firms)
    h = fit.h_for_budget(ev, budget)
    L = fit.leads(ev, h)
    st = fit.paired_stats(L)
    rate = fit.clustered_rate(ev, h)
    return {"h": h, "score": dt.clipped_mean(list(L.values())), "earlier": st["earlier"], "n": st["n"],
            "no_alert": st["no_alert"], "median": st["median_lead_min"], "false_rate": rate[0],
            "n_false": rate[1], "site_days": rate[2], "leads": L, "ev": ev}


def false_alert_summary(ev, h):
    """The clustered placebo false alerts at h: when (UTC hour), which day kind, how big."""
    hours, kinds, sizes = Counter(), Counter(), []
    for e in ev:
        for d_i, d in enumerate(e["placebo_days"]):
            sel = d[3] >= h
            if not sel.any():
                continue
            sizes.append(int(sel.sum()))
            kinds["day0 (fire day, far sites)" if d_i == 0 else "previous days"] += 1
    return {"n_days_with_false": sum(kinds.values()), "kinds": dict(kinds),
            "sites_per_day_median": float(np.median(sizes)) if sizes else 0}


def run_round(n, cause, change, cur, cand, fids, firms, log):
    a = log.get("_cache", {}).get(fit.cfg_hash(cur)) or evaluate(cur, fids, firms)
    b = evaluate(cand, fids, firms)
    keep = b["score"] > a["score"] + 1e-9
    row = {"round": n, "cause": cause, "change": change, "before": cur.to_json(), "after": cand.to_json(),
           "score_before": a["score"], "score_after": b["score"], "h_before": a["h"], "h_after": b["h"],
           "earlier_before": a["earlier"], "earlier_after": b["earlier"], "n": b["n"],
           "no_alert_before": a["no_alert"], "no_alert_after": b["no_alert"],
           "false_rate_after": b["false_rate"], "kept": keep,
           "false_alerts_after": false_alert_summary(b["ev"], b["h"]),
           "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    log.setdefault("_cache", {})[fit.cfg_hash(cur)] = a
    log.setdefault("_cache", {})[fit.cfg_hash(cand)] = b
    return row, (cand if keep else cur)


def write_logs(rows, final):
    ROUNDS_JSON.parent.mkdir(parents=True, exist_ok=True)
    ROUNDS_JSON.write_text(json.dumps({"rounds": rows, "final_config": final.to_json()}, indent=1, default=str))
    lines = ROUNDS_MD.read_text().split("\n") if ROUNDS_MD.is_file() else []
    head = [l for l in lines if not l.startswith("| R")]
    body = []
    for r in rows:
        body.append(f"| R{r['round']} | {r['cause']} | {r['change']} | {r['score_before']:.1f} → {r['score_after']:.1f} "
                    f"(earlier {r['earlier_before']} → {r['earlier_after']} of {r['n']}; no alert {r['no_alert_before']} → "
                    f"{r['no_alert_after']}; h {r['h_before']:.0f} → {r['h_after']:.0f}) | {r['false_rate_after']:.2e} | "
                    f"{'yes' if r['kept'] else 'no'} |")
    ROUNDS_MD.write_text("\n".join([l for l in head if l.strip() or True]).rstrip("\n") + "\n" + "\n".join(body) + "\n")


def main(plan, start: dt.Config, rows=None):
    firms = FirmsClean()
    fids = dev_fids()
    cur = start
    rows = rows or []
    log = {}
    for i, (cause, change, fn) in enumerate(plan, start=len(rows) + 1):
        cand = fn(cur)
        row, cur = run_round(i, cause, change, cur, cand, fids, firms, log)
        rows.append(row)
        write_logs(rows, cur)
        print(f"R{i}: {change}: {row['score_before']:.1f} -> {row['score_after']:.1f} kept={row['kept']}", flush=True)
    return cur, rows


def with_flag(cfg, flag):
    parts = cfg.ukey.split("_")
    key = flag.rstrip("0123456789")
    parts = [p for p in parts if not (p.rstrip("0123456789") == key and p != parts[0])]
    return replace(cfg, ukey="_".join(parts + [flag]))

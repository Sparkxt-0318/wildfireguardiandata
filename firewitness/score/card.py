"""The score card. Threshold fixed on validation, scored on test, with persistence and climatology beside the model."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from . import contract as ct
from .dataset import FIRE, NO_FIRE, UNKNOWN, Dataset
from .features import danger_at
from .leak import leak_report
from .ops import dilate_space, dilate_time, to_calendar
from .predictions import Predictions
from .strata import N_DANGER, hard_mask

COUNT_KEYS = ("n_pred", "tp_pred", "n_fire", "tp_fire")


class SceneCtx:
    """Per-scene arrays reused across thresholds and tolerances."""

    def __init__(self, scene, contract):
        self.s = scene
        s = scene
        self.tgt = np.zeros(len(s.dates), bool)
        self.tgt[s.valid_targets()] = True
        self.known = s.state != UNKNOWN
        self.F = s.state == FIRE
        self.Ft = self.F & self.tgt[:, None, None]
        self.Fcal, self.idx, self.d0 = to_calendar(s.dates, self.F)
        self._dil = {}
        self._hard = None
        self.horizon = contract["horizon_days"]

    def dil_fire(self, r, tau):
        k = (r, tau)
        if k not in self._dil:
            self._dil[k] = dilate_time(dilate_space(self.Fcal, r), tau)
        return self._dil[k]

    def hard(self, hard_km):
        if self._hard is None:
            h = np.zeros(self.s.state.shape, bool)
            for t in self.s.valid_targets():
                h[t] = hard_mask(self.s, int(t), hard_km=hard_km) & (self.s.state[t] == NO_FIRE)
            self._hard = h
        return self._hard


def flagged(ctx: SceneCtx, score, thr):
    with np.errstate(invalid="ignore"):
        raw = score >= thr
    raw &= ctx.tgt[:, None, None]
    return raw & ctx.known, int((raw & ~ctx.known).sum())


def match_counts(ctx: SceneCtx, P, r: int, tau: int) -> dict:
    Pcal, _, _ = to_calendar(ctx.s.dates, P)
    DF = ctx.dil_fire(r, tau)[ctx.idx]
    tp_pred = int((P & DF).sum())
    DP = dilate_time(dilate_space(Pcal, r), tau)[ctx.idx]
    tp_fire = int((ctx.Ft & DP).sum())
    return {"n_pred": int(P.sum()), "tp_pred": tp_pred, "n_fire": int(ctx.Ft.sum()), "tp_fire": tp_fire}


def event_stats(ctx: SceneCtx, P, r: int, tau: int, ev: dict, horizon: int) -> list:
    """Events = (fire, day) with >= min_new_cells newly burning cells (not within new_radius of the previous day's fire).
    Returns [(detected, lead_days or None)]."""
    s = ctx.s
    Pcal, _, d0 = to_calendar(s.dates, P)
    out = []
    for t in s.valid_targets():
        new = ctx.F[t] & ~dilate_space(ctx.F[t - 1], ev["new_radius_cells"])
        if new.sum() < ev["min_new_cells"]:
            continue
        d = int(s.dates[t]) - d0
        lead = None
        for delta in range(tau, -tau - 1, -1):
            day = d - delta
            if 0 <= day < len(Pcal) and (dilate_space(Pcal[day], r) & new).any():
                lead = delta + horizon
                break
        out.append((lead is not None, lead))
    return out


def per_fire_eval(ds: Dataset, fires, getter, thr, c: dict, ctxs: dict, with_events=True) -> dict:
    """Counts per fire for every tolerance and reading, plus hard-negative and event stats."""
    res = {}
    for fid in fires:
        ctx = ctxs[fid]
        P, dropped = flagged(ctx, getter(fid), thr)
        rec = {"tol": {}, "dropped_on_unknown": dropped, "n_pred": int(P.sum())}
        slack = ctx.s.interval_slack
        for name, tol in sorted(c["tolerances"].items()):
            rec["tol"][name] = {}
            for reading in c["label_readings"]:
                tau = tol["time_days"] + (slack if reading == "interval" else 0)
                rec["tol"][name][reading] = match_counts(ctx, P, tol["space_cells"], tau)
        h = ctx.hard(c.get("hard", {}).get("hard_km", 10.0))
        rec["hard_pred"] = int((P & h).sum())
        rec["hard_n"] = int(h.sum())
        if with_events:
            etol = c["tolerances"][c["event"].get("tolerance", "mid")]
            rec["events"] = event_stats(ctx, P, etol["space_cells"], etol["time_days"], c["event"], c["horizon_days"])
        res[fid] = rec
    return res


def _f1(tp_p, n_p, tp_f, n_f):
    p = tp_p / n_p if n_p else 0.0
    r = tp_f / n_f if n_f else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def pooled(res: dict, tol: str, reading: str) -> dict:
    t = {k: 0 for k in COUNT_KEYS}
    for fid in sorted(res):
        for k in COUNT_KEYS:
            t[k] += res[fid]["tol"][tol][reading][k]
    p, r, f1 = _f1(t["tp_pred"], t["n_pred"], t["tp_fire"], t["n_fire"])
    return {**t, "precision": round(p, 6), "recall": round(r, 6), "f1": round(f1, 6)}


def candidate_thresholds(values: np.ndarray) -> list:
    u = np.unique(values[np.isfinite(values)])
    if len(u) == 0:
        return [0.5]
    if len(u) <= 12:
        return [float(x) for x in u]
    qs = [0.5, 0.8, 0.9, 0.95, 0.98, 0.99, 0.995, 0.998, 0.999, 0.9995, 0.9998, 0.9999]
    return sorted({float(np.quantile(values, q)) for q in qs})


def choose_threshold(ds, val_fires, getter, c: dict, ctxs: dict) -> float:
    th = c["threshold"]
    if th["rule"] == "fixed":
        return float(th["value"])
    tol = c["tolerances"][th.get("tolerance", "strict")]
    vals = []
    for fid in val_fires:
        sc = getter(fid)[ctxs[fid].tgt]
        v = sc[np.isfinite(sc)]
        vals.append(v[:: max(1, len(v) // 400000)])
    allv = np.concatenate(vals) if vals else np.zeros(0)
    best, bt = -1.0, None
    cands = candidate_thresholds(allv)
    for thr in sorted(cands):
        tot = {k: 0 for k in COUNT_KEYS}
        for fid in val_fires:
            ctx = ctxs[fid]
            P, _ = flagged(ctx, getter(fid), thr)
            m = match_counts(ctx, P, tol["space_cells"], tol["time_days"])
            for k in COUNT_KEYS:
                tot[k] += m[k]
        f1 = _f1(tot["tp_pred"], tot["n_pred"], tot["tp_fire"], tot["n_fire"])[2]
        if f1 >= best:      # ties go to the higher threshold (fewer flags)
            best, bt = f1, thr
    return float(bt) if bt is not None else 0.5


def bootstrap_diff(resA: dict, resB: dict, tol: str, reading: str, n: int, seed: int) -> dict:
    fires = sorted(resA)
    A = np.array([[resA[f]["tol"][tol][reading][k] for k in COUNT_KEYS] for f in fires], np.float64)
    B = np.array([[resB[f]["tol"][tol][reading][k] for k in COUNT_KEYS] for f in fires], np.float64)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(fires), size=(n, len(fires)))

    def f1(M):
        S = M[idx].sum(1)
        p = np.divide(S[:, 1], S[:, 0], out=np.zeros(n), where=S[:, 0] > 0)
        r = np.divide(S[:, 3], S[:, 2], out=np.zeros(n), where=S[:, 2] > 0)
        return np.divide(2 * p * r, p + r, out=np.zeros(n), where=(p + r) > 0)

    d = f1(A) - f1(B)
    a0 = _f1(A[:, 1].sum(), A[:, 0].sum(), A[:, 3].sum(), A[:, 2].sum())[2]
    b0 = _f1(B[:, 1].sum(), B[:, 0].sum(), B[:, 3].sum(), B[:, 2].sum())[2]
    lo, hi = np.quantile(d, [0.025, 0.975])
    return {"diff_f1": round(a0 - b0, 6), "ci95": [round(float(lo), 6), round(float(hi), 6)], "excludes_zero": bool(lo > 0 or hi < 0),
            "n_fires": len(fires)}


def summarise(res: dict, c: dict) -> dict:
    out = {"tolerances": {}}
    for name in sorted(c["tolerances"]):
        out["tolerances"][name] = {rd: pooled(res, name, rd) for rd in c["label_readings"]}
    n_pred = sum(res[f]["n_pred"] for f in res)
    n_fire = out["tolerances"][sorted(c["tolerances"])[0]][c["label_readings"][0]]["n_fire"]
    out["predicted_cells"] = n_pred
    out["true_fire_cells"] = n_fire
    out["area_ratio"] = round(n_pred / n_fire, 4) if n_fire else None
    hp, hn = sum(res[f]["hard_pred"] for f in res), sum(res[f]["hard_n"] for f in res)
    out["hard_negative_false_alarm_rate"] = round(hp / hn, 6) if hn else None
    out["hard_negative_cells"] = hn
    evs = [e for f in sorted(res) for e in res[f]["events"]]
    leads = sorted(l for d, l in evs if d)
    ev = {"events": len(evs), "detected": sum(1 for d, _ in evs if d)}
    ev["detection_rate"] = round(ev["detected"] / ev["events"], 6) if ev["events"] else None
    if leads:
        q = np.percentile(leads, [25, 50, 75])
        ev["lead_days_q25_median_q75"] = [float(x) for x in q]
    else:
        ev["lead_days_q25_median_q75"] = None
    out["event_level"] = ev
    out["flags_dropped_on_unknown"] = sum(res[f]["dropped_on_unknown"] for f in res)
    return out


def excluded_unknown(ds: Dataset, fires, c) -> dict:
    n_unk = n_all = n_nontarget = 0
    for fid in fires:
        s = ds.scenes[fid]
        tg = np.zeros(len(s.dates), bool)
        tg[s.valid_targets()] = True
        cells = int(np.prod(s.state.shape[1:]))
        n_all += int(tg.sum()) * cells
        n_unk += int(((s.state == UNKNOWN) & tg[:, None, None]).sum())
        n_nontarget += int((~tg).sum()) * cells
    return {"unknown_cells": n_unk, "scored_cell_days": n_all, "share_unknown": round(n_unk / n_all, 6) if n_all else None,
            "cell_days_without_issue_state": n_nontarget,
            "reason": ds.meta.get("state_rule", "adapter-defined")}


def build_card(ds: Dataset, split: dict, preds: Predictions, c: dict, model_name: str = "model", baselines: dict | None = None,
               fold: str = "test") -> dict:
    """baselines: {'persistence': Predictions, 'climatology': Predictions} (built by baselines.make if None)."""
    from .baselines import make as make_baselines
    c = ct.validate(c)
    if split.get("row_level"):
        raise ValueError("row-level random splits cannot produce a score card (gate N1 uses them only for comparison)")
    val_f, test_f = split["folds"]["val"], split["folds"][fold]
    need = list(test_f) + ([] if c["threshold"]["rule"] == "fixed" else list(val_f))
    miss = [f for f in need if f not in preds.scores]
    if miss:
        raise ValueError(f"predictions missing for fires: {miss[:5]}")
    base = baselines or make_baselines(ds, split)
    fires_all = sorted(set(val_f) | set(test_f))
    ctxs = {f: SceneCtx(ds.scenes[f], c) for f in fires_all}
    card = {"contract": c.get("name"), "contract_sha256": ct.digest(c), "split_sha256": split["sha256"],
            "split_scheme": split["scheme"], "fold": fold, "n_test_fires": len(test_f), "n_val_fires": len(val_f),
            "dataset": ds.name, "model": model_name, "predictions_sha256": preds.sha256(), "models": {}, "threshold": {}}
    allm = {model_name: preds, "persistence": base["persistence"], "climatology": base["climatology"]}
    resl = {}
    for name, p in allm.items():
        getter = lambda fid, p=p: p.scores[fid]
        thr = choose_threshold(ds, val_f, getter, c, ctxs) if not (c["threshold"]["rule"] == "fixed") else float(c["threshold"]["value"])
        res = per_fire_eval(ds, test_f, getter, thr, c, ctxs)
        resl[name] = res
        card["threshold"][name] = round(thr, 8)
        card["models"][name] = summarise(res, c)
    card["unknown_excluded"] = excluded_unknown(ds, test_f, c)
    card["lift"] = {}
    n_b, seed = c["bootstrap"]["n"], c["bootstrap"]["seed"]
    for other in ("persistence", "climatology"):
        card["lift"][f"{model_name}_minus_{other}"] = {
            tn: {rd: bootstrap_diff(resl[model_name], resl[other], tn, rd, n_b, seed) for rd in c["label_readings"]}
            for tn in sorted(c["tolerances"])}
    card["leak"] = leak_report(ds, test_f, preds, c)
    tr = preds.meta.get("trained_on_fires")
    if tr is None:
        card["training_provenance"] = {"status": "not declared", "overlap_with_test": None}
    else:
        ov = sorted(set(tr) & set(test_f))
        card["training_provenance"] = {"status": "FAIL: trained on test fires" if ov else "pass", "overlap_with_test": ov[:10]}
    warn = []
    ar = card["models"][model_name]["area_ratio"]
    if ar is not None and ar > c["area_ratio_warn"]:
        warn.append(f"OVER-PREDICTION: predicted area is {ar:.1f}x the true fire area (warn above {c['area_ratio_warn']}x)")
    if card["training_provenance"]["status"].startswith("FAIL"):
        warn.append("TRAINING PROVENANCE: " + card["training_provenance"]["status"])
    if card["leak"]["status"] != "pass":
        warn.append("LEAK CHECK: " + card["leak"]["status"])
    card["warnings"] = warn
    card["card_sha256"] = hashlib.sha256(json.dumps({k: v for k, v in card.items()}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return card


def to_json(card: dict) -> str:
    return json.dumps(card, sort_keys=True, indent=1)


def render(card: dict) -> str:
    m = card["model"]
    L = [f"# Score card: {m}", "",
         f"contract `{card['contract_sha256'][:12]}` · split `{card['split_sha256'][:12]}` ({card['split_scheme']}, fold {card['fold']}, "
         f"{card['n_test_fires']} fires; threshold from {card['n_val_fires']} validation fires) · predictions `{card['predictions_sha256'][:12]}`", ""]
    for w in card["warnings"]:
        L.append(f"**!! {w}**")
    if card["warnings"]:
        L.append("")
    names = [m, "persistence", "climatology"]
    L += ["## Precision / recall / F1 at the validation threshold", "",
          "| tolerance | reading | " + " | ".join(f"{n} P / R / F1" for n in names) + " |", "|---|---|" + "---|" * len(names)]
    tols = sorted(card["models"][m]["tolerances"])
    for tn in tols:
        for rd in sorted(card["models"][m]["tolerances"][tn]):
            row = []
            for n in names:
                x = card["models"][n]["tolerances"][tn][rd]
                row.append(f"{x['precision']:.3f} / {x['recall']:.3f} / {x['f1']:.3f}")
            L.append(f"| {tn} | {rd} | " + " | ".join(row) + " |")
    L += ["", "## Predicted area over true area; hard negatives; events", "",
          "| | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    def row(label, fn):
        return f"| {label} | " + " | ".join(fn(card["models"][n]) for n in names) + " |"
    L.append(row("threshold", lambda x: ""))  # placeholder replaced below
    L[-1] = "| threshold | " + " | ".join(str(card["threshold"][n]) for n in names) + " |"
    L.append(row("predicted / true area", lambda x: "n/a" if x["area_ratio"] is None else f"{x['area_ratio']:.2f}"))
    L.append(row("false-alarm rate on hard negatives", lambda x: "n/a" if x["hard_negative_false_alarm_rate"] is None else f"{x['hard_negative_false_alarm_rate']:.4f}"))
    L.append(row("events detected / events", lambda x: f"{x['event_level']['detected']} / {x['event_level']['events']}"))
    L.append(row("lead days q25 / median / q75", lambda x: "n/a" if not x["event_level"]["lead_days_q25_median_q75"] else " / ".join(f"{v:g}" for v in x["event_level"]["lead_days_q25_median_q75"])))
    u = card["unknown_excluded"]
    L += ["", f"Cells excluded as unknown: {u['unknown_cells']} of {u['scored_cell_days']} scored cell-days ({u['share_unknown']}). Rule: {u['reason']}", ""]
    L += ["## Lift (F1 difference, 95% cluster bootstrap over fires)", ""]
    for k, v in card["lift"].items():
        for tn in sorted(v):
            for rd in sorted(v[tn]):
                x = v[tn][rd]
                L.append(f"- {k} [{tn}/{rd}]: {x['diff_f1']:+.4f} ({x['ci95'][0]:+.4f}, {x['ci95'][1]:+.4f}){'  *' if x['excludes_zero'] else ''}")
    L += ["", "## Leak check", "", f"status: **{card['leak']['status']}** — {card['leak']['detail']}", "",
          f"training provenance: {card['training_provenance']['status']}", "",
          f"card hash `{card['card_sha256']}`"]
    return "\n".join(L) + "\n"

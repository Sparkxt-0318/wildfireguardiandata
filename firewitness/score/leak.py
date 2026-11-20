"""Leak check: declared information horizon plus a behavioural screen for implausible foresight."""
from __future__ import annotations

import numpy as np

from .dataset import FIRE, NO_FIRE
from .ops import auc, dilate_space


def leak_report(ds, fires, preds, c: dict) -> dict:
    h = c["horizon_days"]
    lk = c["leak"]
    # 1. declared provenance
    lag = preds.meta.get("info_until_lag_days")
    bad, undeclared = [], []
    for fid in fires:
        s = ds.scenes[fid]
        inf = preds.info_until.get(fid)
        tg = s.valid_targets()
        if inf is not None:
            declared = inf[tg]
            if (declared < 0).any():
                undeclared.append(fid)
            elif (declared > s.dates[tg] - h).any():
                bad.append(fid)
        elif lag is None:
            undeclared.append(fid)
        elif lag < h:
            bad.append(fid)
    if bad:
        return {"status": "FAIL: info_until later than the issue day", "detail": f"fires {bad[:5]}", "auc": None, "n_positives": None}
    if undeclared:
        return {"status": "FAIL: info_until not declared", "detail": f"fires {undeclared[:5]}", "auc": None, "n_positives": None}
    # 2. behavioural screen
    pos, neg = [], []
    for fid in fires:
        s = ds.scenes[fid]
        sc = preds.scores[fid]
        for t in s.valid_targets():
            near = dilate_space(s.state[t - 1] == FIRE, lk["radius_cells"])
            row = sc[t]
            p = (s.state[t] == FIRE) & ~near
            n = (s.state[t] == NO_FIRE) & ~near
            pos.append(row[p][np.isfinite(row[p])])
            nv = row[n]
            nv = nv[np.isfinite(nv)]
            neg.append(nv[:: max(1, len(nv) // 2000)])
    front = front_auc(ds, fires, preds, lk)
    fa = front["auc"]
    if fa is not None and fa > lk.get("front_auc", 0.95):
        return {"status": "FLAG: implausible foresight at the fire front", "detail": f"AUC {fa:.3f} on {front['n_positives']} cells newly burning within {lk['radius_cells']} cells of the previous day's fire exceeds {lk.get('front_auc', 0.95)}",
                "auc": None, "front_auc": round(fa, 4), "n_positives": int(front["n_positives"])}
    pos = np.concatenate(pos) if pos else np.zeros(0)
    neg = np.concatenate(neg) if neg else np.zeros(0)
    if len(pos) < lk["min_positives"]:
        return {"status": "pass", "detail": f"declared horizon respected; behavioural screen not run (only {len(pos)} new-ignition positives, need {lk['min_positives']})",
                "auc": None, "n_positives": int(len(pos))}
    a = auc(pos, neg)
    if a > lk["auc"]:
        return {"status": "FLAG: implausible foresight", "detail": f"AUC {a:.3f} on {len(pos)} cells with no fire within {lk['radius_cells']} cells the day before exceeds {lk['auc']}",
                "auc": round(a, 4), "n_positives": int(len(pos))}
    fa_txt = "" if front["auc"] is None else f"; front AUC {front['auc']:.3f} (limit {lk.get('front_auc', 0.95)})"
    return {"status": "pass", "detail": f"declared horizon respected; AUC {a:.3f} on {len(pos)} new-ignition cells (limit {lk['auc']}){fa_txt}. A screen, not a proof.",
            "auc": round(a, 4), "n_positives": int(len(pos))}


def front_auc(ds, fires, preds, lk) -> dict:
    """AUC on cells within radius of the previous day's fire (not burning then): new fire vs no fire."""
    pos, neg = [], []
    for fid in fires:
        s = ds.scenes[fid]
        sc = preds.scores[fid]
        for t in s.valid_targets():
            prev = s.state[t - 1] == FIRE
            ring = dilate_space(prev, lk["radius_cells"]) & ~prev
            row = sc[t]
            p = ring & (s.state[t] == FIRE)
            n = ring & (s.state[t] == NO_FIRE)
            pos.append(row[p][np.isfinite(row[p])])
            nv = row[n]; nv = nv[np.isfinite(nv)]
            neg.append(nv[:: max(1, len(nv) // 2000)])
    pos = np.concatenate(pos) if pos else np.zeros(0)
    neg = np.concatenate(neg) if neg else np.zeros(0)
    if len(pos) < lk["min_positives"]:
        return {"auc": None, "n_positives": int(len(pos))}
    return {"auc": auc(pos, neg), "n_positives": int(len(pos))}

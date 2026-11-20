"""Gates N1-N5: planted cheats must lose. Run on any Dataset (synthetic for CI, WildfireSpreadTS for the report)."""
from __future__ import annotations

import copy
import csv
import io
import json
import os
import random
import tempfile

import numpy as np

from . import baselines, card as cardmod, contract as ct, models, negatives, splits
from .dataset import FIRE, NO_FIRE, UNKNOWN, Dataset
from .features import danger_at
from .predictions import Predictions

TOP = 4


def _contract(extra=None):
    c = copy.deepcopy(ct.TEMPLATE)
    c["name"] = "gates"
    if extra:
        c.update(extra)
    return ct.validate(c)


def _fires(sp):
    return sorted(set(sp["folds"]["val"]) | set(sp["folds"]["test"]))


def _blocked_card(ds, sp, preds, name, c=None):
    return cardmod.build_card(ds, sp, preds, c or _contract(), name)


def _row_split_f1(ds, sp, preds):
    """Strict, cell-level F1 on rows of the naive random-row split; threshold from its validation rows."""
    out = {}
    for fold_name, fold_id in (("val", 1), ("test", 2)):
        out[fold_name] = []
    all_tab = {}
    for fid in sorted(preds.scores):
        s = ds.scenes[fid]
        T, H, W = s.state.shape
        tt, yy, xx = np.meshgrid(np.arange(T), np.arange(H), np.arange(W), indexing="ij")
        fi = np.full(tt.shape, sorted(ds.scenes).index(fid))
        fold = splits.row_fold(sp, fi.ravel(), tt.ravel(), yy.ravel(), xx.ravel()).reshape(tt.shape)
        tg = np.zeros(T, bool)
        tg[s.valid_targets()] = True
        known = (s.state != UNKNOWN) & tg[:, None, None]
        all_tab[fid] = (fold, known)

    def f1_at(thr, fold_id):
        tp = npred = nfire = 0
        for fid, (fold, known) in all_tab.items():
            s = ds.scenes[fid]
            sel = known & (fold == fold_id)
            with np.errstate(invalid="ignore"):
                P = (preds.scores[fid] >= thr) & sel
            F = (s.state == FIRE) & sel
            tp += int((P & F).sum()); npred += int(P.sum()); nfire += int(F.sum())
        p = tp / npred if npred else 0.0
        r = tp / nfire if nfire else 0.0
        return (2 * p * r / (p + r) if p + r else 0.0), p, r, npred, nfire

    vals = np.concatenate([preds.scores[f][np.isfinite(preds.scores[f])][::50] for f in all_tab])
    best, thr = -1, None
    for t in sorted(cardmod.candidate_thresholds(vals)):
        f = f1_at(t, 1)[0]
        if f >= best:
            best, thr = f, t
    f1, p, r, npred, nfire = f1_at(thr, 2)
    return {"threshold": float(thr), "f1": round(f1, 4), "precision": round(p, 4), "recall": round(r, 4),
            "area_ratio": round(npred / nfire, 3) if nfire else None}


def gate_n1(ds, sp_blocked, sp_rows):
    c = _contract()
    mem = models.Memoriser().fit(ds, sp_blocked["folds"]["train"])
    P = mem.predict(ds, _fires(sp_blocked))
    card = _blocked_card(ds, sp_blocked, P, "location-memoriser", c)
    lift = card["lift"]["location-memoriser_minus_persistence"]
    # blocked: not better than persistence (a clearly positive, CI-excluding-zero lift would be a failure)
    better = [(tn, rd) for tn in lift for rd in lift[tn] if lift[tn][rd]["diff_f1"] > 0 and lift[tn][rd]["excludes_zero"]]
    mm = card["models"]["location-memoriser"]["tolerances"]["strict"]["strict"]
    pm = card["models"]["persistence"]["tolerances"]["strict"]["strict"]
    # random cell-day split: same model, trained on random rows, scored on other random rows of the same fires
    ids = sorted(ds.scenes)

    def row_mask(fid):
        s = ds.scenes[fid]
        T, H, W = s.state.shape
        tt, yy, xx = np.meshgrid(np.arange(T), np.arange(H), np.arange(W), indexing="ij")
        fi = np.full(tt.shape, ids.index(fid))
        return splits.row_fold(sp_rows, fi.ravel(), tt.ravel(), yy.ravel(), xx.ravel()).reshape(tt.shape) == 0

    mem2 = models.Memoriser().fit(ds, ids, row_mask)
    rows = _row_split_f1(ds, sp_rows, mem2.predict(ds, ids))
    pers_rows = _row_split_f1(ds, sp_rows, baselines.persistence(ds, ids))
    # second cheat: neighbour-day interpolator (uses training rows of the same fire on adjacent days)
    interp_rows = _row_split_f1(ds, sp_rows, models.Interpolator().predict(ds, ids, row_mask))
    none_mask = lambda fid: np.zeros(ds.scenes[fid].state.shape, bool)        # split by fire: no row of a test fire is in training
    Pi = models.Interpolator().predict(ds, _fires(sp_blocked), none_mask)
    card_i = _blocked_card(ds, sp_blocked, Pi, "neighbour-day-interpolator", c)
    lift_i = card_i["lift"]["neighbour-day-interpolator_minus_persistence"]
    better_i = [(tn, rd) for tn in lift_i for rd in lift_i[tn] if lift_i[tn][rd]["diff_f1"] > 0 and lift_i[tn][rd]["excludes_zero"]]
    passed = (not better) and (not better_i)
    return {"gate": "N1", "passed": bool(passed),
            "claim": "a model that memorises location is no better than persistence under blocked splits",
            "blocked_memoriser_f1_strict": mm["f1"], "blocked_persistence_f1_strict": pm["f1"],
            "blocked_lift_cells_where_memoriser_clearly_better": better,
            "blocked_lift_strict_strict": lift["strict"]["strict"],
            "random_rows_memoriser": rows, "random_rows_persistence": pers_rows,
            "inflation_ratio_random_over_blocked_f1": round(rows["f1"] / max(mm["f1"], 1e-9), 2),
            "memoriser_beats_persistence_on_random_rows": rows["f1"] > pers_rows["f1"],
            "interpolator_random_rows": interp_rows,
            "interpolator_beats_persistence_on_random_rows": interp_rows["f1"] > pers_rows["f1"],
            "interpolator_blocked_f1_strict": card_i["models"]["neighbour-day-interpolator"]["tolerances"]["strict"]["strict"]["f1"],
            "interpolator_blocked_lift_strict_strict": lift_i["strict"]["strict"],
            "interpolator_blocked_lift_cells_where_clearly_better": better_i}


def gate_n2(ds, sp):
    P = models.flag_everything(ds, _fires(sp))
    card = _blocked_card(ds, sp, P, "flag-everything")
    m, p = card["models"]["flag-everything"], card["models"]["persistence"]
    f_m = m["tolerances"]["strict"]["strict"]["f1"]
    f_p = p["tolerances"]["strict"]["strict"]["f1"]
    warned = any("OVER-PREDICTION" in w for w in card["warnings"])
    return {"gate": "N2", "passed": bool(f_m < f_p and warned), "claim": "a model that flags everything loses on the card",
            "f1_flag_everything_strict": f_m, "f1_persistence_strict": f_p, "area_ratio": m["area_ratio"],
            "over_prediction_warning_printed": warned,
            "f1_flag_everything_loose": m["tolerances"]["loose"]["strict"]["f1"], "f1_persistence_loose": p["tolerances"]["loose"]["strict"]["f1"]}


def gate_n3(ds, sp, honest_model_preds):
    fires = _fires(sp)
    out = {}
    for label, kw in (("scar_lying_declaration", dict(kind="scar")), ("next_day_lying_declaration", dict(kind="next")),
                      ("scar_honest_declaration", dict(kind="scar", honest_declaration=True))):
        P = models.leaky(ds, fires, **kw)
        card = _blocked_card(ds, sp, P, "leaky")
        out[label] = {"status": card["leak"]["status"], "auc": card["leak"].get("auc"), "detail": card["leak"]["detail"]}
    card_f = _blocked_card(ds, sp, models.leaky_front(ds, fires), "leaky")
    out["front_peek_lying_declaration"] = {"status": card_f["leak"]["status"], "auc": card_f["leak"].get("front_auc"), "detail": card_f["leak"]["detail"]}
    honest = _blocked_card(ds, sp, honest_model_preds, "honest")
    out["honest_model"] = {"status": honest["leak"]["status"], "auc": honest["leak"].get("auc")}
    caught = all(not out[k]["status"].startswith("pass") for k in ("scar_lying_declaration", "next_day_lying_declaration", "scar_honest_declaration", "front_peek_lying_declaration"))
    return {"gate": "N3", "passed": bool(caught and out["honest_model"]["status"] == "pass"),
            "claim": "a model fed information from after the fire is caught by the leak check (and an honest model is not)", **out}


def gate_n4(ds, sp, preds, name="model"):
    c = _contract()
    fires = _fires(sp)
    hashes = {}
    base = cardmod.to_json(cardmod.build_card(ds, sp, preds, c, name))
    hashes["dense_first_run"] = _h(base)
    hashes["dense_second_run"] = _h(cardmod.to_json(cardmod.build_card(ds, sp, preds, c, name)))
    shuffled = Predictions({k: preds.scores[k] for k in random.Random(1).sample(sorted(preds.scores), len(preds.scores))},
                           {k: preds.info_until[k] for k in random.Random(2).sample(sorted(preds.info_until), len(preds.info_until))}, preds.meta)
    shuffled_ds = Dataset(ds.name, {k: ds.scenes[k] for k in random.Random(3).sample(sorted(ds.scenes), len(ds.scenes))}, ds.cell_km, ds.meta)
    hashes["dense_shuffled_order"] = _h(cardmod.to_json(cardmod.build_card(shuffled_ds, sp, shuffled, c, name)))
    # sparse csv route: top 3% cells of each fire, rows in three different orders
    rows = []
    sc = {}
    for fid in fires:
        s = ds.scenes[fid]
        a = preds.scores[fid]
        v = a[np.isfinite(a)]
        q = np.quantile(v[::20], 0.97) if len(v) else 1.0
        for t in s.valid_targets():
            ys, xs = np.nonzero(a[t] >= q)
            for y, x in zip(ys, xs):
                import datetime as dt
                rows.append((fid, dt.date.fromordinal(int(s.dates[t])).isoformat(), int(y), int(x), float(a[t, y, x]),
                             dt.date.fromordinal(int(s.dates[t]) - 1).isoformat()))
    csv_hashes = []
    for order in ("as_is", "reversed", "random"):
        rr = list(rows)
        if order == "reversed":
            rr.reverse()
        elif order == "random":
            random.Random(7).shuffle(rr)
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
            w = csv.writer(f)
            w.writerow(["fire_id", "date", "y", "x", "score", "info_until"])
            w.writerows(rr)
            path = f.name
        P2 = Predictions.from_csv(path, ds, {"info_until_lag_days": 1})
        for fid in fires:
            P2.scores.setdefault(fid, np.full(ds.scenes[fid].state.shape, -np.inf, np.float32))
        os.unlink(path)
        csv_hashes.append(_h(cardmod.to_json(cardmod.build_card(ds, sp, P2, c, name))))
    hashes["csv_orders"] = csv_hashes
    ok = len({hashes["dense_first_run"], hashes["dense_second_run"], hashes["dense_shuffled_order"]}) == 1 and len(set(csv_hashes)) == 1
    return {"gate": "N4", "passed": bool(ok), "claim": "same predictions give the same card in any order and on a re-run", "hashes": hashes}


def _h(s):
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def _top_danger_area(ds, fires, preds, thr, danger=TOP):
    npred = nfire = 0
    for fid in fires:
        s = ds.scenes[fid]
        for t in s.valid_targets():
            d = danger_at(s, int(t)) == danger
            known = s.state[t] != UNKNOWN
            with np.errstate(invalid="ignore"):
                P = (preds.scores[fid][t] >= thr) & known & d
            npred += int(P.sum())
            nfire += int(((s.state[t] == FIRE) & d).sum())
    return npred, nfire


def gate_n5(ds, sp, k=3, r_max=2.0, prox=False):
    train = sp["folds"]["train"]
    fires = _fires(sp)
    out = {}
    for label, matched in (("matched", True), ("random", False)):
        tab = negatives.sample(ds, train, k=k, matched=matched)
        m = models.Logistic(f"wx-{label}", prox=prox).fit(ds, tab["table"], tab["fires"])
        P = m.predict(ds, fires)
        c = _contract()
        ctxs = {f: cardmod.SceneCtx(ds.scenes[f], c) for f in fires}
        thr_val = cardmod.choose_threshold(ds, sp["folds"]["val"], lambda f: P.scores[f], c, ctxs)
        row = {}
        for tname, thr in (("validation_threshold", thr_val), ("fixed_0.5", 0.5)):
            npred, nfire = _top_danger_area(ds, sp["folds"]["test"], P, thr)
            row[tname] = {"threshold": round(float(thr), 6), "pred_cells_top_danger": npred, "true_cells_top_danger": nfire,
                          "area_ratio_top_danger": round(npred / nfire, 3) if nfire else None}
        out[label] = {"negatives_stats": {k2: v for k2, v in tab["stats"].items() if k2 in ("positives", "negatives", "by_danger", "match_level_share", "hard_share_of_negatives")}, **row}
    mt = out["matched"]["validation_threshold"]["area_ratio_top_danger"]
    rt = out["random"]["validation_threshold"]["area_ratio_top_danger"]
    mt5 = out["matched"]["fixed_0.5"]["area_ratio_top_danger"]
    rt5 = out["random"]["fixed_0.5"]["area_ratio_top_danger"]
    primary = (mt is not None and rt is not None and mt <= r_max and rt > r_max)
    secondary = (mt5 is not None and rt5 is not None and mt5 <= r_max and rt5 > r_max)
    return {"gate": "N5", "model_uses_proximity_features": prox, "passed": bool(primary), "claim": "matched negatives do not over-predict in top-danger periods where random negatives do",
            "pre_registered_ratio_limit": r_max, "primary_reading_validation_threshold": primary,
            "secondary_reading_fixed_0.5": secondary, **out}


def run_all(ds: Dataset, seed: int = 54) -> dict:
    sp = splits.make(ds, "space", seed=seed)
    spr = splits.make(ds, "random_rows", seed=seed)
    tab = negatives.sample(ds, sp["folds"]["train"], k=3)
    honest = models.Logistic("wx+prox", prox=True).fit(ds, tab["table"], tab["fires"]).predict(ds, _fires(sp))
    res = {"dataset": ds.name, "summary": ds.summary(), "split": {"sha256": sp["sha256"], "folds": {k: len(v) for k, v in sp["folds"].items()}, "dropped": len(sp["dropped"])}}
    res["N1"] = gate_n1(ds, sp, spr)
    res["N2"] = gate_n2(ds, sp)
    res["N3"] = gate_n3(ds, sp, honest)
    res["N4"] = gate_n4(ds, sp, honest)
    res["N5"] = gate_n5(ds, sp)
    res["N5_prox"] = gate_n5(ds, sp, prox=True)
    res["honest_model_card"] = cardmod.build_card(ds, sp, honest, _contract(), "wx+prox")
    return res


def main(a) -> int:
    ds = Dataset.load(a.dataset)
    res = run_all(ds)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True, default=str)
    for g in ("N1", "N2", "N3", "N4", "N5"):
        print(g, "PASS" if res[g]["passed"] else "FAIL")
    return 0 if all(res[g]["passed"] for g in ("N1", "N2", "N3", "N4", "N5")) else 1

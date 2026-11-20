"""Run S1, S2, S3, S5 over sequence lists. Credit: HPWREN, http://hpwren.ucsd.edu/ (image data)."""
from __future__ import annotations
import json, os, hashlib
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from . import pipeline, s1 as S1, seq
from .params import get as get_params, cfg_hash

RAW = "/home/user/wildfire 3 (1)/firewitness_raw/figlib/"
CACHE = "/home/user/cache"


def seq_path(name, raw=RAW):
    return os.path.join(raw, name)


def _s23(args):
    name, p, raw = args
    sq = seq.load_sequence(seq_path(name, raw), CACHE)
    r = pipeline.label_sequence(sq, p)
    if r["excluded"]:
        return dict(name=name, excluded=r["excluded"], info=r["prep"]["info"])
    pr = r["prep"]
    main = r["main"]
    return dict(name=name, excluded=None, info=pr["info"], n_pre=int(len(pr["pre_idx"])), L0=pr["L0"],
                S=[float(x) for x in pr["S"]], S_fitted=pr["S_fitted"],
                placebo_frames=[int(t) for t in r["placebo_frames"]],
                first_offset=r["first_offset"], first_frame=None if r["first_frame"] is None else int(r["first_frame"]),
                main=None if main is None else dict(seed_xy=[float(v) for v in main["seed_xy"]], seed_area=int(main["seed_area"]),
                                                    mass=float(main["mass"]), t_conf=int(main["t_conf"]), area_conf=int(main["area_conf"])),
                n_smoke_chains=int(sum(1 for c in r["chains"] if c["cls"] == "smoke")),
                out_hash=output_hash(r))


def output_hash(r):
    h = hashlib.sha256()
    h.update(np.round(r["prep"]["alpha"], 5).tobytes())
    h.update(json.dumps(r["first_frame"]).encode())
    return h.hexdigest()


def run_s23(names, p=None, workers=4, raw=RAW):
    p = p or get_params()
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(_s23, [(n, p, raw) for n in names]))


def _s1(args):
    n, k, am, e, p, raw = args
    sq = seq.load_sequence(seq_path(n, raw), CACHE)
    try:
        return S1.evaluate_case(sq, k, am, e, p)
    except Exception as ex:                      # a failing case is reported, never dropped
        return dict(name=n, k=k, amax=am, endm=e, excluded="error: %s" % ex)


def run_s1(cases, p=None, workers=4, raw=RAW):
    p = p or get_params()
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(_s1, [(n, k, am, e, p, raw) for n, k, am, e in cases]))


def boot_ci(values, clusters, stat=np.mean, n=2000, seed=0):
    values = np.asarray(values, float); clusters = np.asarray(clusters)
    ok = np.isfinite(values)
    values, clusters = values[ok], clusters[ok]
    if len(values) == 0:
        return (np.nan, np.nan, np.nan)
    ids = sorted(set(clusters))
    idx = {c: np.where(clusters == c)[0] for c in ids}
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        pick = rng.choice(len(ids), len(ids))
        v = np.concatenate([values[idx[ids[i]]] for i in pick])
        out.append(stat(v))
    return float(stat(values)), float(np.quantile(out, 0.025)), float(np.quantile(out, 0.975))


def summarise_s1(rows):
    good = [r for r in rows if not r.get("excluded")]
    ex = len(rows) - len(good)
    def col(k): return np.array([r.get(k, np.nan) for r in good], float)
    out = dict(n_cases=len(rows), n_excluded=ex, n_sequences=len({r["name"] for r in good}))
    cl = [r["name"] for r in good]
    out["mae"] = boot_ci(col("mae"), cl)
    out["bias"] = boot_ci(col("bias"), cl)
    for lv in ["L0", "0.10", "0.20", "0.40", "0.60"]:
        out[f"edge_{lv}_median"] = float(np.nanmedian(col(f"edge_{lv}"))) if np.isfinite(col(f"edge_{lv}")).any() else None
        out[f"edge_{lv}_n"] = int(np.isfinite(col(f"edge_{lv}")).sum())
    det = np.array([bool(r.get("detected")) for r in good])
    amax = col("amax")
    out["detect_all"] = boot_ci(det.astype(float), cl)
    hi = amax >= 0.6
    out["detect_amax>=0.6"] = boot_ci(det[hi].astype(float), [c for c, h in zip(cl, hi) if h])
    fe = col("first_err_frames")
    out["first_err_median_frames"] = float(np.nanmedian(fe)) if np.isfinite(fe).any() else None
    out["first_err_n"] = int(np.isfinite(fe).sum())
    out["false_smoke_chains_mean"] = float(np.mean(col("false_smoke_chains")))
    byE = {}
    for e in S1.ENDMEMBERS:
        sel = [r for r in good if r["endm"] == e]
        byE[e] = dict(n=len(sel), mae=float(np.nanmean([r["mae"] for r in sel])) if sel else None,
                      bias=float(np.nanmean([r["bias"] for r in sel])) if sel else None,
                      detect=float(np.mean([bool(r["detected"]) for r in sel])) if sel else None)
    out["by_endmember"] = byE
    byA = {}
    for a in S1.AMAX:
        sel = [r for r in good if r["amax"] == a]
        byA[str(a)] = dict(n=len(sel), mae=float(np.nanmean([r["mae"] for r in sel])) if sel else None,
                           bias=float(np.nanmean([r["bias"] for r in sel])) if sel else None,
                           detect=float(np.mean([bool(r["detected"]) for r in sel])) if sel else None)
    out["by_amax"] = byA
    return out


def summarise_s23(res):
    ok = [r for r in res if not r.get("excluded")]
    out = dict(n_sequences=len(res), n_excluded=len(res) - len(ok),
               excluded=[(r["name"], r["excluded"]) for r in res if r.get("excluded")])
    pf = np.array([len(r["placebo_frames"]) for r in ok], float); nf = np.array([r["n_pre"] for r in ok], float)
    out["placebo_false_frames"] = int(pf.sum()); out["placebo_frames"] = int(nf.sum())
    out["placebo_rate"] = float(pf.sum() / nf.sum()) if nf.sum() else None
    rates = pf / nf
    out["placebo_rate_ci"] = boot_ci(pf / nf, [r["name"] for r in ok]) if len(ok) else None
    # pooled bootstrap over sequences of the frame-weighted rate
    rng = np.random.default_rng(0); b = []
    for _ in range(2000):
        i = rng.integers(0, len(ok), len(ok)); b.append(pf[i].sum() / nf[i].sum())
    out["placebo_rate_pooled_ci"] = [float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975))] if len(ok) else None
    out["sequences_with_false_frames"] = int((pf > 0).sum())
    det = [r for r in ok if r["first_offset"] is not None]
    out["detected"] = len(det); out["detected_share"] = len(det) / max(len(ok), 1)
    d = np.array([r["first_offset"] for r in det], float)
    if len(d):
        out["s3_median_s"] = float(np.median(d)); out["s3_mean_s"] = float(d.mean())
        out["s3_q"] = [float(np.quantile(d, q)) for q in (0.1, 0.25, 0.5, 0.75, 0.9)]
        out["s3_share_before_human"] = float((d < 0).mean()); out["s3_share_after_human"] = float((d > 0).mean())
        out["s3_share_within_5min"] = float((abs(d) <= 300).mean())
    return out

"""Negatives only from verified no-fire cells, matched to positives on danger class, land cover, region, season.

Output table columns (numpy arrays, one entry per sampled row):
  fire (index into `fires`), t, y, x, label (1 fire / 0 no fire), hard (0/1), level (match level 0..4, 9 = hard top-up,
  -1 for positives), stratum (exact key of the positive each row is matched to).
"""
from __future__ import annotations

import json

import numpy as np

from .dataset import Dataset, FIRE, NO_FIRE
from .features import danger_at
from .ops import dilate_space
from .strata import hard_mask, hash_str, lc_group

LEVELS = {0: "exact (danger, land cover, region, month)", 1: "month +-1", 2: "danger +-1 and month +-1",
          3: "same land-cover group and region, same danger", 4: "same danger, any land cover/region/month",
          9: "hard top-up (not matched)"}
R_MOD = 100003


def _mdist(a, b):
    d = np.abs(a - b)
    return np.minimum(d, 12 - d)


def _cells(ds: Dataset, ids, buffer_cells: int, hard_km: float):
    """Positives and eligible negative candidates over all valid target days of the given fires."""
    P, C = [], []
    for fi, fid in enumerate(ids):
        s = ds.scenes[fid]
        reg = hash_str(s.region) % R_MOD
        lcg = lc_group(s.static["landcover"])
        lc = s.static["landcover"].astype(np.int16)
        for t in s.valid_targets():
            st = s.state[t]
            fire = st == FIRE
            d = danger_at(s, int(t))
            mon = s.month(int(t))
            near = dilate_space(fire, buffer_cells) if buffer_cells else fire
            neg = (st == NO_FIRE) & ~near
            hm = hard_mask(s, int(t), hard_km=hard_km) if neg.any() else None
            for mask, store in ((fire, P), (neg, C)):
                yy, xx = np.nonzero(mask)
                if len(yy) == 0:
                    continue
                n = len(yy)
                rec = (np.full(n, fi, np.int32), np.full(n, t, np.int32), yy.astype(np.int32), xx.astype(np.int32),
                       d[yy, xx].astype(np.int16), lc[yy, xx], lcg[yy, xx].astype(np.int16),
                       np.full(n, reg, np.int32), np.full(n, mon, np.int16),
                       (hm[yy, xx] if (store is C) else np.zeros(n, bool)))
                store.append(rec)
    cat = lambda L: tuple(np.concatenate([r[i] for r in L]) for i in range(10)) if L else tuple(np.zeros(0) for _ in range(10))
    return cat(P), cat(C)


def _slice_pool(keys_sorted, order, key):
    lo = np.searchsorted(keys_sorted, key, "left")
    hi = np.searchsorted(keys_sorted, key, "right")
    return order[lo:hi]


def sample(ds: Dataset, ids, k: int = 3, seed: int = 54, buffer_cells: int = 1, hard_share: float = 0.25,
           hard_km: float = 10.0, matched: bool = True) -> dict:
    """Matched sampler (matched=True) or the naive random-negatives sampler (matched=False)."""
    ids = sorted(ids)
    (pf, pt, py, px, pd, plc, plg, pr, pm, _), (cf, ct, cy, cx, cd, clc, clg, cr, cm, chard) = _cells(ds, ids, buffer_cells, hard_km)
    npos, ncand = len(pf), len(cf)
    taken = np.zeros(ncand, bool)
    sel_idx, sel_level, sel_strat = [], [], []
    rng_all = np.random.default_rng([seed, 1])
    if matched and npos and ncand:
        k0 = ((cd.astype(np.int64) * 40 + clc) * R_MOD + cr) * 13 + cm
        k1 = (cd.astype(np.int64) * 40 + clc) * R_MOD + cr
        k2 = clc.astype(np.int64) * R_MOD + cr
        k3 = clg.astype(np.int64) * R_MOD + cr
        k4 = cd.astype(np.int64)
        pools = []
        for kk in (k0, k1, k2, k3, k4):
            o = np.argsort(kk, kind="stable")
            pools.append((kk[o], o))
        p0 = ((pd.astype(np.int64) * 40 + plc) * R_MOD + pr) * 13 + pm
        uk, inv, cnt = np.unique(p0, return_inverse=True, return_counts=True)
        first = np.zeros(len(uk), np.int64)
        first[inv[::-1]] = np.arange(len(p0))[::-1]
        for si, key in enumerate(uk):
            need = k * int(cnt[si])
            rng = np.random.default_rng([seed, int(key) % (2 ** 62)])
            j = first[si]
            d0, lc0, lg0, r0, m0 = int(pd[j]), int(plc[j]), int(plg[j]), int(pr[j]), int(pm[j])
            got = 0
            for lev in range(5):
                if got >= need:
                    break
                kk = (key, (d0 * 40 + lc0) * R_MOD + r0, lc0 * R_MOD + r0, lg0 * R_MOD + r0, d0)[lev]
                pool = _slice_pool(pools[lev][0], pools[lev][1], kk)
                if len(pool) == 0:
                    continue
                pool = pool[~taken[pool]]
                if lev == 1:
                    pool = pool[_mdist(cm[pool], m0) <= 1]
                elif lev == 2:
                    pool = pool[(np.abs(cd[pool] - d0) <= 1) & (_mdist(cm[pool], m0) <= 1)]
                elif lev == 3:
                    pool = pool[cd[pool] == d0]
                if len(pool) == 0:
                    continue
                take = pool if len(pool) <= need - got else rng.choice(pool, need - got, replace=False)
                taken[take] = True
                sel_idx.append(take)
                sel_level.append(np.full(len(take), lev, np.int8))
                sel_strat.append(np.full(len(take), key, np.int64))
                got += len(take)
        sel_idx = np.concatenate(sel_idx) if sel_idx else np.zeros(0, np.int64)
        lev_arr = np.concatenate(sel_level) if sel_level else np.zeros(0, np.int8)
        st_arr = np.concatenate(sel_strat) if sel_strat else np.zeros(0, np.int64)
        # hard top-up to the stated share
        h0 = int(chard[sel_idx].sum())
        M = len(sel_idx)
        e = int(np.ceil(max(0.0, (hard_share * M - h0) / (1 - hard_share))))
        extra = np.nonzero(chard & ~taken)[0]
        if e and len(extra):
            ex = rng_all.choice(extra, min(e, len(extra)), replace=False)
            taken[ex] = True
            sel_idx = np.concatenate([sel_idx, ex])
            lev_arr = np.concatenate([lev_arr, np.full(len(ex), 9, np.int8)])
            st_arr = np.concatenate([st_arr, np.full(len(ex), -1, np.int64)])
    else:
        n = min(k * npos, ncand)
        sel_idx = rng_all.choice(ncand, n, replace=False) if ncand else np.zeros(0, np.int64)
        lev_arr = np.full(len(sel_idx), 5, np.int8)
        st_arr = np.full(len(sel_idx), -1, np.int64)
    o = np.lexsort((cx[sel_idx], cy[sel_idx], ct[sel_idx], cf[sel_idx]))   # canonical order
    sel_idx, lev_arr, st_arr = sel_idx[o], lev_arr[o], st_arr[o]
    po = np.lexsort((px, py, pt, pf))
    table = {
        "fire": np.concatenate([pf[po], cf[sel_idx]]).astype(np.int32),
        "t": np.concatenate([pt[po], ct[sel_idx]]).astype(np.int32),
        "y": np.concatenate([py[po], cy[sel_idx]]).astype(np.int32),
        "x": np.concatenate([px[po], cx[sel_idx]]).astype(np.int32),
        "label": np.concatenate([np.ones(npos, np.int8), np.zeros(len(sel_idx), np.int8)]),
        "hard": np.concatenate([np.zeros(npos, np.int8), chard[sel_idx].astype(np.int8)]),
        "level": np.concatenate([np.full(npos, -1, np.int8), lev_arr]),
        "danger": np.concatenate([pd[po], cd[sel_idx]]).astype(np.int8),
        "month": np.concatenate([pm[po], cm[sel_idx]]).astype(np.int8),
    }
    stats = balance(table, ids, matched, npos, ncand)
    return {"fires": ids, "table": table, "stats": stats}


def balance(table, ids, matched, npos, ncand) -> dict:
    lab, d, lev, hard = table["label"], table["danger"], table["level"], table["hard"]
    st = {"matched": matched, "positives": int(npos), "negatives": int((lab == 0).sum()), "eligible_negative_candidates": int(ncand),
          "by_danger": {}, "match_level_share": {}, "hard_share_of_negatives": None}
    for c in range(5):
        st["by_danger"][str(c)] = {"pos": int(((lab == 1) & (d == c)).sum()), "neg": int(((lab == 0) & (d == c)).sum())}
    neg = lab == 0
    if neg.any():
        for lv in np.unique(lev[neg]):
            st["match_level_share"][LEVELS.get(int(lv), "random (unmatched)")] = round(float((lev[neg] == lv).mean()), 4)
        st["hard_share_of_negatives"] = round(float(hard[neg].mean()), 4)
    return st


def save(result: dict, path: str) -> None:
    np.savez_compressed(path, **result["table"])
    with open(path.replace(".npz", ".json"), "w") as f:
        json.dump({"fires": result["fires"], "stats": result["stats"]}, f, indent=1, sort_keys=True)


def load(path: str) -> dict:
    z = np.load(path)
    info = json.load(open(path.replace(".npz", ".json")))
    return {"fires": info["fires"], "table": {k: z[k] for k in z.files}, "stats": info["stats"]}

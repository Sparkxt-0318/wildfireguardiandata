"""Tool 3: record linkage and duplicate detection.

Candidate pairs come from space and time blocking. Each compared field is a witness with several exclusive
levels (distance, day difference, size ratio, name similarity, state); level probabilities for true and false
pairs (m, u) and the share of true pairs are fitted WITHOUT labels by EM (Fellegi-Sunter). The posterior match
probability gives one of three outcomes: link, no link, undecided. Published links are never used as features.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from . import geo

EPS = 1e-9


# ------------------------------------------------------------------ names
_STOP = {"FIRE", "COMPLEX", "THE", "FIRES", "WILDFIRE", "INCIDENT", "NO", "NUMBER", "UNIT", "OF", "AND"}


def name_tokens(s) -> frozenset:
    if not isinstance(s, str):
        return frozenset()
    t = re.sub(r"[^A-Z0-9 ]", " ", s.upper()).split()
    return frozenset(x for x in t if x not in _STOP)


def name_sim(a, b) -> float:
    """Jaccard on tokens; NaN if either side has no name."""
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return np.nan
    na, nb = {x for x in ta if x.isdigit()}, {x for x in tb if x.isdigit()}
    if na and nb and na != nb and (ta - na) == (tb - nb):
        return 0.0      # numbered siblings (BEAR BASIN 2 / BEAR BASIN 3): same words, different number = different fires
    return len(ta & tb) / len(ta | tb)


# ------------------------------------------------------------------ candidates
def candidate_pairs(L: pd.DataFrame, R: pd.DataFrame, radius_km, day_window: float | None = 30.0, max_per_right: int = 2000) -> pd.DataFrame:
    """Pairs (li, ri) with distance <= radius (scalar or per-R array, km) and |day_L - day_R| <= day_window.

    L, R need lat, lon, day (NaN day = no time filter for that row). Indices are positional."""
    ok = (np.isfinite(L.lat) & np.isfinite(L.lon)).to_numpy()
    lidx = np.flatnonzero(ok)
    tree = cKDTree(geo.xyz(L.lat.to_numpy()[lidx], L.lon.to_numpy()[lidx]))
    rr = np.broadcast_to(np.asarray(radius_km, float), (len(R),))
    rok = np.flatnonzero((np.isfinite(R.lat) & np.isfinite(R.lon)).to_numpy())
    lists = tree.query_ball_point(geo.xyz(R.lat.to_numpy()[rok], R.lon.to_numpy()[rok]), geo.km_to_chord(rr[rok]), workers=4)
    ld, rd = L.day.to_numpy(), R.day.to_numpy()
    li, ri = [], []
    for r, hits in zip(rok, lists):
        if not hits:
            continue
        h = lidx[np.asarray(hits)]
        if day_window is not None and np.isfinite(rd[r]):
            dd = np.abs(ld[h] - rd[r])
            h = h[np.isnan(dd) | (dd <= day_window)]
        if len(h) > max_per_right:
            h = h[:max_per_right]
        li.append(h)
        ri.append(np.full(len(h), r))
    if not li:
        return pd.DataFrame({"li": [], "ri": []}, dtype=int)
    return pd.DataFrame({"li": np.concatenate(li), "ri": np.concatenate(ri)})


# ------------------------------------------------------------------ comparison
LEVELS = {
    "dist": [0.5, 2, 5, 15],               # km upper edges -> 5 levels
    "day": [0, 1, 3, 14],                  # |days| upper edges -> 5 levels
    "size": [0.1, 0.5, 2.0],               # |log2 ratio| upper edges -> 4 levels
    "name": [0.99, 0.5, 0.01],             # similarity lower edges -> levels 0 best .. 3
    "rdist": [0.25, 0.5, 1.0, 2.0],        # distance / fire radius -> 5 levels
    "state": [],                           # equal / different -> 2 levels
}
NLEV = {"id": 2, "rdist": 5, "dist": 5, "day": 5, "size": 4, "name": 4, "state": 2}
FIELDS = ["dist", "day", "size", "name", "state"]


def compare(L: pd.DataFrame, R: pd.DataFrame, pairs: pd.DataFrame, use=FIELDS) -> np.ndarray:
    """(n_pairs, n_fields) int8 level matrix, -1 where a field is missing on either side."""
    li, ri = pairs["li"].to_numpy(), pairs["ri"].to_numpy()
    out = np.full((len(pairs), len(use)), -1, dtype=np.int8)
    for j, f in enumerate(use):
        if f == "dist":
            d = geo.haversine_km(L.lat.to_numpy()[li], L.lon.to_numpy()[li], R.lat.to_numpy()[ri], R.lon.to_numpy()[ri])
            out[:, j] = np.digitize(d, LEVELS["dist"], right=True)
            out[~np.isfinite(d), j] = -1
        elif f == "id":
            a, b = L.ident.to_numpy(dtype=object)[li], R.ident.to_numpy(dtype=object)[ri]
            ok = pd.notna(a) & pd.notna(b)
            out[:, j] = np.where(ok, (a != b).astype(np.int8), -1)     # level 0 = same identifier, 1 = different
        elif f == "rdist":
            d = geo.haversine_km(L.lat.to_numpy()[li], L.lon.to_numpy()[li], R.lat.to_numpy()[ri], R.lon.to_numpy()[ri])
            ac = np.nanmax(np.vstack([np.nan_to_num(L.acres.to_numpy()[li], nan=0.0), np.nan_to_num(R.acres.to_numpy()[ri], nan=0.0)]), axis=0)
            rad = np.sqrt(np.maximum(ac, 1.0) * 0.00405 / np.pi) + 0.5
            out[:, j] = np.digitize(d / rad, LEVELS["rdist"], right=True)
            out[~np.isfinite(d), j] = -1
        elif f == "day":
            d = np.abs(L.day.to_numpy()[li] - R.day.to_numpy()[ri])
            out[:, j] = np.digitize(d, LEVELS["day"], right=True)
            out[~np.isfinite(d), j] = -1
        elif f == "size":
            a, b = L.acres.to_numpy()[li], R.acres.to_numpy()[ri]
            with np.errstate(divide="ignore", invalid="ignore"):
                lr = np.abs(np.log2((a + 0.01) / (b + 0.01)))
            out[:, j] = np.digitize(lr, LEVELS["size"], right=True)
            out[~np.isfinite(lr) | ~(a > 0) | ~(b > 0), j] = -1
        elif f == "name":
            ln, rn = L.name.to_numpy(dtype=object)[li], R.name.to_numpy(dtype=object)[ri]
            uniq = pd.DataFrame({"a": ln, "b": rn}).drop_duplicates()
            uniq["s"] = [name_sim(a, b) for a, b in zip(uniq.a, uniq.b)]
            s = pd.DataFrame({"a": ln, "b": rn}).merge(uniq, on=["a", "b"], how="left")["s"].to_numpy()
            lv = np.where(s >= 0.99, 0, np.where(s >= 0.5, 1, np.where(s > 0.01, 2, 3))).astype(np.int8)
            lv[~np.isfinite(s)] = -1
            out[:, j] = lv
        elif f == "state":
            a, b = L.state.to_numpy(dtype=object)[li], R.state.to_numpy(dtype=object)[ri]
            ok = pd.notna(a) & pd.notna(b)
            out[:, j] = np.where(ok, (a == b).astype(np.int8) ^ 1, -1)   # level 0 = equal, 1 = different
    return out


# ------------------------------------------------------------------ Fellegi-Sunter, categorical, unlabeled EM
@dataclass
class FSModel:
    fields: list
    m: list            # per field: P(level | match)
    u: list            # per field: P(level | non-match)
    prior: float
    iters: int = 0

    def log_odds(self, X: np.ndarray) -> np.ndarray:
        lo = np.full(len(X), np.log(self.prior / (1 - self.prior)))
        for j in range(len(self.fields)):
            lv = X[:, j]
            ok = lv >= 0
            llr = np.log(np.clip(self.m[j], EPS, None)) - np.log(np.clip(self.u[j], EPS, None))
            lo[ok] += llr[lv[ok]]
        return lo

    def posterior(self, X: np.ndarray) -> np.ndarray:
        return 1 / (1 + np.exp(-np.clip(self.log_odds(X), -40, 40)))


def fit_fs(X: np.ndarray, fields, init_prior=0.05, iters=200, tol=1e-7, smooth=0.5, w=None) -> FSModel:
    """EM without labels. Initialise m to favour the best (lowest) levels so the match class is the close one."""
    n, k = X.shape
    m, u = [], []
    for j in range(k):
        L = NLEV[fields[j]]
        base = np.arange(L, 0, -1, dtype=float)
        m.append(base / base.sum() * 0.0 + (base ** 3) / (base ** 3).sum())
        u.append((np.arange(1, L + 1, dtype=float) ** 2) / (np.arange(1, L + 1) ** 2).sum())
    prior = init_prior
    w = np.ones(n) if w is None else w
    for it in range(iters):
        lo = np.full(n, np.log(prior / (1 - prior)))
        for j in range(k):
            lv = X[:, j]
            ok = lv >= 0
            lo[ok] += np.log(np.clip(m[j][lv[ok]], EPS, None)) - np.log(np.clip(u[j][lv[ok]], EPS, None))
        g = 1 / (1 + np.exp(-np.clip(lo, -40, 40)))
        newp = float(np.clip((g * w).sum() / w.sum(), 1e-6, 1 - 1e-6))
        nm, nu = [], []
        for j in range(k):
            L = NLEV[fields[j]]
            ok = X[:, j] >= 0
            mm = np.bincount(X[ok, j], weights=(g * w)[ok], minlength=L) + smooth
            uu = np.bincount(X[ok, j], weights=((1 - g) * w)[ok], minlength=L) + smooth
            nm.append(mm / mm.sum())
            nu.append(uu / uu.sum())
        delta = max(abs(newp - prior), *(np.abs(a - b).max() for a, b in zip(nm, m)))
        m, u, prior = nm, nu, newp
        if delta < tol:
            break
    return FSModel(list(fields), m, u, prior, it + 1)


# ------------------------------------------------------------------ decisions
def decide(pairs: pd.DataFrame, post: np.ndarray, hi=0.95, lo=0.05, margin=0.25, side="left", one_to_one=False) -> pd.DataFrame:
    """Outcome per candidate pair: link, no_link, undecided.

    side='left': each left record may link to at most one right record (the best candidate must beat the second
    by `margin` in probability, else undecided). Right records may take several left records (complexes)."""
    p = pairs.copy()
    p["post"] = post
    key = "li" if side == "left" else "ri"
    p = p.sort_values([key, "post"], ascending=[True, False])
    rank = p.groupby(key).cumcount()
    second = p.groupby(key)["post"].transform(lambda s: s.iloc[1] if len(s) > 1 else 0.0)
    p["rank"] = rank
    p["second"] = second
    best = rank == 0
    link = best & (p["post"] >= hi) & ((p["post"] - p["second"]) >= margin)
    und = (best & ~link & (p["post"] > lo)) | (~best & (p["post"] >= hi))
    p["outcome"] = np.where(link, "link", np.where(und, "undecided", "no_link"))
    return p


# ------------------------------------------------------------------ baselines and scoring
def fixed_rule(pairs: pd.DataFrame, X: np.ndarray, fields, dist_level: int, day_level: int, side="left") -> pd.DataFrame:
    """A single-threshold rule: link the nearest candidate within a distance level and a day level."""
    jd = fields.index("dist")
    ok = (X[:, jd] >= 0) & (X[:, jd] <= dist_level)
    score = -X[:, jd] * 100.0
    if "day" in fields:
        jt = fields.index("day")
        ok &= X[:, jt] <= day_level
        score = score - X[:, jt]
    p = pairs[ok].copy()
    p["score"] = score[ok]
    key = "li" if side == "left" else "ri"
    p = p.sort_values([key, "score"], ascending=[True, False]).drop_duplicates(key)
    return p[["li", "ri"]]


def prf(pred: set, truth: set) -> dict:
    tp = len(pred & truth)
    p = tp / len(pred) if pred else 0.0
    r = tp / len(truth) if truth else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": p, "recall": r, "f1": f, "tp": tp, "n_pred": len(pred), "n_truth": len(truth)}

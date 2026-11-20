"""Tool 3b: duplicates within one table (or a stack of tables).

Pairs by space and time; each compared field is a witness; the match probability is fitted without labels
(see link.py); outcomes: link, no link, undecided. Duplicate removal is expressed as patches on the field
`dup_of` (old = missing); the clean table keeps one record per cluster and the raw table stays beside it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ..core import Patch, PatchSet, missing
from . import geo, link as L

FIELDS = ["id", "dist", "day", "size", "name"]


def self_pairs(df: pd.DataFrame, radius_km=3.0, day_window=3.0) -> pd.DataFrame:
    ok = np.flatnonzero((np.isfinite(df.lat) & np.isfinite(df.lon)).to_numpy())
    t = cKDTree(geo.xyz(df.lat.to_numpy()[ok], df.lon.to_numpy()[ok]))
    pr = t.query_pairs(geo.km_to_chord(radius_km), output_type="ndarray")
    a, b = ok[pr[:, 0]], ok[pr[:, 1]]
    d = df.day.to_numpy()
    dd = np.abs(d[a] - d[b])
    keep = np.isnan(dd) | (dd <= day_window)
    return pd.DataFrame({"li": a[keep], "ri": b[keep]})


def find(df: pd.DataFrame, model: L.FSModel | None = None, radius_km=3.0, day_window=3.0, hi=0.97, lo=0.05, fit_mask=None,
         cross_source_only=False):
    """Returns (pairs with posterior and outcome, model). df needs ident, name, day, lat, lon, acres."""
    df = df.reset_index(drop=True)
    pairs = self_pairs(df, radius_km, day_window)
    if cross_source_only:
        s = df["source"].to_numpy(dtype=object)
        pairs = pairs[s[pairs.li.to_numpy()] != s[pairs.ri.to_numpy()]].reset_index(drop=True)
    fields = [f for f in FIELDS if not (f == "id" and df["ident"].notna().sum() == 0)]
    X = L.compare(df, df, pairs, fields)
    if model is None:
        sel = np.ones(len(pairs), bool) if fit_mask is None else fit_mask[pairs.li.to_numpy()]
        model = L.fit_fs(X[sel], fields, init_prior=0.02)
    p = pairs.copy()
    p["post"] = model.posterior(X)
    p["outcome"] = np.where(p.post >= hi, "link", np.where(p.post > lo, "undecided", "no_link"))
    return p, model


def clusters(n: int, links: pd.DataFrame) -> np.ndarray:
    """Connected components over linked pairs (union-find)."""
    parent = np.arange(n)
    def find_(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in zip(links.li.to_numpy(), links.ri.to_numpy()):
        ra, rb = find_(a), find_(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    return np.array([find_(i) for i in range(n)])


def keeper_order(df: pd.DataFrame) -> pd.Series:
    """Lower is better: more complete record first (has name, acres, id), then earliest row."""
    score = df.name.notna().astype(int) + df.acres.notna().astype(int) + df.ident.notna().astype(int)
    return (-score).astype(float) + np.arange(len(df)) * 1e-9


def dedupe_patches(df: pd.DataFrame, pairs: pd.DataFrame, rule="dup:fs_link", cross_source_only: bool = False) -> tuple[list[Patch], np.ndarray]:
    df = df.reset_index(drop=True)
    lk = pairs[pairs.outcome == "link"]
    comp = clusters(len(df), lk)
    order = keeper_order(df).to_numpy()
    best = pd.Series(order).groupby(comp).idxmin()
    keeper = best.reindex(comp).to_numpy().copy()
    patches = []
    prob = {}
    for a, b, p in zip(lk.li, lk.ri, lk.post):
        prob[a] = max(prob.get(a, 0), p); prob[b] = max(prob.get(b, 0), p)
    src = df["source"].to_numpy(dtype=object) if "source" in df else None
    for i in np.flatnonzero(keeper != np.arange(len(df))):
        k = keeper[i]
        if cross_source_only and src is not None and src[i] == src[k]:
            keeper[i] = i
            continue        # chained through a third record: same-source records are separate fires
        patches.append(Patch(df.rid.iloc[i], "dup_of", missing(), df.rid.iloc[k], rule,
                             {"posterior_best_link": round(float(prob.get(i, 0.0)), 4), "cluster_size": int((comp == comp[i]).sum())}, float(prob.get(i, 0.95))))
    return patches, keeper

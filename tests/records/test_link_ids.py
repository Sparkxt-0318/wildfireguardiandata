import pytest

pytest.importorskip("scipy")
import numpy as np
import pandas as pd

from firewitness.records import dedupe, ids, link as L


def synth(n=400, seed=0):
    rng = np.random.default_rng(seed)
    lat = rng.uniform(35, 45, n); lon = rng.uniform(-120, -100, n); day = rng.integers(14000, 14300, n).astype(float)
    ac = 10 ** rng.uniform(0, 4, n)
    names = [f"FIRE{rng.integers(0, 10**6)}" for _ in range(n)]
    left = pd.DataFrame({"lat": lat, "lon": lon, "day": day, "acres": ac, "name": names, "state": "XX", "ident": None})
    right = left.copy()
    right["lat"] += rng.normal(0, 0.003, n); right["lon"] += rng.normal(0, 0.003, n)
    right["day"] += rng.integers(-1, 2, n); right["acres"] *= rng.uniform(0.9, 1.1, n)
    return left, right


def test_fs_links_true_pairs_without_labels():
    left, right = synth()
    pairs = L.candidate_pairs(left, right, 5.0, 3.0)
    X = L.compare(left, right, pairs, ["dist", "day", "size", "name", "state"])
    m = L.fit_fs(X, ["dist", "day", "size", "name", "state"], init_prior=0.2)
    dec = L.decide(pairs, m.posterior(X))
    lk = dec[dec.outcome == "link"]
    assert (lk.li == lk.ri).mean() > 0.98 and len(lk) > 300


def test_numbered_siblings_are_not_the_same_fire():
    assert L.name_sim("BEAR BASIN 2", "BEAR BASIN 3") == 0.0
    assert L.name_sim("BEAR BASIN FIRE", "BEAR BASIN") == 1.0


def test_dedupe_keeps_distinct_close_fires_and_removes_copy():
    df = pd.DataFrame({"rid": list("abcd"), "ident": [None] * 4, "name": ["ALPHA", "ALPHA", "BEAR 1", "BEAR 2"],
                       "day": [100., 100., 200., 200.], "lat": [40, 40.001, 41, 41.001], "lon": [-100, -100.001, -101, -101.001],
                       "acres": [50, 52, 3, 3], "source": ["s1", "s2", "s1", "s2"]})
    pairs, m = dedupe.find(df, model=L.FSModel(["dist", "day", "size", "name"], [np.array([.8, .15, .05, 0, 0]), np.array([.9, .1, 0, 0, 0]), np.array([.7, .2, .05, .05]), np.array([.7, .15, .1, .05])],
                                              [np.array([.05, .2, .5, .25, 0]), np.array([.3, .3, .4, 0, 0]), np.array([.2, .2, .3, .3]), np.array([.05, .05, .2, .7])], 0.2))
    pt, keeper = dedupe.dedupe_patches(df, pairs)
    assert [p.record_id for p in pt] == ["b"]


def test_ids_deterministic_and_order_free():
    f = pd.DataFrame({"key": ["a", "b", "c"], "day": [14000., 14000., 14001.], "lat": [40.01, 40.02, 40.0], "lon": [-120.01, -120.02, -120.0], "acres": [5., 50., 1.]})
    a = ids.assign_ids(f)
    b = ids.assign_ids(f.sample(frac=1, random_state=3)).sort_index()
    assert (a.perm_id == b.perm_id).all() and a.perm_id.is_unique
    assert a.perm_id.iloc[1].endswith("-01")

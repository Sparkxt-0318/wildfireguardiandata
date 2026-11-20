"""Planted cheats must lose (gates N1-N5 on a small synthetic benchmark with known truth)."""
import pytest

from firewitness.score import gates, models, negatives, splits


@pytest.fixture(scope="module")
def setup(ds):
    sp = splits.make(ds, "space")
    spr = splits.make(ds, "random_rows")
    tab = negatives.sample(ds, sp["folds"]["train"], k=3)
    honest = models.Logistic("wx+prox", prox=True).fit(ds, tab["table"], tab["fires"]).predict(ds, gates._fires(sp))
    return sp, spr, honest


def test_n1_memoriser_loses_under_blocked_splits(ds, setup):
    sp, spr, _ = setup
    r = gates.gate_n1(ds, sp, spr)
    assert r["passed"]
    assert r["inflation_ratio_random_over_blocked_f1"] > 1.5


def test_n2_flag_everything_loses(ds, setup):
    r = gates.gate_n2(ds, setup[0])
    assert r["passed"] and r["area_ratio"] > 3


def test_n3_leaks_are_caught_and_honest_model_is_not(ds, setup):
    sp, _, honest = setup
    r = gates.gate_n3(ds, sp, honest)
    assert r["passed"], r


def test_n4_card_is_order_independent(ds, setup):
    sp, _, honest = setup
    r = gates.gate_n4(ds, sp, honest)
    assert r["passed"], r


def test_n5_matched_sampler_vs_random(ds, setup):
    sp, _, _ = setup
    r = gates.gate_n5(ds, sp)
    m = r["matched"]["fixed_0.5"]["area_ratio_top_danger"]
    rr = r["random"]["fixed_0.5"]["area_ratio_top_danger"]
    assert m is not None and rr is not None
    assert m < rr           # direction of the effect; the pre-registered absolute limit is reported in results/

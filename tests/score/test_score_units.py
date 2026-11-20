import copy
import json

import numpy as np
import pytest

from firewitness.score import contract, negatives, splits
from firewitness.score.dataset import FIRE, NO_FIRE, UNKNOWN
from firewitness.score.geo import utm_to_latlon


def test_utm_inverse_known_point():
    # UTM 10N 500000 E, 4649776 N is lat 42.0, lon -123.0 (central meridian)
    lat, lon = utm_to_latlon(500000, 4649776.2, 10)
    assert abs(lat - 42.0) < 1e-4 and abs(lon + 123.0) < 1e-6


def test_split_is_by_fire_buffered_and_hash_protected(ds, tmp_path):
    sp = splits.make(ds, "space")
    f = sp["folds"]
    assert not (set(f["train"]) & set(f["val"]) or set(f["train"]) & set(f["test"]) or set(f["val"]) & set(f["test"]))
    assert f["test"] and f["val"] and f["train"]
    assert all(d["reason"] == "buffer" for d in sp["dropped"])
    p = tmp_path / "s.json"
    splits.write(sp, str(p))
    assert splits.load(str(p))["sha256"] == sp["sha256"]
    d = json.load(open(p)); d["folds"]["test"] = d["folds"]["test"][:-1]
    json.dump(d, open(p, "w"))
    with pytest.raises(ValueError):
        splits.load(str(p))


def test_split_independent_of_scene_order(ds):
    from firewitness.score.dataset import Dataset
    import random
    ids = sorted(ds.scenes); random.Random(1).shuffle(ids)
    ds2 = Dataset(ds.name, {k: ds.scenes[k] for k in ids}, ds.cell_km, ds.meta)
    assert splits.make(ds, "space")["sha256"] == splits.make(ds2, "space")["sha256"]


def test_negatives_only_verified_no_fire_matched_and_reproducible(ds):
    sp = splits.make(ds, "space")
    ids = sp["folds"]["train"]
    a = negatives.sample(ds, ids, k=3)
    b = negatives.sample(ds, ids, k=3)
    for k in a["table"]:
        assert np.array_equal(a["table"][k], b["table"][k])
    t = a["table"]
    neg = t["label"] == 0
    states = np.array([ds.scenes[ids[f]].state[tt, y, x] for f, tt, y, x in zip(t["fire"][neg][:5000], t["t"][neg][:5000], t["y"][neg][:5000], t["x"][neg][:5000])])
    assert (states == NO_FIRE).all()                      # never unknown, never fire
    pos = t["label"] == 1
    assert a["stats"]["hard_share_of_negatives"] >= 0.24
    # matched on danger class: negatives follow the positives' danger distribution much more closely than random ones
    r = negatives.sample(ds, ids, k=3, matched=False)
    def gap(res):
        tb = res["table"]
        pd_ = np.bincount(tb["danger"][tb["label"] == 1], minlength=5) / (tb["label"] == 1).sum()
        nd_ = np.bincount(tb["danger"][tb["label"] == 0], minlength=5) / (tb["label"] == 0).sum()
        return np.abs(pd_ - nd_).sum()
    assert gap(a) < gap(r)


def test_contract_refuses_test_fitted_threshold():
    c = copy.deepcopy(contract.TEMPLATE)
    c["threshold"]["rule"] = "max_f1_on_test"
    with pytest.raises(contract.ContractError):
        contract.validate(c)
    c["threshold"] = {"rule": "fixed", "value": None}
    with pytest.raises(contract.ContractError):
        contract.validate(c)


def test_card_refuses_edited_or_row_level_split(ds):
    from firewitness.score import baselines, card
    sp = splits.make(ds, "random_rows")
    with pytest.raises(ValueError):
        card.build_card(ds, sp, baselines.persistence(ds, ds.ids()), contract.validate(copy.deepcopy(contract.TEMPLATE)), "x")

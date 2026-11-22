# Reproduce SCORE_RESULTS live-adapter numbers using the repo's own code (firewitness.score) on released live-v0.1 files.
import sys, json
import numpy as np
from firewitness.score.adapters import live
from firewitness.score import splits, negatives
R = sys.argv[1]
ds = live.read_onset(f"{R}/onset_labels.csv", f"{R}/live_fires.csv")
ids = ds.ids()
print("fires", len(ids), "real intervals", sum(1 for f in ids if not ds.scenes[f].meta["record_only"]))
tot = {"fire": 0, "no_fire": 0, "unknown": 0, "cells": 0}
for f in ids:
    st = ds.scenes[f].state
    for k, v in (("fire", 1), ("no_fire", 0), ("unknown", -1)):
        pass
sp = splits.make(ds, "space", seed=54)
print("split", {k: len(v) for k, v in sp["folds"].items()}, "dropped", len(sp["dropped"]))
res = negatives.sample(ds, sp["folds"]["train"], seed=54)
print(json.dumps(res["stats"], default=str)[:800])

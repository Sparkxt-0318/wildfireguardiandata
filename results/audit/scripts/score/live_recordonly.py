# Record-only live adapter (protocol/live_fires.csv anchors = discovery_t), repo code, released live_fires.csv.
import sys, json
from firewitness.score.adapters import live
from firewitness.score import splits, negatives
R = sys.argv[1]
ds = live.read_csv(f"{R}/live_fires.csv")
print("summary", ds.summary())
sp = splits.make(ds, "space", seed=54)
print("split", {k: len(v) for k, v in sp["folds"].items()}, "dropped", len(sp["dropped"]))
st = negatives.sample(ds, sp["folds"]["train"], seed=54)["stats"]
print("pos", st["positives"], "neg", st["negatives"], st["match_level_share"], st["hard_share_of_negatives"])

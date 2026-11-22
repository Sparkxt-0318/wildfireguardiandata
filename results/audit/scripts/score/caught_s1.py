# Reproduce SCORE_RESULTS caught-S1 addition with repo code on the CA subset of released caught_states_v0.1_2020.parquet.
import sys, json, time
import geopandas as gpd, pandas as pd
from firewitness.score.adapters import caught, live
from firewitness.score import splits, negatives
C, L = sys.argv[1], sys.argv[2]
t = time.time()
lab = pd.read_parquet(f"{C}/caught_labels_v0.1_2020.parquet", columns=["rid", "STATE", "tier"])
ca = set(lab[lab.STATE == "CA"].rid)
g = gpd.read_parquet(f"{C}/caught_states_v0.1_2020.parquet")
g = g[g.rid.isin(ca)]
print("rows", len(g), g.state.value_counts().to_dict())
ds = caught.from_rows(g.to_dict("records"))
print("summary", ds.summary(), round(time.time() - t), "s")
import numpy as np
cells = [ds.scenes[f].cell_km for f in ds.ids()] if hasattr(ds.scenes[ds.ids()[0]], "cell_km") else None
if cells: print("median cell km", float(np.median(cells)))
sp = splits.make(ds, "space", seed=54)
print("split", {k: len(v) for k, v in sp["folds"].items()}, "dropped", len(sp["dropped"]))
res = negatives.sample(ds, sp["folds"]["train"], seed=54)
print(json.dumps(res["stats"], default=str)[:900])
# live dataset total
dl = live.read_onset(f"{L}/onset_labels.csv", f"{L}/live_fires.csv"); print("live summary", dl.summary())
# exact match-level shares (unrounded)
tb = res["table"]; neg = tb["label"] == 0
import collections
cnt = collections.Counter(tb["level"][neg].tolist()); tot = int(neg.sum())
print("level counts", {k: (v, v / tot) for k, v in sorted(cnt.items())}, "hard exact", float(tb["hard"][neg].mean()))

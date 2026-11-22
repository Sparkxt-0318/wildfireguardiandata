# Floor rule check on extent-sized cells (cell_from_floor=False), repo code, released CA 2020 states.
import sys
import numpy as np, geopandas as gpd, pandas as pd
from firewitness.score.adapters import caught
C = sys.argv[1]
lab = pd.read_parquet(f"{C}/caught_labels_v0.1_2020.parquet", columns=["rid", "STATE"])
g = gpd.read_parquet(f"{C}/caught_states_v0.1_2020.parquet"); g = g[g.rid.isin(set(lab[lab.STATE == "CA"].rid))]
ds = caught.from_rows(g.to_dict("records"), cell_from_floor=False)
nf = ok = 0
for f in ds.ids():
    s = ds.scenes[f]
    st = s.state  # (T, Y, X) with -1 unknown, 0 no_fire, 1 fire ?
    m = (st == 1)  # 0 unknown, 1 verified no fire, 2 fire (dataset.py)
    nf += int(m.sum())
    if "floor_m2" in s.static:
        fo = s.static["floor_m2"] <= (s.cell_km * 1000.0) ** 2
        ok += int((m & fo[None]).sum()) if fo.ndim == 2 else int((m & fo).sum())
print("summary", ds.summary(), "no_fire cell-days", nf, "passing floor rule", ok)

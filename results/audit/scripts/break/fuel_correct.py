"""Break-it: give the fuel agent a map built to agree with the independent layers ("a correct map") and see what it says.
Same area as the quick start (lon/lat box, LF2016 grid M16). The map is constructed per cell from NLCD, canopy and
WorldCover with the protocol's own groups; nothing is fitted."""
import numpy as np, json
from firewitness.fuel import runner, agent
from firewitness.fuel.layers import load
cfg = runner.region_cfg()
L = load(runner.area_dir("BOX_m115p2_40p4_m114p8_40p7"), "M16", cfg)
G = cfg["groups"]; nl = cfg["nlcd"]; c = cfg["rules"]["consistent"]
print("groups", {k: v[:3] for k, v in G.items()})
S, n, _ = agent.tree_evidence(L, cfg)
lc = L.lc
orig = agent.check(L, cfg)
m = np.full(lc.shape, G["GR"][0], np.int16)                     # default grass
m[lc == 52] = G["SH"][0]
tim = list(G.get("TU", [])) + list(G.get("TL", []))
m[(S >= c["timber_S_min"]) & (n >= c["min_n"])] = (G["TU"] if "TU" in G else G["TL"])[0]
m[np.isin(lc, nl["water"])] = 98; m[np.isin(lc, nl["snow"])] = 92
m[np.isin(lc, nl["dev_any"])] = 91; m[np.isin(lc, nl["crop"])] = 93; m[lc == 31] = 99
m[L.fbfm <= 0] = L.fbfm[L.fbfm <= 0]                              # keep nodata where the map had none
L.fbfm = m
res = agent.check(L, cfg)
names = agent.VERDICT_NAMES
def counts(r): return {names[k]: int((r.verdict == k).sum()) for k in (1, 2, 3, 4)}
rc = {r: int(((res.rules >> b) & 1).sum()) for r, b in agent.RULE_BITS.items() if ((res.rules >> b) & 1).any()}
print(json.dumps({"original_LF2016": counts(orig), "constructed_correct_map": counts(res), "rules_firing_on_correct_map": rc}, indent=1))

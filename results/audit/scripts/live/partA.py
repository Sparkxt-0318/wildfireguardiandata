import sys, math, json
import numpy as np, pandas as pd
R = sys.argv[1]
def wilson(k, n, z=1.96):
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d
    w = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return p, max(0, c-w), min(1, c+w)
def boot_median(x, n=2000, seed=0):  # same scheme as firewitness/live/pipeline.boot_median (reimplemented)
    x = np.asarray([v for v in x if v is not None and not (isinstance(v,float) and math.isnan(v))], float)
    rng = np.random.default_rng(seed)
    meds = np.median(x[rng.integers(0, len(x), (n, len(x)))], 1)
    return float(np.median(x)), float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))
L = pd.read_csv(f"{R}/onset_labels.csv")
F = pd.read_csv(f"{R}/live_fires.csv")
print("rows", len(L), "unique ids", L.fire_id.nunique(), "fires list", len(F), F.fire_id.nunique())
print("split counts", F.split.value_counts().to_dict(), "class x split\n", pd.crosstab(F.size_class, F.split))
L["has"] = L.onset_utc.notna()
for nm, sub in [("all", L), ("dev", L[L.split=="dev"]), ("test", L[L.split=="test"])]:
    k, n = int(sub.has.sum()), len(sub)
    print(nm, n, k, ["%.4f" % v for v in wilson(k, n)])
print("by class all:", L.groupby("size_class").has.agg(["sum","count"]).to_dict())
O = L[L.has]
for col in ["lead_vs_T0_min","lead_vs_fdc_min","lead_vs_polar_min","lead_vs_discovery_min"]:
    x = O[col].dropna()
    print(col, "n", len(x), "boot seed0", ["%.2f" % v for v in boot_median(x.tolist())],
          "n_positive", int((x>0).sum()))
    # seed sensitivity
    meds = [boot_median(x.tolist(), seed=s)[1:] for s in range(1, 6)]
    print("   other seeds", [("%.1f" % a, "%.1f" % b) for a, b in meds])
print("label kinds\n", L.label_kind.value_counts())
# G18 coverage
print("sats", L.sats.value_counts().to_dict())
# E2
e = L[L.e2_agree.notna()]
print("E2 all", len(e), int(e.e2_agree.astype(str).eq("True").sum()), boot_median(e.e2_abs_diff_min.tolist()))
k = int(e.e2_agree.astype(str).eq("True").sum()); print("  wilson", wilson(k, len(e)))
for sp in ["dev","test"]:
    ee = e[e.split==sp]; kk = int(ee.e2_agree.astype(str).eq("True").sum())
    print("E2", sp, len(ee), kk, boot_median(ee.e2_abs_diff_min.tolist()) if len(ee) else None)
# long leads > 3h
lg = O[O.lead_vs_T0_min > 180][["fire_id","name","lead_vs_T0_min","split"]]
print("long leads vs T0 > 180 min:\n", lg)
print("Siphon/Rough Rock:\n", L[L.fire_id.isin(["2024-AZTNF-001687","2025-OKOMA-000395"])][["fire_id","name","label_kind","lead_vs_T0_min","lead_vs_fdc_min"]])
# dev no-onset fires count
print("no onset overall", int((~L.has).sum()))
# traceback per sat
T = pd.read_csv(f"{R}/traceback_by_satellite.csv")
print("tb rows", len(T), T.sat.value_counts().to_dict(), "fires with G18", T[T.sat=="G18"].fire_id.nunique())
print("h_A", T.groupby("sat").h_A.unique().to_dict())
Tm = T.merge(F[["fire_id","split"]], on="fire_id")
print("onset by sat x split\n", pd.crosstab([Tm.sat, Tm.split], Tm.onset))
# long-lead counts by reference
for col in ["lead_vs_T0_min","lead_vs_fdc_min","lead_vs_polar_min","lead_vs_discovery_min"]:
    print("leads > 180 min", col, int((O[col] > 180).sum()))

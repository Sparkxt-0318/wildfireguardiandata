import sys, math, json, tarfile, os
import numpy as np, pandas as pd
R = sys.argv[1]
def wilson(k, n, z=1.96):
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d
    w = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return p, max(0, c-w), min(1, c+w)
def boot_median(x, n=2000, seed=0):
    x = np.asarray(x, float); rng = np.random.default_rng(seed)
    meds = np.median(x[rng.integers(0, len(x), (n, len(x)))], 1)
    return float(np.median(x)), float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))
def lead(v):
    if pd.isna(v): return None
    if v == "-inf": return -math.inf
    if v == "+inf": return math.inf
    return float(v)
def stats(df, seed=0):
    L = [lead(v) for v in df.lead_min.astype(object)]
    L = [v for v in L if v is not None]
    n = len(L); e = sum(v > 0 for v in L)
    med = boot_median([max(min(v, 1e6), -1e6) for v in L], seed=seed)
    clipped = np.mean([max(min(v, 240), -120) for v in L]) if n else None
    return dict(n=n, earlier=e, share=wilson(e, n) if n else None, med=med,
                no_alert=sum(v == -math.inf for v in L), no_op=sum(v == math.inf for v in L), clipped_mean=clipped)
F = pd.read_csv(f"{R}/live_fires.csv")
for nm in ["replay_test.csv", "replay_dev.csv"]:
    D = pd.read_csv(f"{R}/{nm}", dtype={"lead_min": object})
    print(nm, "rows", len(D), "unique", D.fire_id.nunique())
    s = stats(D); print(" overall", s)
    for seed in (1, 2, 3):
        print("   seed", seed, "median CI", stats(D, seed)["med"])
    for c, g in D.groupby("size_class"):
        print("  class", c, stats(g))
    # check consistency of alert/op/lead
    bad = 0
    for _, r in D.iterrows():
        a = pd.to_datetime(r.alert_utc) if pd.notna(r.alert_utc) else None
        o = pd.to_datetime(r.operational_utc) if pd.notna(r.operational_utc) else None
        lv = lead(r.lead_min)
        if a is not None and o is not None:
            if lv is None or abs((o - a).total_seconds()/60 - lv) > 0.11: bad += 1
        elif a is None and o is not None and lv != -math.inf: bad += 1
        elif a is not None and o is None and lv != math.inf: bad += 1
        elif a is None and o is None and lv is not None: bad += 1
    print("  rows inconsistent lead vs times:", bad)
    if nm == "replay_test.csv":
        print("  split check: all test?", set(F.set_index("fire_id").loc[D.fire_id, "split"]))
        print("  earlier fires:", D[[lead(v) is not None and lead(v) > 0 for v in D.lead_min]][["fire_id","size_class","lead_min"]].to_string())
J = json.load(open(f"{R}/replay_test.json"))
print("json stats", J["stats"]); print("json false", J["false_rate_at_h_this_split_clustered"], J["false_rate_at_h_this_split_per_pixel"])
print("51/483771 =", 51/483771.0729166665, "453/483771 =", 453/483771.0729166665, "x1.05e6 =", 1.05e6*51/483771.07)
print("1e-2 budget x1.05e6 =", 1.05e6*0.00897531961516836)
# supplement
L = pd.read_csv(f"{R}/supplement_caught_onset_labels.csv"); Fs = pd.read_csv(f"{R}/supplement_caught_fires.csv")
print("supp rows", len(L), Fs.size_group.value_counts().to_dict(), "sats", L.sats.value_counts().to_dict())
O = L[L.onset_utc.notna()]
print("supp onsets", len(O), wilson(len(O), len(L)), "lead T0", O.lead_vs_T0_min.tolist(), boot_median(O.lead_vs_T0_min.tolist()))
print("label kinds", O.label_kind.tolist(), "E2", L.e2_agree.dropna().tolist(), "discovery precision", L.discovery.str[11:].value_counts().head(3).to_dict())
# export
tf = tarfile.open(f"{R}/live_export_v0.1.tar.gz")
dirs = sorted({m.name.split("/")[1] for m in tf.getmembers() if m.name.count("/") >= 1 and m.name.split("/")[1]})
print("export fires", len(dirs), dirs)
Fd = pd.to_datetime(F.discovery_t, unit="s"); print("discovery range", Fd.min(), Fd.max())

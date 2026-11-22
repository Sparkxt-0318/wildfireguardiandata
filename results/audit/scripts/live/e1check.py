import sys, math, pandas as pd
R = sys.argv[1]
def wilson(k, n, z=1.96):
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d
    w = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return round(p,5), round(max(0, c-w),5), round(min(1, c+w),5)
T = pd.read_csv(f"{R}/traceback_by_satellite.csv").merge(pd.read_csv(f"{R}/live_fires.csv")[["fire_id","split"]], on="fire_id")
# onset <=> S_pre >= h_A in the released table?
print("onset==(S_pre>=h_A):", ((T.S_pre >= T.h_A) == T.onset).all())
for sat in ["G16","G18"]:
    t = T[(T.sat==sat)&(T.split=="test")].S_pre.sort_values(ascending=False)
    print(sat, "test n", len(t), "top S_pre", t.head(8).round(2).tolist())
    for h in ([35.52, 38.83] if sat=="G16" else [31.28, 30.19]):
        print("   h", h, "count", int((t>=h).sum()))
# Wilson arithmetic on published counts (counts themselves need placebo files not released)
for k, n in [(61,8900),(55,4882),(19,120),(6,64),(94,9058),(15,120),(61,5861),(12,76)]:
    print(k, n, wilson(k, n))
print("expected false onsets 1% x traces:", 0.01*len(T), "x traces w/o onset", 0.01*(~T.onset).sum())

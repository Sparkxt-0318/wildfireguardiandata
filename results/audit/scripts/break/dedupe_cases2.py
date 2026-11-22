"""Variant: background where 2 % of records have a planted cross-source duplicate, and all records carry names."""
import sys, numpy as np, pandas as pd
sys.argv += []
exec(open(sys.argv[2]).read().split("cs = pd.DataFrame")[0])   # reuse bg and cases
names = np.array(["OAK","PINE","ELM","ASH","FIR","BIRCH","MAPLE","ALDER","SAGE","CREEK","RIDGE","CANYON","MESA","PEAK","HOLLOW","SPRING"])
bg["name"] = rng.choice(names, len(bg)) + " " + rng.integers(1,500,len(bg)).astype(str)
k = int(0.02*len(bg)); pick = rng.choice(len(bg), k, replace=False)
dup = bg.iloc[pick].copy()
ang = rng.uniform(0,2*np.pi,k); r = rng.uniform(0,1.5,k)
dup["lat"] = dup.lat + r*np.cos(ang)/111.0; dup["lon"] = dup.lon + r*np.sin(ang)/(111.0*np.cos(np.radians(dup.lat)))
dup["day"] = dup.day + rng.integers(0,2,k); dup["source"] = "COPYSRC"; dup["rid"] = "dup:" + dup.rid
bg = pd.concat([bg, dup], ignore_index=True)
cs = pd.DataFrame(cases, columns=["rid","name","day","lat","lon","acres","source"]); cs["ident"]=None
df = pd.concat([bg[cs.columns], cs], ignore_index=True)
pairs, model = dedupe.find(df, cross_source_only=True)
patches, keeper = dedupe.dedupe_patches(df, pairs, cross_source_only=True)
rid = df.rid.to_numpy(); idx = {r:i for i,r in enumerate(rid)}
pl = pairs.copy(); pl["a"]=rid[pl.li]; pl["b"]=rid[pl.ri]
planted = pl[(pl.a.str.replace("dup:","")==pl.b.str.replace("dup:",""))]
print("planted dup pairs", k, "found as link", (planted.outcome=="link").sum(), "undecided", (planted.outcome=="undecided").sum())
other = pl[~pl.index.isin(planted.index) & ~pl.a.str.match(r"^[cde]\d") & ~pl.b.str.match(r"^[cde]\d")]
print("other background pairs", len(other), "linked", (other.outcome=="link").sum())
for a,b in [("c1a","c1b"),("c2a","c2b"),("c3a","c3b"),("d1a","d1b"),("d2a","d2b"),("e1a","e1b")]:
    i,j = idx[a], idx[b]
    m = pairs[((pairs.li==i)&(pairs.ri==j))|((pairs.li==j)&(pairs.ri==i))]
    if len(m)==0: print(a,b,"not a candidate pair (outside 3 km / 3 days)", "merged:", keeper[i]==keeper[j])
    else: print(a,b,"post=%.4f outcome=%s merged=%s"%(m.post.iloc[0], m.outcome.iloc[0], keeper[i]==keeper[j]))

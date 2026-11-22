"""Break-it cases for duplicates, through the library API (the CLI `records clean` does not run tool 3)."""
import sys, numpy as np, pandas as pd
from firewitness.records import dedupe, geo
REL = sys.argv[1]
f = pd.read_parquet(REL, columns=["fid","day","lat","lon","acres","state","year"])
bg = f[(f.state=="CA") & (f.year==2018)].copy().reset_index(drop=True)
rng = np.random.default_rng(1)
bg["source"] = rng.choice(["FS","BLM","ST","NPS","FWS"], len(bg))
bg["name"] = None; bg["ident"] = None; bg["rid"] = "bg:" + bg.fid.astype(str)
def km_off(lat, lon, km_n, km_e):
    return lat + km_n/111.0, lon + km_e/(111.0*np.cos(np.radians(lat)))
base_lat, base_lon, d0 = 36.20, -118.90, float(bg.day.median())
cases = []
# c) two different fires, same day, a few km apart (2.5 km and 4 km), different names and sizes, different sources
la, lo = km_off(base_lat, base_lon, 0, 2.5); cases += [("c1a","MILL",d0,base_lat,base_lon,15.0,"FS"),("c1b","CEDAR",d0,la,lo,0.5,"ST")]
la, lo = km_off(base_lat+0.5, base_lon, 0, 4.0); cases += [("c2a","ROCK",d0,base_lat+0.5,base_lon,3.0,"FS"),("c2b","DOVE",d0,la,lo,40.0,"ST")]
# c') same day, 2.5 km, NO names (most FPA FOD small fires), similar small size
la, lo = km_off(base_lat+1.0, base_lon, 0, 2.5); cases += [("c3a",None,d0,base_lat+1.0,base_lon,0.1,"FS"),("c3b",None,d0,la,lo,0.1,"ST")]
# d) one fire reported twice, 2 km and 12 h apart, same name and size, two sources
la, lo = km_off(base_lat+1.5, base_lon, 2.0, 0); cases += [("d1a","BEAR",d0,base_lat+1.5,base_lon,120.0,"FS"),("d1b","BEAR",d0+0.5,la,lo,120.0,"ST")]
# d') same, but no name and sizes 120 vs 100
la, lo = km_off(base_lat+2.0, base_lon, 2.0, 0); cases += [("d2a",None,d0,base_lat+2.0,base_lon,120.0,"FS"),("d2b",None,d0+0.5,la,lo,100.0,"ST")]
# e) a source that copies another exactly: identical record in a second source
cases += [("e1a","WILLOW",d0,base_lat+2.5,base_lon,8.0,"FS"),("e1b","WILLOW",d0,base_lat+2.5,base_lon,8.0,"COPY")]
cs = pd.DataFrame(cases, columns=["rid","name","day","lat","lon","acres","source"]); cs["ident"]=None
df = pd.concat([bg[cs.columns], cs], ignore_index=True)
pairs, model = dedupe.find(df, cross_source_only=True)
patches, keeper = dedupe.dedupe_patches(df, pairs, cross_source_only=True)
rid = df.rid.to_numpy()
idx = {r:i for i,r in enumerate(rid)}
print("background records", len(bg), "cross-source candidate pairs", len(pairs), "links", (pairs.outcome=="link").sum(), "undecided", (pairs.outcome=="undecided").sum())
for a,b in [("c1a","c1b"),("c2a","c2b"),("c3a","c3b"),("d1a","d1b"),("d2a","d2b"),("e1a","e1b")]:
    i,j = idx[a], idx[b]
    m = pairs[((pairs.li==i)&(pairs.ri==j))|((pairs.li==j)&(pairs.ri==i))]
    km = geo.haversine_km(df.lat[i],df.lon[i],df.lat[j],df.lon[j]) if hasattr(geo,"haversine_km") else float("nan")
    if len(m)==0: print(a,b,"not a candidate pair (outside 3 km / 3 days)", "merged:", keeper[i]==keeper[j])
    else: print(a,b,"post=%.4f outcome=%s merged=%s"%(m.post.iloc[0], m.outcome.iloc[0], keeper[i]==keeper[j]))

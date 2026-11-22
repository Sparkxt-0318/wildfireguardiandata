# Disc-vertex check on label geometries and placebo/three-state check on states files.
import sys, pyarrow.parquet as pq, pandas as pd, numpy as np, shapely
from pyproj import Geod
D=sys.argv[1]; g=Geod(ellps='WGS84'); rng=np.random.default_rng(0)
nv=[]; ratios=[]
for y in (2018,2019,2020):
    t=pq.read_table(D+f'caught_labels_v0.1_{y}.parquet', columns=['rid','tier','pixel_label','r_m','geometry']).to_pandas()
    t=t[~t.pixel_label]
    geoms=shapely.from_wkb(t.geometry.values)
    nv.append(pd.Series(shapely.get_num_coordinates(geoms)-1).value_counts())
    idx=rng.choice(len(t), 1500, replace=False)
    for i in idx:
        a=abs(g.geometry_area_perimeter(geoms[i])[0]); r=t.r_m.iloc[i]
        ratios.append(a/(np.pi*r*r))
print('vertex counts (closed ring minus 1) of non-pixel-label geometries:', pd.concat(nv).groupby(level=0).sum().to_dict())
ratios=np.array(ratios); print('area/(pi r^2): median %.5f, p1 %.5f, p99 %.5f -> %.2f %% less'%(np.median(ratios),np.percentile(ratios,1),np.percentile(ratios,99),100*(1-np.median(ratios))))
print('regular 16-gon theoretical: %.4f %% less'%(100*(1-16/(2*np.pi)*np.sin(2*np.pi/16))))
# states
rids=set()
for y in (2018,2019,2020):
    rids|=set(pq.read_table(D+f'caught_labels_v0.1_{y}.parquet', columns=['rid']).column(0).to_pylist())
for y in (2018,2019,2020):
    s=pq.read_table(D+f'caught_states_v0.1_{y}.parquet', columns=['rid','tier','std_label','state','floor_m2']).to_pandas()
    print(y, len(s), 'states', s.state.value_counts().to_dict(), 'tiers', s.tier.value_counts().to_dict(),
          'unique rid', s.rid.nunique(), 'rid not in labels', len(set(s.rid)-rids), 'rid prefixes', s.rid.str[:3].value_counts().to_dict(),
          'dup (rid,state)', int(s.duplicated(['rid','state']).sum()))

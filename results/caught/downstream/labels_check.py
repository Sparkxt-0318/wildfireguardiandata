import sys, math, json
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
from shapely import wkt
from rasterio.features import rasterize
from rasterio.transform import Affine
from scipy import ndimage
sys.dont_write_bytecode = True
K = Path('/home/user/sparkxt-0318/wildfireguardian/research/kcf-margin'); sys.path.insert(0, str(K))
from reach import CELL_KM, NEVER, component_reach, dist_km, conformal_R, clopper_pearson
from calibrate import lofo, summarise_lofo, by_fire
S = Path(sys.argv[1]); W = S/'work'
PAD = 16  # cells (6 km) so labels within 5 km of K_t fit
lab = pd.read_csv('/home/user/wildfireguardiandata/results/caught/verified_S1.csv')
g = gpd.GeoDataFrame(lab, geometry=lab.geometry_wkt.map(wkt.loads), crs=4326).to_crs(3310)
LA = 'America/Los_Angeles'
g['L0'] = [pd.Timestamp(d).tz_localize(LA).tz_convert('UTC').tz_localize(None) for d in g.label_t0]
g['L1'] = [(pd.Timestamp(d)+pd.Timedelta(days=1)).tz_localize(LA, ambiguous=False, nonexistent='shift_forward').tz_convert('UTC').tz_localize(None) for d in g.label_t1]
base = pd.read_csv(W/'gofer_reach.csv.gz')
rows = []; touched = set(); touched_time = set(); allrows = []
for f in sorted(base.fire.unique()):
    z = np.load(W/'gofer_arrival'/f'{f}.npz'); A = z['A']; tf = z['transform']; t0 = pd.Timestamp(str(z['t0'])).tz_localize(None)
    A = np.pad(A, PAD, constant_values=NEVER)
    x0, y1 = tf[2], tf[5]; tfn = Affine(CELL_KM*1000, 0, x0-PAD*CELL_KM*1000, 0, -CELL_KM*1000, y1+PAD*CELL_KM*1000)
    T = int(base[base.fire==f].t_idx.max()) + int(base[base.fire==f].h.min()) + 1  # placeholder, recomputed below
    T = int(A[A!=NEVER].max()) + 1 if False else None
    hrs = base[base.fire==f]
    # T = number of perimeters: issue hours run t<=T-1-h; recover from max(t_idx+h)
    T = int((hrs.t_idx + hrs.h).max()) + 1
    tmin, tmax = t0, t0 + pd.Timedelta(hours=T)
    final = A != NEVER
    near = ndimage.distance_transform_edt(~final) * CELL_KM <= 5.0
    h_, w_ = A.shape
    cand = g[(g.L1 > tmin) & (g.L0 < tmax)]
    masks = []
    for _, r in cand.iterrows():
        m = rasterize([(r.geometry, 1)], out_shape=(h_, w_), transform=tfn, fill=0, dtype='uint8').astype(bool)
        if m.any() and (m & near).any():
            masks.append((r.rid, r.L0, r.L1, m)); touched.add(r.rid)
    # labels near the fire footprint at all, regardless of time window
    for _, r in g[(g.L1 <= tmin) | (g.L0 >= tmax)].iterrows():
        pass
    known_cache = {}
    for t in range(int(A[A != NEVER].min()), T):
        known = A <= t; dist = dist_km(known); Tt = t0 + pd.Timedelta(hours=t)
        for h in (5, 8):
            if t + h > T - 1: continue
            newb = (A > t) & (A <= t + h); Te = Tt + pd.Timedelta(hours=h)
            res = {}
            for ver in ('lower', 'upper'):
                act = [m for (rid, L0, L1, m) in masks if (L0 >= Tt and L1 <= Te if ver == 'lower' else L0 < Te and L1 > Tt)]
                if act:
                    new = newb | (np.logical_or.reduce(act) & ~known)
                    r_, _, _ = component_reach(known, new, (5.0,), dist=dist)
                    res[ver] = r_[5.0]
                else:
                    res[ver] = None
                if act:
                    for (rid, L0, L1, m) in masks:
                        if (L0 >= Tt and L1 <= Te if ver == 'lower' else L0 < Te and L1 > Tt) and (m & ~known & (dist <= 5.0)).any(): touched_time.add((ver, rid))
            b = base[(base.fire == f) & (base.t_idx == t) & (base.h == h)]
            if len(b) != 1: continue
            b0 = float(b.reach_km.iloc[0])
            allrows.append(dict(fire=f, t_idx=t, h=h, base=b0,
                                lower=b0 if res['lower'] is None else res['lower'],
                                upper=b0 if res['upper'] is None else res['upper']))
    print(f, len(masks), flush=True)
df = pd.DataFrame(allrows); df.to_csv(S/'scores_with_labels.csv.gz', index=False)
# touched by distance only (any time)
print('labels near any GOFER final footprint & time overlapping fire span:', len(touched))
out = []
for h, Rp in ((5, 3.75), (8, 5.03)):
    d = df[df.h == h]
    for ver in ('base', 'lower', 'upper'):
        sc = by_fire(d, ver)
        for Rmode in ('fixed', 'rederived'):
            lo = lofo(sc, 0.10)
            if Rmode == 'fixed':
                m = np.array([np.mean(v > Rp) for v in sc.values()]); k = m.sum(); n = len(m)
                miss = m.mean(); ci = clopper_pearson(k, n); Rv = Rp
            else:
                s = summarise_lofo(lo); miss = s['miss_rate']; ci = s['ci95']; n = s['n_fires']
                Rv = conformal_R(list(sc.values()), 0.10)[0]
            out.append(dict(h=h, scores=ver, R_mode=Rmode, R_km=round(Rv, 3), lofo_miss=miss, ci_lo=ci[0], ci_hi=ci[1], n_fires=n, hours=len(d)))
    for ver in ('lower', 'upper'):
        ch = d[~np.isclose(d[ver], d.base)]
        out.append(dict(h=h, scores=ver+'_changed_cells', R_mode='', R_km=Rp, lofo_miss=len(ch), ci_lo=int((ch[ver] > Rp).sum()), ci_hi=int(((ch.base <= Rp) & (ch[ver] > Rp)).sum()), n_fires=ch.fire.nunique(), hours=len(d)))
o = pd.DataFrame(out); o.to_csv(S/'downstream_numbers.csv', index=False); print(o.to_string())
print({v: len({r for (vv, r) in touched_time if vv == v}) for v in ('lower', 'upper')})

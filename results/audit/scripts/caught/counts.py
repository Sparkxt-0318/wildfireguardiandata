# Independent recomputation of CAUGHT_RESULTS.md slice tables from caught-v0.1 label parquet files.
import sys, json, pandas as pd, numpy as np
from scipy.stats import beta
sys.path.insert(0, sys.argv[1])
df = pd.read_pickle(sys.argv[2])
def cp(k, n, a=0.05):
    lo = 0.0 if k == 0 else beta.ppf(a/2, k, n-k+1)
    hi = 1.0 if k == n else beta.ppf(1-a/2, k+1, n-k)
    return 100*lo, 100*hi
slices = {'S1': df[(df.STATE=='CA') & (df.FIRE_YEAR==2020)],
          'S2': df[df.FIRE_YEAR==2020], 'S3': df}
for s, d in slices.items():
    print(f'==== {s}: records {len(d)}, searched {int(d.searched.sum())}, tiers', d.tier.value_counts().to_dict())
    rows=[]
    for cls in list('ABCDEFG')+['all']:
        x = d if cls=='all' else d[d.FIRE_SIZE_CLASS==cls]
        nl = x[~x.std_label]
        v = int((nl.tier=='verified').sum()); p=int((nl.tier=='probable').sum()); r=int((nl.tier=='record-only').sum())
        lo,hi = cp(v, len(nl))
        rows.append((cls, len(x), int(x.std_label.sum()), len(nl), v, f'{lo:.2f}-{hi:.2f}', p, r))
    print(pd.DataFrame(rows, columns=['cls','records','std','nostd','verified','CI%','probable','recordonly']).to_string(index=False))
    nl = d[~d.std_label]; vn = nl[nl.tier=='verified']
    tok = lambda col, t: int(vn[col].str.split(',').apply(lambda L: t in L).sum())
    print(' verified no-std witnesses:', {t: tok('witnesses', t) for t in ['S2_SCAR','PERIM','HMS_ANALYST','GOES','HMS_SMOKE','LANDSAT_SCAR']})
    print(' verified no-std in pairs:', {t: int(vn.pairs.str.contains('"'+t+'"').sum()) for t in ['S2_SCAR','PERIM','HMS_ANALYST','GOES']})
    V = d[d.tier=='verified']
    print(' all verified', len(V), 'with PERIM witness', tok_all := int(V.witnesses.str.split(',').apply(lambda L:'PERIM' in L).sum()),
          'PERIM kind', int(V.kinds.str.split(',').apply(lambda L:'PERIMETER' in L).sum()))
    P = d[d.tier=='probable']
    print(' all probable', len(P), 'probable no pixel label', int((~P.pixel_label).sum()), 'probable kinds==SMOKE', int((P.kinds=='SMOKE').sum()))
    print(' record-only reasons', d[d.tier=='record-only'].reason.value_counts().to_dict())
    ro = d[d.tier=='record-only']
    print(' class A record-only', int((ro.FIRE_SIZE_CLASS=='A').sum()), 'of which below_floor', int(((ro.FIRE_SIZE_CLASS=='A')&(ro.reason=='below_floor')).sum()))
    print(' clear_look_nothing_found classes B-G', int(((ro.FIRE_SIZE_CLASS!='A')&(ro.reason=='clear_look_nothing_found')).sum()),
          'all classes', int((ro.reason=='clear_look_nothing_found').sum()))
# by year
print('==== S3 by year')
for y, x in df.groupby('FIRE_YEAR'):
    nl = x[~x.std_label]
    vc = nl[nl.tier=='verified'].FIRE_SIZE_CLASS.value_counts().sort_index().to_dict()
    print(y, len(x), int(x.std_label.sum()), len(nl), int((nl.tier=='verified').sum()), vc,
          int((nl.tier=='probable').sum()), int((nl.tier=='record-only').sum()), 'searched', int(x.searched.sum()))
# integrity
print('==== integrity')
print('rows', len(df), 'unique rid', df.rid.nunique(), 'unique FOD_ID', df.FOD_ID.nunique())
print('tier null', int(df.tier.isna().sum()), 'tier values', sorted(df.tier.unique()))
print('slice values', df.slice.unique(), 'FIRE_YEAR==file year', bool((df.FIRE_YEAR==df._file_year).all()))
print('record-only with null reason', int(((df.tier=='record-only')&df.reason.isna()).sum()),
      'labelled with reason', int(((df.tier!='record-only')&df.reason.notna()).sum()))
print('verified with <1 pair', int(((df.tier=='verified')&(df.pairs=='[]')).sum()),
      'probable with pairs', int(((df.tier=='probable')&(df.pairs!='[]')).sum()))
nk = df.kinds.apply(lambda s: len([k for k in s.split(',') if k]))
print('kinds count by tier', pd.crosstab(df.tier, nk.clip(upper=3)).to_dict())
print('std_label vs std_witnesses consistent', bool((df.std_label == (df.std_witnesses!='')).all()))
print('FIRE_SIZE_CLASS vs FIRE_SIZE check')
bins=[0,0.25,10,100,300,1000,5000,1e12]
cls=pd.cut(df.FIRE_SIZE, bins=bins, labels=list('ABCDEFG'), right=False)
print(' mismatches (A<0.25,B<10,C<100,D<300,E<1000,F<5000):', int((cls.astype(str)!=df.FIRE_SIZE_CLASS).sum()))

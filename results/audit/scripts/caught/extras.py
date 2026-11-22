# Consistency checks: CP intervals from published placebo k/n (inputs not in release), v0.1 quantities feeding v0.2 text,
# label intervals for S1 verified labels, comparison with repo verified_S1/S2 csv (non-release, side check only).
import sys, pandas as pd, numpy as np
from scipy.stats import beta
df = pd.read_pickle(sys.argv[1]); repo = sys.argv[2]
def cp(k, n):
    lo = 0.0 if k == 0 else beta.ppf(.025, k, n-k+1); hi = 1.0 if k == n else beta.ppf(.975, k+1, n-k)
    return f'{100*k/n:.2f} % ({100*lo:.2f}-{100*hi:.2f})'
for k, n in [(9,3526),(10,9251),(178,3526),(51,30992),(53,70163),(1524,30992),(191,91224),(205,209000),(4837,91224)]:
    print('CP from published', k, n, cp(k, n))
P = df[df.tier=='probable']
for nm, d in [('S1', P[(P.STATE=='CA')&(P.FIRE_YEAR==2020)]), ('S2', P[P.FIRE_YEAR==2020]), ('S3', P)]:
    print(nm, 'probable with SCAR kind', int(d.kinds.str.split(',').apply(lambda L:'SCAR' in L).sum()),
          'probable scar_status==scar', int((d.scar_status=='scar').sum()))
V1 = df[(df.tier=='verified')&(df.STATE=='CA')&(df.FIRE_YEAR==2020)]
L = (pd.to_datetime(V1.label_t1) - pd.to_datetime(V1.label_t0)).dt.days
print('S1 verified label interval days (t1-t0): n', len(L), 'min', L.min(), 'median', L.median(), 'q75', L.quantile(.75), 'share>=50', (L>=50).mean())
L1 = L+1; print(' inclusive days: min', L1.min(), 'median', L1.median(), 'q75', L1.quantile(.75), 'share>=50', (L1>=50).mean())
for f, sel in [('verified_S1.csv', V1), ('verified_S2.csv', df[(df.tier=='verified')&(df.FIRE_YEAR==2020)])]:
    try:
        r = pd.read_csv(f'{repo}/results/caught/{f}', usecols=lambda c: c in ('rid','tier','FOD_ID'))
        key = 'rid' if 'rid' in r else 'FOD_ID'
        a = set(r[key].astype(str)); b = set(sel[key].astype(str))
        print(f, 'repo rows', len(r), 'release rows', len(sel), 'only repo', len(a-b), 'only release', len(b-a))
    except Exception as e: print(f, 'ERR', e)

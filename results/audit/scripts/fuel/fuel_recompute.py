"""Recompute fuel numbers recoverable from release fuel-v0.1 overlays (verdict.tif, rules.tif, suggest.tif, overlay.json)."""
import json, sys, os
import numpy as np, rasterio
from pyproj import Transformer
D = sys.argv[1]
V = {1: 'consistent', 2: 'stale', 3: 'contradicted', 4: 'unknown'}
BITS = ['R1.1', 'R1.2', 'R1.3', 'R1.4', 'R1.5', 'R1.6', 'R1.7', 'R1.9', 'S1', 'S2', 'R3a', 'R3b', 'U0']
tr = Transformer.from_crs('EPSG:5070', 'EPSG:4326', always_xy=True)
def load(p):
    with rasterio.open(p) as r:
        return r.read(1), r.bounds, r.crs
res = {}
for m in ['M22', 'M16']:
    for a in sorted(os.listdir(os.path.join(D, m))):
        d = os.path.join(D, m, a)
        J = json.load(open(os.path.join(d, 'overlay.json')))
        v, b, crs = load(os.path.join(d, 'verdict.tif'))
        rl, _, _ = load(os.path.join(d, 'rules.tif'))
        sg, _, _ = load(os.path.join(d, 'suggest.tif'))
        cnt = {V[k]: int((v == k).sum()) for k in V}
        cnt['outside'] = int((v == 0).sum())
        rc = {BITS[i]: int(((rl >> i) & 1).astype(bool).sum()) for i in range(len(BITS))}
        row = dict(map=m, area=a, counts=cnt, json_counts=J['counts'], counts_match=all(cnt[k] == J['counts'][k] for k in J['counts']),
                   rule_counts=rc, json_rule_counts=J['rule_counts'],
                   rules_match=all(rc[k] == J['rule_counts'].get(k, 0) for k in rc),
                   n_contra_with_suggest=int(((v == 3) & (sg != 0)).sum()), n_suggest=int((sg != 0).sum()), json_suggestions=J.get('suggestions'),
                   inputs_unchanged=J.get('inputs_unchanged'), code_hash=J.get('code_hash'), config_hash=J.get('config_hash'),
                   cutoff=J.get('event_cutoff_year'), shape=v.shape)
        cx, cy = (b.left + b.right) / 2, (b.bottom + b.top) / 2
        row['center_lonlat'] = tuple(round(x, 2) for x in tr.transform(cx, cy))
        res[(m, a)] = row
for k, r in res.items():
    print(json.dumps({kk: vv for kk, vv in r.items() if kk not in ('json_rule_counts',)}, default=str))
print()
for m in ['M22', 'M16']:
    rows = [r for (mm, a), r in res.items() if mm == m and a.startswith('T')]
    tot = {k: sum(r['counts'][k] for r in rows) for k in ['consistent', 'stale', 'contradicted', 'unknown', 'outside']}
    n = sum(tot[k] for k in ['consistent', 'stale', 'contradicted', 'unknown'])
    print(m, 'sealed areas', len(rows), 'cells in area', n, 'all incl outside', n + tot['outside'],
          {k: '%.2f%%' % (100 * tot[k] / n) for k in ['consistent', 'contradicted', 'stale', 'unknown']},
          'all counts match overlay.json:', all(r['counts_match'] for r in rows), 'rule bits match:', all(r['rules_match'] for r in rows),
          'inputs_unchanged all:', all(r['inputs_unchanged'] for r in rows), 'code hashes', {r['code_hash'][:12] for r in rows})
fires = [r for (mm, a), r in res.items() if a.startswith('F_')]
print('fires', len(fires), 'maps', {r['map'] for r in fires})
print('states', sorted({r['area'].split('_')[2] for r in fires}), len({r['area'].split('_')[2] for r in fires}))
print('years', sorted({r['area'].split('_')[1] for r in fires}))
print('cutoff==fire year all:', all(str(r['cutoff']) == r['area'].split('_')[1] for r in fires))
print('contradicted with suggestion, total over fires:', sum(r['n_contra_with_suggest'] for r in fires),
      '; fires with >0:', sum(r['n_contra_with_suggest'] > 0 for r in fires),
      '; fires with 0:', [r['area'] for r in fires if r['n_contra_with_suggest'] == 0])
print('all suggest cells over fires', sum(r['n_suggest'] for r in fires), 'json suggestions sum', sum(r['json_suggestions'] or 0 for r in fires))
print('R3b detwiler', res[('M16', 'F_2017_CA_detwiler')]['rule_counts']['R3b'], res[('M16', 'F_2017_CA_detwiler')]['json_rule_counts'].get('R3b'))
print('fire counts/rules match json:', all(r['counts_match'] and r['rules_match'] for r in fires))
print('sealed tile centres', {r['area']: r['center_lonlat'] for r in res.values() if r['map'] == 'M22'})

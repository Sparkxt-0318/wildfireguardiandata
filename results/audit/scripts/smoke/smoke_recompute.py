"""Independent recompute of sealed smoke S2/S3 numbers from release smoke-v0.1 labels.json/opacity.npz/edges.json."""
import json, sys, os, hashlib
import numpy as np
D = sys.argv[1]
rows = []
for name in sorted(os.listdir(D)):
    L = json.load(open(os.path.join(D, name, 'labels.json')))
    r = dict(name=name, excluded=L.get('excluded'), n_inputs=len(L['inputs']))
    if not L.get('excluded'):
        off = np.array(L['offsets'])
        p = L['params']
        pre = (off <= p['pre_end_offset']) & (off >= p['pre_start_offset'])
        r.update(n_pre=int(pre.sum()), n_frames=len(off), placebo=L['placebo_smoke_frames'],
                 first=L['first_smoke_offset_s'], human=L['human_offset_s'], params_hash=L['params_hash'],
                 n_chains=len(L['chains']), first_frame=L['first_smoke_frame'],
                 offsets_minmax=(int(off.min()), int(off.max())), gaps=sorted(set(np.diff(off).tolist())))
        # check placebo frame indices lie in pre window
        r['placebo_offsets'] = [int(off[t]) for t in L['placebo_smoke_frames']]
        z = np.load(os.path.join(D, name, 'opacity.npz'))
        r['npz_keys'] = {k: (z[k].shape, str(z[k].dtype)) for k in z.files}
        r['npz_offsets_equal'] = bool(np.array_equal(z['offsets'], off)) if 'offsets' in z.files else None
        E = json.load(open(os.path.join(D, name, 'edges.json')))
        r['edges_type'] = type(E).__name__ + (':' + ','.join(list(E)[:6]) if isinstance(E, dict) else '')
    rows.append(r)
for r in rows:
    print(json.dumps({k: v for k, v in r.items()}, default=str)[:900])
ok = [r for r in rows if not r['excluded']]
print('sequences', len(rows), 'excluded', [(r['name'], r['excluded'], r['n_inputs']) for r in rows if r['excluded']])
pf = np.array([len(r['placebo']) for r in ok], float); nf = np.array([r['n_pre'] for r in ok], float)
print('S2 false frames', pf.sum(), 'of', nf.sum(), 'rate %.4f' % (pf.sum() / nf.sum()), 'seqs with false', int((pf > 0).sum()), 'of', len(ok))
# independent percentile bootstrap over sequences of pooled rate (own seed)
rng = np.random.default_rng(12345); b = []
for _ in range(20000):
    i = rng.integers(0, len(ok), len(ok)); b.append(pf[i].sum() / nf[i].sum())
print('S2 pooled CI own bootstrap (20000, seed 12345): %.4f %.4f' % tuple(np.quantile(b, [.025, .975])))
# the repo's stated scheme: seed 0, 2000, pooled
rng = np.random.default_rng(0); b = []
for _ in range(2000):
    i = rng.integers(0, len(ok), len(ok)); b.append(pf[i].sum() / nf[i].sum())
print('S2 pooled CI repo scheme (seed 0, 2000): %.4f %.4f' % tuple(np.quantile(b, [.025, .975])))
# mean of per-seq rates CI with repo boot_ci style (seed 0)
rates = pf / nf
rng = np.random.default_rng(0); out = []
ids = list(range(len(ok)))
for _ in range(2000):
    pick = rng.choice(len(ids), len(ids)); out.append(np.mean(rates[pick]))
print('S2 mean-of-rates', rates.mean(), 'CI', np.quantile(out, [.025, .975]))
det = [r for r in ok if r['first'] is not None]
d = np.array([r['first'] - r['human'] for r in det], float)
print('S3 detected', len(det), 'of', len(ok), 'share %.3f' % (len(det) / len(ok)))
print('S3 diffs sorted', sorted(d.tolist()))
print('S3 quantiles q10,q25,q50,q75,q90 (numpy linear):', [float(np.quantile(d, q)) for q in (.1, .25, .5, .75, .9)])
print('S3 share before %.3f after %.3f within5min %.3f' % ((d < 0).mean(), (d > 0).mean(), (abs(d) <= 300).mean()))
print('not detected:', [r['name'] for r in ok if r['first'] is None])
print('params hashes', sorted({r['params_hash'] for r in ok}))

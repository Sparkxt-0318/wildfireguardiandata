"""Sanity: per sealed sequence, from opacity.npz classes, first frame with any smoke-class pixel vs labels first_smoke_frame;
smoke-class pixels in the pre window (full run, not the blocked placebo); edges.json levels."""
import json, sys, os
import numpy as np
D = sys.argv[1]
for name in sorted(os.listdir(D)):
    L = json.load(open(os.path.join(D, name, 'labels.json')))
    if L.get('excluded'): continue
    z = np.load(os.path.join(D, name, 'opacity.npz'))
    cn = list(z['class_names']); cls = z['classes']; off = z['offsets']
    si = cn.index('smoke')
    has = (cls == si).reshape(len(off), -1).any(1)
    fr = np.where(has)[0]
    pre = (off <= -300) & (off >= -2400)
    E = json.load(open(os.path.join(D, name, 'edges.json')))
    k0 = list(E)[0]
    print(name, cn, 'first smoke-class frame', (int(fr[0]), int(off[fr[0]])) if len(fr) else None,
          'labels', L['first_smoke_frame'], L['first_smoke_offset_s'], '| pre frames w/ smoke class (full run):', int((has & pre).sum()),
          '| placebo', len(L['placebo_smoke_frames']), '| edges keys', len(E), 'sample', type(E[k0]).__name__, list(E[k0])[:6] if isinstance(E[k0], dict) else len(E[k0]),
          '| alpha max', int(z['alpha'].max()))

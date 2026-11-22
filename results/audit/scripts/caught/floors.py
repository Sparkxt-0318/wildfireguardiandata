# Recompute heat floors and scar floors with the repo's own floor code (firewitness.caught), compare with release json.
import json, sys, math
from firewitness.caught.run import heat_floors
from firewitness.caught.floor import scar_floor_m2
rel = json.load(open(sys.argv[1]))
hf = heat_floors(0)
for k in rel: print(k, 'release', rel[k], 'repo code', hf.get(k), 'EQUAL' if hf.get(k)==rel[k] else 'DIFF')
for nm, p in [('S2', 20), ('Landsat', 30)]:
    print(nm, 'scar floor N_min 8 T 0.10:', scar_floor_m2(0.10, p, n_min=8), 'independent:', (math.sqrt(8)+1)**2*p*p*0.10/0.25)
for fuel, T, d in [('grass',.100,.251),('shrub',.100,.228),('timber',.118,.233)]:
    for nm,p in [('S2',20),('L',30)]:
        f=(math.sqrt(8)+1)**2*p*p*T/d; print(fuel, nm, round(f), round(f/4046.856,2))

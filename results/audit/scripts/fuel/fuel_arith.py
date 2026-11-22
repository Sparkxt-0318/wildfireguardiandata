"""Internal-arithmetic check of published fuel counts (not a recompute from data: plot tables are not released)."""
from math import sqrt
def wil(k, n, z=1.959964):
    p = k / n; c = p + z * z / (2 * n); h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)); return (c - h) / (1 + z * z / n), (c + h) / (1 + z * z / n)
for lab, dc, nc, dk, nk in [('sealed', 103, 117, 179, 1609), ('dev r10', 41, 48, 125, 1638), ('dev v1', 47, 64, 112, 1615)]:
    print(lab, 'd_c %.4f d_k %.4f R %.3f' % (dc / nc, dk / nk, (dc / nc) / (dk / nk)), 'contradicted&agree', nc - dc)
for lab, k, n in [('sealed M22', 14, 1515), ('dev r10', 7, 1743), ('dev v1', 17, 1743), ('sealed M16', 8, 1546)]:
    print(lab, 'F2 %.4f%%' % (100 * k / n), 'Wilson upper %.4f%%' % (100 * wil(k, n)[1]))

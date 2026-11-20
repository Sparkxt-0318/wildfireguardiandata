"""Fire arrival time (hours) on the 30 m grid from a sequence of progression perimeters.

Method (arrival_hours):
  1. Perimeters are made nested by the running union, M_0 <= M_1 <= ... (monotone in time).
  2. Cells inside the first perimeter M_0 get t = 0 (hours since the first perimeter's datetime).
  3. A cell in the ring between successive perimeters k and k+1 (outside M_k, inside M_{k+1}) gets
         t = t_k + (t_{k+1} - t_k) * d_k / (d_k + d_{k+1})
     d_k     = Euclidean distance (m) from the cell to M_k       (EDT of the complement of M_k)
     d_{k+1} = Euclidean distance (m) from the cell to the nearest cell OUTSIDE M_{k+1} (EDT of M_{k+1}).
     Both EDTs measure to a neighbouring cell CENTRE, which is half a cell farther than the perimeter edge, so
     res/2 is subtracted from each (a cell touching a front then has d = res/2, not res; d_k + d_{k+1} >= res).
     So a cell on the old front gets ~t_k, a cell on the new front gets ~t_{k+1}; for a front moving at a
     constant speed the formula is exact up to the 30 m cell size.
  4. Cells never inside any perimeter = NODATA (-9999).
"""
from __future__ import annotations
from typing import Sequence

import numpy as np
from scipy import ndimage

NODATA = -9999.0


def arrival_hours(masks: Sequence[np.ndarray], t_hours: Sequence[float], res: float = 30.0) -> np.ndarray:
    """masks[k]: boolean raster of perimeter k (same shape); t_hours[k]: its time in hours since the first perimeter
    (t_hours[0] is normally 0), non-decreasing. Returns float32 array, NODATA outside every perimeter."""
    if len(masks) != len(t_hours) or len(masks) == 0:
        raise ValueError("masks and t_hours must have the same non-zero length")
    t_hours = [float(t) for t in t_hours]
    if any(b < a for a, b in zip(t_hours, t_hours[1:])):
        raise ValueError("times must be non-decreasing")
    shape = masks[0].shape
    out = np.full(shape, NODATA, dtype=np.float32)
    cur = np.asarray(masks[0], dtype=bool).copy()  # running union M_k
    out[cur] = t_hours[0]
    for k in range(len(masks) - 1):
        nxt = cur | np.asarray(masks[k + 1], dtype=bool)  # nested: M_{k+1} = M_k union P_{k+1}
        ring = nxt & ~cur
        if ring.any() and not cur.any():
            # first perimeter smaller than one cell (rasterised empty): the first non-empty one is taken as t_{k+1}
            out[ring] = np.float32(t_hours[k + 1])
        elif ring.any():
            d_k = ndimage.distance_transform_edt(~cur, sampling=res)  # to the nearest cell inside M_k
            d_n = ndimage.distance_transform_edt(nxt, sampling=res)   # to the nearest cell outside M_{k+1}
            dk, dn = d_k[ring] - res / 2, d_n[ring] - res / 2  # distance to the edge, not the neighbour centre
            frac = dk / (dk + dn)  # dk, dn >= res/2 on the ring, so the denominator is > 0
            out[ring] = (t_hours[k] + (t_hours[k + 1] - t_hours[k]) * frac).astype(np.float32)
        cur = nxt
    return out

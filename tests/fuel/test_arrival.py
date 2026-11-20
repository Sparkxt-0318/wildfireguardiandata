import pytest

for _m in ("scipy", "rasterio", "geopandas"):
    pytest.importorskip(_m)

import sys

import numpy as np

from firewitness.fuel.fires29.arrival import arrival_hours, NODATA


def _disk(shape, c, r, res=30.0):
    yy, xx = np.indices(shape)
    return np.hypot((xx - c[1]) * res, (yy - c[0]) * res) <= r


def test_expanding_disk_linear_front():
    shape, c, res = (301, 301), (150, 150), 30.0
    r0, v = 300.0, 100.0  # m, m/h
    times = [0.0, 6.0, 12.0, 24.0, 30.0]
    masks = [_disk(shape, c, r0 + v * t) for t in times]
    a = arrival_hours(masks, times, res)
    assert a.dtype == np.float32 and a.shape == shape
    yy, xx = np.indices(shape)
    rho = np.hypot((xx - c[1]) * res, (yy - c[0]) * res)
    inside_first = masks[0]
    assert np.all(a[inside_first] == 0.0)
    final = masks[-1]
    assert np.all(a[~final] == NODATA)
    assert np.all(a[final] != NODATA)
    exp = (rho - r0) / v
    ring = final & ~inside_first
    err = np.abs(a[ring] - exp[ring])
    # distances are measured on a 30 m grid: error well below one cell / front speed (0.3 h)
    assert np.percentile(err, 95) < 0.35
    assert err.max() < 0.8
    # monotone outwards: arrival increases with radius (allowing cell noise)
    order = np.argsort(rho[ring])
    s = a[ring][order]
    assert s[-200:].mean() > s[:200].mean() + 20


def test_nested_by_running_union():
    shape = (60, 60)
    big = _disk(shape, (30, 30), 600)
    small = _disk(shape, (30, 30), 300)
    # second perimeter is smaller than the first (mapping noise): running union keeps the first
    a = arrival_hours([big, small], [0.0, 10.0])
    assert np.all(a[big] == 0.0) and np.all(a[~big] == NODATA)


def test_empty_growth_and_validation():
    m = np.zeros((10, 10), bool)
    m[4:6, 4:6] = True
    a = arrival_hours([m, m], [0.0, 5.0])
    assert (a == 0).sum() == 4 and (a == NODATA).sum() == 96


def test_first_perimeter_rasterises_empty():
    m0 = np.zeros((20, 20), bool)
    m1 = _disk((20, 20), (10, 10), 150)
    a = arrival_hours([m0, m1], [0.0, 3.0])
    assert np.all(a[m1] == 3.0) and np.all(a[~m1] == NODATA)

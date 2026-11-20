import math

import numpy as np
import pytest

scipy = pytest.importorskip("scipy")

from firewitness.live import goes, signal as sg, detector as dt  # noqa: E402
from firewitness.live.live import slot_times  # noqa: E402


def test_nanmedian0_matches_numpy():
    rng = np.random.default_rng(1)
    x = rng.normal(size=(21, 7, 5)).astype(np.float32)
    x[rng.random(x.shape) < 0.4] = np.nan
    x[:, 0, 0] = np.nan
    a = np.nanmedian(x, 0) if np.isfinite(x).any(0).all() else None
    m, n = sg.nanmedian0(x)
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ref = np.nanmedian(x, 0)
    assert np.allclose(m, ref, equal_nan=True, atol=1e-6)
    assert n[0, 0] == 0


def test_scan_geometry_round_trip():
    g = {"x_scale": 5.6e-05, "x_offset": -0.101332, "y_scale": -5.6e-05, "y_offset": 0.128212, "nx": 2500, "ny": 1500, "lon0": -75.0}
    r, c = goes.lonlat_to_rc(-118.0, 34.0, g)
    lon, lat = goes.rc_to_lonlat(r, c, g)
    assert abs(lon + 118.0) < 1e-6 and abs(lat - 34.0) < 1e-6


def test_u_from_max_is_monotone_and_null_calibrated():
    Z = np.array([0.0, 1.0, 2.0, 3.0, 5.0])
    u = sg.u_from_max(Z, np.full(5, 9))
    assert np.all(np.diff(u) > 0)
    # max of 9 iid N(0,1) has median about 1.446; its u is about 0
    assert abs(float(sg.u_from_max(np.array([1.4462]), np.array([9]))[0])) < 0.05


def test_cusum_holds_on_missing_frames():
    u = np.array([3, np.nan, 3, -10], float)[:, None]
    S, _ = sg.cusum(u, 0.5)
    assert S[:, 0].tolist() == [2.5, 2.5, 5.0, 0.0]


def test_compact_filter_rejects_extended_patches():
    z = np.zeros((1, 1, 15, 15))
    z[0, 0, 7, 7] = 6.0                      # point source: kept
    assert np.isfinite(sg.compact_filter(z, 4)[0, 0, 7, 7])
    z2 = np.zeros((1, 1, 15, 15))
    z2[0, 0, 3:12, 3:12] = 6.0               # 9x9 warm patch: rejected at its centre
    assert np.isnan(sg.compact_filter(z2, 4)[0, 0, 7, 7])


def test_two_witness_statistic():
    cfg = dt.Config(cap=8, k=0.5, rho=1.5, m=1.0)
    uE = np.full((4, 1), 3.0)
    uW = np.full((4, 1), 3.0)
    G = dt.g_series(uE, uW, cfg)
    # each S grows 2.5 per frame; pair term (S_E + S_W) / 1.5 exceeds either alone
    assert math.isclose(float(G[-1, 0]), 20.0 / 1.5, rel_tol=1e-6)
    G1 = dt.g_series(uE, None, cfg)
    assert math.isclose(float(G1[-1, 0]), 10.0, rel_tol=1e-6)


def test_episodes_and_clusters():
    G = np.array([[0, 0, 0], [5, 6, 0], [9, 7, 0], [0, 0, 4], [0, 0, 0]], np.float32)
    s, a, b, m = dt.episodes(G, floor=1.0)
    assert sorted(m.tolist()) == [4.0, 7.0, 9.0]
    rc = np.array([[0, 0], [0, 1], [5, 5]])[s]
    # sites 0 and 1 are adjacent and overlap in time: one cluster at h=5; site 2 alone does not reach 5
    assert dt.count_clusters(rc, a, b, m, 5.0) == 1
    assert dt.count_clusters(rc, a, b, m, 1.0) == 2


def test_slot_times_on_conus_cadence():
    t = slot_times(1795197600.0, 1795197600.0 + 900)
    assert all((x - 78) % 300 == 0 for x in t) and len(t) == 3

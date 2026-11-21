import numpy as np

from firewitness.live import traceback_v02 as v


def test_band7_coefficient_matches_mir_method():
    # Wooster et al. 2003: a ~ 3.0e-9 W m-2 sr-1 um-1 K-4 near 3.9 um; ABI radiance is mW m-2 sr-1 (cm-1)-1
    nu = 1e4 / 3.9
    a_um = v.band7_a("G16") * 1e-3 * nu ** 2 * 1e-4
    assert 2.6e-9 < a_um < 3.4e-9
    T = np.array([700.0, 1000.0, 1300.0])
    rel = v.planck_L(T, "G18") / (v.band7_a("G18") * T ** 4)
    assert np.all(np.abs(rel - 1) < 0.15)


def test_pixel_area_two_km_grid():
    lat, lon = np.meshgrid(np.arange(5) * 0.018, np.arange(5) * 0.018, indexing="ij")
    A = v.pixel_area_m2(lat, lon)
    assert np.allclose(A, 2.0e3 ** 2 * 1.0, rtol=0.05)


def test_plume_present_needs_two_consecutive_daytime_frames():
    P = np.array([[0, 5, 0, 5, 5, 0, 5, 9]])
    day = np.array([[1, 1, 1, 1, 1, 1, 0, 1]], bool)
    pres = v.plume_present(P, day, 5)[0]
    assert pres.tolist() == [False, False, False, False, True, False, False, False]
    day2 = day.copy(); day2[0, 5] = False
    pres2 = v.plume_present(P, day2, 5)[0]
    assert pres2[7]            # frames 5 and 6 are night: 4 -> 7 are consecutive daytime frames


def test_support_lead_from_first_frame_of_run():
    T = 40
    ts = np.full((1, T), np.nan); ts[0] = 1e9 + 300 * np.arange(T)
    day = np.ones((1, T), bool)
    P = np.zeros((1, T), int); P[0, 20:30] = 10   # present (2 consecutive) from frame 21
    tD = ts[0, 28]
    s = v.support(P, day, ts, tD, 10)
    assert s["supported"] and abs(s["plume_lead_min"] - 35.0) < 1e-6
    s2 = v.support(P, day, ts, ts[0, 10], 10)
    assert not s2["supported"]
    nite = np.zeros((1, T), bool)
    assert v.support(P, nite, ts, tD, 10) is None

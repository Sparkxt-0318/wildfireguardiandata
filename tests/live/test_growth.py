import math

import numpy as np
import pandas as pd

from firewitness.live.growth import stats as st
from firewitness.live.growth.common import CFG


def test_theil_sen_is_robust_to_outliers():
    t = np.arange(13) / 12.0
    y = 10 + 30 * t
    y[3] = 500.0
    y[7] = -200.0
    assert abs(st.theil_sen(t, y) - 30.0) < 1e-9


def test_block_bootstrap_is_deterministic_and_brackets_the_slope():
    rng = np.random.default_rng(1)
    t = np.arange(37) / 12.0
    y = 5 + 20 * t + rng.normal(0, 2, len(t))
    b1 = st.block_boot_slopes(t, y, 500, 4, st.seed_of("f", "G16", "slope_3h"))
    b2 = st.block_boot_slopes(t, y, 500, 4, st.seed_of("f", "G16", "slope_3h"))
    assert np.array_equal(b1, b2)
    lo, hi = np.percentile(b1, [2.5, 97.5])
    assert lo < 20 < hi


def test_window_needs_half_the_frames_and_both_ends():
    tau = np.arange(0, 61, 5.0)                      # 13 frames of the first hour
    ok = np.ones(13, bool)
    _, n, known = st.window_frames(tau, ok, 1, CFG)
    assert n == 13 and known
    ok2 = ok.copy(); ok2[7:] = False                  # last clear frame at 30 min: the end is missing
    assert not st.window_frames(tau, ok2, 1, CFG)[2]
    ok3 = ok.copy(); ok3[::2] = False                 # 6 frames < 7 needed
    assert st.window_frames(tau, ok3, 1, CFG)[1] == 6 and not st.window_frames(tau, ok3, 1, CFG)[2]


def test_cloudy_frames_are_missing_not_zero():
    tau = np.arange(-120, 361, 5.0)
    P = 10 + 0.5 * np.clip(tau, 0, None)              # 30 MW/h
    P[(tau > 100) & (tau < 140)] = np.nan             # a cloudy spell
    N = np.where(np.isfinite(P), 1.0, np.nan)
    v = st.point_attrs(tau, P, N, CFG)
    assert abs(v["slope_3h"] - 30) < 1e-9 and abs(v["slope_6h"] - 30) < 1e-9
    assert v["n_clear_3h"] == 37 - 7


def test_states_and_doubling_time():
    assert st.state(float("nan"), 1.0) == "unknown"
    assert st.state(-3.0, 2.0) == "measured"
    assert st.state(1.5, 2.0) == "flat"
    tau = np.arange(0, 361, 5.0)
    P = 2.0 ** (tau / 60.0) * 50 - 1.0                # doubles every hour (with the +1 MW offset)
    N = np.ones_like(P)
    v = st.fire_attrs("x", "G16", tau, P, P * 0.9, P * 1.1, N, CFG)
    assert abs(v["doubling_time_h"] - 1.0) < 1e-6


def test_auc_and_local_hour():
    assert st.auc([1, 2, 3, 4], [False, False, True, True]) == 1.0
    assert st.auc([1, 1, 1, 1], [False, True, False, True]) == 0.5
    assert st.local_solar_hour("2024-07-01T20:00:00Z", -120.0) == 12.0


def test_frame_stats_counts_only_significant_ring_pixels():
    from firewitness.live.growth import series as gs
    T, H = 4, 40
    bt = np.full((1, T, H, H), 300.0)
    bg = np.full((1, T, H, H), 300.0, np.float32)
    sc = np.full((1, T, H, H), 0.5, np.float32)
    bt[0, :, 20, 20] = 320.0                          # core fire pixel
    bt[0, :, 23, 20] = 300.4                          # ring pixel, small noise: z < 4, not counted
    bt[0, :, 17, 17] = 310.0                          # ring pixel, z = 20: counted
    bt[0, 2, 19, 19] = np.nan                         # one core pixel missing at slot 2 -> frame not clear
    s = {"BT7": bt}
    area = np.full((H, H), 4e6)
    P, lo, hi, N, clear = gs.frame_stats(s, bg, sc, area, "G16", 0, 20, 20, np.arange(T))
    assert clear.tolist() == [True, True, False, True]
    assert np.isnan(P[2]) and np.isnan(N[2])
    assert N[0] == 2
    a = gs.band7_a("G16")
    frp = lambda T_: 4e6 * 5.670374419e-8 * (gs.planck_L(T_, "G16") - gs.planck_L(300.0, "G16")) / a / 1e6
    assert abs(P[0] - (frp(320.0) + frp(310.0))) < 1e-6
    assert lo[0] <= P[0] <= hi[0]


def test_first_operational_power_defaults_to_zero():
    f = pd.DataFrame({"fire_id": ["a", "a", "b"], "role": ["east", "west", "east"],
                      "fdc_first": ["2024-01-01T01:00:00Z", "2024-01-01T00:30:00Z", None],
                      "fdc_first_power_mw": [50.0, 20.0, None]})
    p = st.first_operational_power(f)
    assert p["a"] == 20.0 and p["b"] == 0.0

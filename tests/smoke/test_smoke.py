import shutil
import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")
pytest.importorskip("PIL")

from firewitness.smoke import core, evaluate, s1, s4, seq


def test_filename_offsets(tmp_path):
    for n in ["1583515695_-00180.jpg", "1583515935_+00060.jpg", "notes.txt"]:
        (tmp_path / n).write_bytes(b"x")
    files = seq.list_frames(str(tmp_path))
    assert [f[0] for f in files] == [-180, 60]


def test_gain_offset_recovered():
    rng = np.random.default_rng(0)
    ref = rng.uniform(0.2, 0.7, (seq.H, seq.W, 3)).astype(np.float32)
    frame = 1.2 * ref + 0.05
    frame[100:150, 100:200] = 0.9                      # a smoke-like minority of pixels must not drive the fit
    g, o = core.fit_gain_offset(frame, ref)
    assert np.allclose(g, 1.2, atol=0.03) and np.allclose(o, 0.05, atol=0.02)


def test_opacity_recovers_known_alpha():
    rng = np.random.default_rng(1)
    B = rng.uniform(0.2, 0.6, (seq.H, seq.W, 3)).astype(np.float32)
    S = np.array([0.8, 0.8, 0.8], np.float32)
    a = np.zeros((seq.H, seq.W), np.float32); a[100:200, 100:300] = 0.5
    I = (1 - a[..., None]) * B + a[..., None] * S
    from firewitness.smoke.params import get
    est = core.opacity(I - B, B, S, get())
    assert abs(est[100:200, 100:300].mean() - 0.5) < 1e-3 and est[:50].max() < 1e-3


def test_boundary_distance():
    m = np.zeros((100, 100), bool); m[20:60, 20:60] = True
    assert s1.boundary_dist(m, m) == 0.0
    m2 = np.zeros_like(m); m2[20:60, 25:65] = True
    assert 2.0 < s1.boundary_dist(m, m2) < 6.0
    assert np.isnan(s1.boundary_dist(m, np.zeros_like(m)))


def test_iou_and_levels():
    assert s4.iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert s4.iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


def test_accept_rule():
    base = dict(mae=(0.2, 0, 0), **{"edge_0.20_median": 10.0}, detect_all=(0.5, 0, 0), first_err_abs_median_frames=2.0)
    better = dict(mae=(0.15, 0, 0), **{"edge_0.20_median": 10.0}, detect_all=(0.5, 0, 0), first_err_abs_median_frames=2.0)
    worse = dict(mae=(0.15, 0, 0), **{"edge_0.20_median": 12.0}, detect_all=(0.5, 0, 0), first_err_abs_median_frames=2.0)
    assert evaluate.accept(base, better, 10, 10)["accepted"]
    assert not evaluate.accept(base, better, 10, 11)["accepted"]       # S2 must not worsen
    assert not evaluate.accept(base, worse, 10, 10)["accepted"]        # one component worse by more than 5%
    assert not evaluate.accept(base, base, 10, 10)["accepted"]         # nothing better
    assert evaluate.accept(base, base, 10, 5)["accepted"]              # A3: fewer false frames, S1 unchanged


def test_plume_is_deterministic():
    rng1 = s1.rng_for("x", 0); rng2 = s1.rng_for("x", 0)
    B = np.zeros((seq.H, seq.W, 3), np.float32)
    hor = np.full(seq.W, 150.0)
    a1, s_1 = s1.make_plume(rng1, B, hor, 0.6, 4); a2, s_2 = s1.make_plume(rng2, B, hor, 0.6, 4)
    assert np.array_equal(a1, a2) and s_1 == s_2 and a1.max() <= 0.6 + 1e-6


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_satellite_clip_plays(tmp_path):
    from firewitness.video import satellite
    satellite.make_fixture(str(tmp_path / "fx"))
    info = satellite.render_satellite(str(tmp_path / "fx"), str(tmp_path / "c.mp4"), seconds=1, fps=10, gif=False, stills=False)
    assert info["decodes_start_to_end"] and info["size"] == "1920x1080" and info["frames"] == 10

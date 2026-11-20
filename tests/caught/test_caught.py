"""Tests for track caught. Heavy geo dependencies are optional in CI: tests needing them skip cleanly."""
import math
from datetime import date

import pytest


def test_floor_physics_monotone():
    from firewitness.caught.floor import Background, heat_floor_m2, pixel_area_m2, scar_floor_m2
    # bigger pixels (edge of scan) need bigger fires
    assert heat_floor_m2("MODIS", 0.0) < heat_floor_m2("MODIS", None)
    assert heat_floor_m2("VIIRS", 0.0) < heat_floor_m2("MODIS", 0.0)
    # a dark night background lowers the VIIRS floor
    night = Background(285, 285, 2, False)
    assert heat_floor_m2("VIIRS", 0.0, night) < heat_floor_m2("VIIRS", 0.0)
    # noisier background raises the floor
    assert heat_floor_m2("MODIS", 0.0, Background(305, 300, 4, True)) >= heat_floor_m2("MODIS", 0.0)
    assert math.isclose(pixel_area_m2("MODIS", 0.0), 1e6, rel_tol=1e-3)
    # scar floor grows with the threshold and is infinite past dNBR_ref
    assert scar_floor_m2(0.10, 20) < scar_floor_m2(0.20, 20)
    assert scar_floor_m2(0.30, 20) == float("inf")


def test_records_radius_and_split():
    from firewitness.caught.records import decimals, r_loc_m, split_of
    assert decimals(38.5) == 1 and decimals(38.12345) == 5
    assert r_loc_m(38.123456, -120.123456) == 250.0
    assert r_loc_m(38.1, -120.1) > 5000.0
    assert split_of("x") in ("dev", "sealed")
    s = [split_of(str(i)) for i in range(2000)]
    assert 0.25 < s.count("dev") / 2000 < 0.35


def test_core_combine_used_for_posterior():
    from firewitness.core.evidence import Witness
    pytest.importorskip("shapely")
    from shapely.geometry import Point
    from firewitness.caught.evidence import Item, posterior
    w = {"S2_SCAR": Witness("S2_SCAR", 0.6, 0.02), "MODIS": Witness("MODIS", 0.2, 0.001)}
    it = [Item("S2_SCAR", Point(0, 0).buffer(10), date(2020, 1, 1), date(2020, 1, 5))]
    p1 = posterior(it, w, 0.3, set())
    p0 = posterior([], w, 0.3, {"S2_SCAR"})
    assert p1 > 0.3 > p0


def test_tiers_need_independent_kinds():
    pytest.importorskip("shapely")
    from shapely.geometry import Point
    from firewitness.caught.evidence import Item, tier
    d0, d1 = date(2020, 7, 1), date(2020, 7, 3)
    scar = Item("S2_SCAR", Point(0, 0).buffer(50), date(2020, 6, 28), date(2020, 7, 6))
    heat = Item("VIIRS_SNPP", Point(30, 0).buffer(270), d0, d0)
    far = Item("GOES", Point(5000, 0).buffer(100), d0, d0)
    late = Item("MODIS", Point(0, 0).buffer(700), date(2020, 9, 1), date(2020, 9, 1))
    assert tier([scar, heat])[0] == "verified"
    assert tier([scar])[0] == "probable"
    assert tier([])[0] == "record-only"
    assert tier([scar, far])[0] == "probable"            # do not agree in place
    assert tier([scar, late])[0] == "probable"           # do not agree in time
    l8 = Item("LANDSAT_SCAR", Point(0, 0).buffer(50), d0, d1)
    assert tier([scar, l8])[0] == "probable"             # same kind twice is not two kinds
    mcd = Item("MCD64A1", Point(0, 0).buffer(330), d0, d1)
    modis = Item("MODIS", Point(0, 0).buffer(700), d0, d0)
    assert tier([mcd, modis])[0] == "probable"           # declared dependency


def test_no_fire_without_candidate_pixels():
    """C3: every accepted scar pixel is a candidate pixel; no dilation or filling (synthetic arrays)."""
    np = pytest.importorskip("numpy")
    ndi = pytest.importorskip("scipy.ndimage")
    rng = np.random.default_rng(0)
    cand = rng.random((60, 60)) > 0.97
    cand[20:26, 20:26] = True
    lab, n = ndi.label(cand, structure=np.ones((3, 3), bool))
    sizes = ndi.sum(np.ones_like(lab), lab, index=range(1, n + 1))
    acc = np.isin(lab, [k + 1 for k in range(n) if sizes[k] >= 4])
    assert not (acc & ~cand).any()


def test_geo_point_index():
    pytest.importorskip("scipy")
    from firewitness.caught.geo import PointIndex, haversine_m
    idx = PointIndex([38.0, 38.01, 40.0], [-120.0, -120.0, -120.0], [100, 100, 100],
                     ["2020-07-01"] * 3, ["2020-07-01"] * 3)
    got = idx.query(38.0, -120.0, 1500, date(2020, 6, 30), date(2020, 7, 2))
    assert sorted(got.tolist()) == [0, 1]
    assert len(idx.query(38.0, -120.0, 1500, date(2020, 7, 2), date(2020, 7, 3))) == 0
    assert abs(haversine_m(38.0, -120.0, 38.01, -120.0) - 1112) < 5


def test_cli_registers():
    import argparse
    from firewitness.caught import cli
    p = argparse.ArgumentParser()
    cli.register(p)
    a = p.parse_args(["floor", "--sensor", "VIIRS", "--night"])
    assert a.func(a) == 0

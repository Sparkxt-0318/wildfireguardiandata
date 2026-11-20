import hashlib
import json
import os

import geopandas as gpd
import numpy as np
import pytest

from firewitness.fuel import runner
from firewitness.fuel import areas as areas_mod
from firewitness.fuel.grid import Grid, write_tif


@pytest.fixture()
def area(tmp_path, monkeypatch):
    g = Grid.from_bounds(0, 0, 30 * 40, 30 * 40)
    d = tmp_path / "areas" / "TEST"
    d.mkdir(parents=True)
    (d / "grid.json").write_text(json.dumps(g.to_dict()))
    rng = np.random.default_rng(1)
    shape = g.shape
    write_tif(d / "fbfm40_lf2022.tif", rng.choice([102, 142, 183, 99, 98], size=shape).astype("int16"), g, dtype="int16")
    write_tif(d / "nlcd_lc2021.tif", rng.choice([71, 52, 42, 11], size=shape).astype("uint8"), g, dtype="uint8")
    write_tif(d / "tcc2021.tif", rng.integers(0, 90, size=shape).astype("uint8"), g, dtype="uint8")
    write_tif(d / "chm.tif", rng.integers(0, 25, size=(2,) + shape).astype("uint8"), g, dtype="uint8")
    write_tif(d / "wc_shares.tif", rng.integers(0, 100, size=(10,) + shape).astype("uint8"), g, dtype="uint8")
    write_tif(d / "hansen.tif", rng.integers(0, 24, size=(2,) + shape).astype("uint8"), g, dtype="uint8")
    gpd.GeoDataFrame({"YEAR": [], "KIND": [], "INCIDENT": [], "SRC": []}, geometry=[], crs=5070).to_file(d / "perimeters.geojson", driver="GeoJSON")
    monkeypatch.setattr(runner, "area_dir", lambda name: d)
    return d


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def test_f3_inputs_untouched_and_rerun_identical(area, tmp_path):
    before = {p.name: sha(p) for p in area.iterdir()}
    m1 = runner.run_area("TEST", "M22", out_root=tmp_path / "o1")
    files = ["verdict.tif", "rules.tif", "suggest.tif", "overlay.json", "cards.npy.gz"]
    h1 = {f: sha(tmp_path / "o1" / "M22" / "TEST" / f) for f in files}
    m2 = runner.run_area("TEST", "M22", out_root=tmp_path / "o2")
    h2 = {f: sha(tmp_path / "o2" / "M22" / "TEST" / f) for f in files}
    after = {p.name: sha(p) for p in area.iterdir()}
    assert before == after            # F3a: no writes to the source files
    assert h1 == h2                   # F3b: byte-identical overlay on re-run
    assert m1["inputs_unchanged"]
    assert not os.access(area / "fbfm40_lf2022.tif", os.W_OK) or os.geteuid() == 0  # read-only (root bypasses mode bits)
    assert sum(m1["counts"].values()) == 41 * 41

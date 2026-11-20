import pytest

for _m in ("scipy", "rasterio", "geopandas"):
    pytest.importorskip(_m)

import ast
from pathlib import Path

import numpy as np

from firewitness.fuel import agent
from firewitness.fuel.grid import Grid
from firewitness.fuel.layers import Layers
from firewitness.fuel.runner import region_cfg

CFG = region_cfg()


def make(cells, shape=(1, 1)):
    """cells: dict of arrays/scalars overriding a neutral default (grass over grass)."""
    g = Grid.from_bounds(0, 0, 30 * shape[1], 30 * shape[0])
    z = lambda v, dt: np.full(shape, v, dt)  # noqa: E731
    d = dict(fbfm=102, lc=71, tcc=0, chm_max=0, chm_cov=0, wc10=0, wc20=0, wc30=90, wc40=0, wc50=0, wc60=0, wc70=0,
             wc80=0, wc90=0, wc100=0, tc2000=0, loss=0, post=0, pre=False)
    d.update(cells)
    wc = {c: z(d[f"wc{c}"], "uint8") for c in (10, 20, 30, 40, 50, 60, 70, 80, 90, 100)}
    return Layers(g, z(d["fbfm"], "int16"), z(d["lc"], "uint8"), z(d["tcc"], "uint8"), z(d["chm_max"], "uint8"),
                  z(d["chm_cov"], "uint8"), wc, z(d["tc2000"], "uint8"), z(d["loss"], "int16"), z(d["post"], "int16"),
                  z(d["pre"], bool), map_year=2022)


def verdict(**kw):
    r = agent.check(make(kw), CFG)
    return agent.VERDICT_NAMES[int(r.verdict[0, 0])], r


def test_consistent_grass():
    assert verdict()[0] == "consistent"


def test_timber_without_canopy_contradicted():
    v, r = verdict(fbfm=183, lc=71, wc10=0, wc30=90)
    assert v == "contradicted" and r.rules[0, 0] & 1


def test_timber_with_canopy_consistent():
    v, _ = verdict(fbfm=183, lc=42, tcc=60, chm_max=18, chm_cov=60, wc10=80, wc30=10)
    assert v == "consistent"


def test_burnable_on_water_suggests_98():
    v, r = verdict(fbfm=102, lc=11, wc80=95, wc30=0)
    assert v == "contradicted" and r.suggest[0, 0] == 98


def test_unburnable_on_vegetation():
    v, r = verdict(fbfm=99, lc=52, wc20=90, wc30=5)
    assert v == "contradicted" and r.sgroup[0, 0] == agent.GROUP_CODES["SH"]


def test_water_class_on_water_consistent():
    assert verdict(fbfm=98, lc=11, wc80=95, wc30=0)[0] == "consistent"


def test_stale_beats_contradicted():
    v, r = verdict(fbfm=183, lc=71, post=2023)
    assert v == "stale" and r.rules[0, 0] & 1  # R1.1 listed too


def test_hansen_loss_after_map_is_stale_only_after_map_year():
    assert verdict(fbfm=183, lc=42, tcc=60, chm_max=18, chm_cov=60, wc10=80, tc2000=60, loss=2023)[0] == "stale"
    assert verdict(fbfm=183, lc=42, tcc=60, chm_max=18, chm_cov=60, wc10=80, tc2000=60, loss=2020)[0] == "consistent"


def test_unmapped_class_unknown():
    assert verdict(fbfm=0)[0] == "unknown"


def test_shrub_under_dense_forest_contradicted():
    v, _ = verdict(fbfm=142, lc=42, tcc=70, chm_max=22, chm_cov=80, wc10=90, wc30=0)
    assert v == "contradicted"


def test_deterministic():
    a = agent.check(make({}, (5, 5)), CFG)
    b = agent.check(make({}, (5, 5)), CFG)
    assert (a.verdict == b.verdict).all() and (a.rules == b.rules).all()


def test_agent_never_imports_plots():
    root = Path(agent.__file__).parent
    banned = {"plots", "grade", "ldc", "metrics", "sealed"}
    for f in ("agent.py", "layers.py", "runner.py", "grid.py", "areas.py"):
        tree = ast.parse((root / f).read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            for n in names:
                assert not (set(n.split(".")) & banned), (f, n)

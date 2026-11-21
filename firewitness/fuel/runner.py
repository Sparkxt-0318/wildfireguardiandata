"""Run the agent on one area and write the overlay (inputs hashed before and after; never written)."""
from __future__ import annotations
import gzip
import io
import json
import os
import stat
import sys
from pathlib import Path

import numpy as np

from ..core.hashing import canonical_json, hash_inputs, hash_obj
from ..core.config import load_region
from . import agent
from .areas import area_dir
from .grid import write_tif
from .layers import Layers, load
from .fetch.rawindex import RAW_ROOT

FUEL_DIR = Path(__file__).parent
OUT_ROOT = RAW_ROOT.parent / "fuel_out"
CODE_VERSION = "fuel-0.1"


def region_cfg(region: str = "us") -> dict:
    return load_region(FUEL_DIR, region)


def code_hash() -> str:
    """Hash of the rule code and config: ties an overlay to the exact rule version."""
    h = [(p.name, p.read_bytes().decode()) for p in (FUEL_DIR / "agent.py", FUEL_DIR / "layers.py", FUEL_DIR / "grid.py")]
    return hash_obj({"code": h})


def make_readonly(paths):
    for p in paths:
        try:
            os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        except OSError:
            pass


def cards_table(L: Layers, res: agent.Result):
    """Compact evidence table for every cell that is not 'consistent' (protocol 3.5)."""
    m = res.verdict != agent.CONSISTENT
    r, c = np.nonzero(m)
    dt = np.dtype([("row", "<i4"), ("col", "<i4"), ("verdict", "u1"), ("rules", "<u4"), ("fbfm", "<i2"), ("suggest", "<i2"),
                   ("S", "i1"), ("n", "u1"), ("lc", "u1"), ("tcc", "u1"), ("chm_max", "u1"), ("chm_cov", "u1"),
                   ("wc_tree", "u1"), ("wc_shrub", "u1"), ("wc_grass", "u1"), ("wc_built", "u1"), ("wc_bare", "u1"),
                   ("wc_water", "u1"), ("tc2000", "u1"), ("loss_year", "<i2"), ("post_fire_year", "<i2")])
    t = np.zeros(len(r), dt)
    vals = dict(row=r, col=c, verdict=res.verdict[m], rules=res.rules[m], fbfm=L.fbfm[m], suggest=res.suggest[m], S=res.S[m],
                n=res.n[m], lc=L.lc[m], tcc=L.tcc[m], chm_max=L.chm_max[m], chm_cov=L.chm_cov[m], wc_tree=L.wc[10][m],
                wc_shrub=L.wc[20][m], wc_grass=L.wc[30][m], wc_built=L.wc[50][m], wc_bare=L.wc[60][m],
                wc_water=L.wc[80][m], tc2000=L.tc2000[m], loss_year=L.loss_year[m], post_fire_year=L.post_fire_year[m])
    for k, v in vals.items():
        t[k] = v
    return t


def write_gz_npy(path: Path, arr):
    buf = io.BytesIO()
    np.save(buf, arr)
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as gz:
        gz.write(buf.getvalue())


def run_area(name: str, map_key: str = "M22", cfg: dict | None = None, out_root: Path | None = None, arrival=None, cutoff_year: int | None = None) -> dict:
    cfg = cfg or region_cfg()
    d = area_dir(name)
    L = load(d, map_key, cfg, cutoff_year=cutoff_year)
    inputs = sorted(set(L.files))
    make_readonly(inputs)
    before = hash_inputs(inputs)
    res = agent.check(L, cfg, arrival=arrival)
    after = hash_inputs(inputs)
    if before != after:
        raise RuntimeError("F3 violated: a source input changed during the run")
    out = Path(out_root or OUT_ROOT) / map_key / name
    out.mkdir(parents=True, exist_ok=True)
    write_tif(out / "verdict.tif", res.verdict, L.grid, nodata=0, dtype="uint8")
    write_tif(out / "rules.tif", res.rules, L.grid, nodata=None, dtype="uint32")
    write_tif(out / "suggest.tif", res.suggest, L.grid, nodata=0, dtype="int16")
    ct = cards_table(L, res)
    write_gz_npy(out / "cards.npy.gz", ct)
    counts = {agent.VERDICT_NAMES[k]: int((res.verdict == k).sum()) for k in (1, 2, 3, 4)}
    rule_counts = {r: int(((res.rules >> b) & 1).sum()) for r, b in agent.RULE_BITS.items()}
    manifest = {"area": name, "map": map_key, "grid": L.grid.to_dict(), "code_version": CODE_VERSION, "code_hash": code_hash(),
                "config_hash": hash_obj(cfg), "inputs": {Path(k).name: v["sha256"] for k, v in before.items()},
                "inputs_unchanged": True, "event_cutoff_year": cutoff_year, "counts": counts, "rule_counts": rule_counts,
                "suggestions": int((res.suggest > 0).sum())}
    (out / "overlay.json").write_text(canonical_json(manifest) + "\n")
    return manifest

"""The brief's command names work at top level: firewitness negatives sample, firewitness splits make, firewitness score."""
import subprocess
import sys

import pytest

from firewitness.score import baselines, models, splits


def run(*args):
    r = subprocess.run([sys.executable, "-W", "ignore", "-m", "firewitness", *args], capture_output=True, text=True)
    return r


def test_top_level_commands_end_to_end(tmp_path, ds):
    d = tmp_path / "ds"
    ds.save(str(d))
    sp = tmp_path / "split.json"
    r = run("splits", "make", "--dataset", str(d), "--scheme", "space", "--out", str(sp))
    assert r.returncode == 0, r.stderr
    r = run("negatives", "sample", "--dataset", str(d), "--split", str(sp), "--fold", "train", "--out", str(tmp_path / "neg.npz"))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "neg.npz").exists()
    c = tmp_path / "c.json"
    assert run("score", "contract-template", "--out", str(c)).returncode == 0
    spl = splits.load(str(sp))
    fires = sorted(set(spl["folds"]["val"]) | set(spl["folds"]["test"]))
    p = tmp_path / "p.npz"
    models.flag_everything(ds, fires).save(str(p))
    r = run("score", "--dataset", str(d), "--split", str(sp), "--contract", str(c), "--predictions", str(p),
            "--model-name", "all", "--out-dir", str(tmp_path / "cards"))
    assert r.returncode == 0, r.stderr
    assert "Score card: all" in r.stdout and "OVER-PREDICTION" in r.stdout


def test_bare_score_prints_usage():
    r = run("score")
    assert r.returncode == 2 and "usage" in r.stdout

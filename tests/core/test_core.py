import json
import random

import pytest

from firewitness.core import (Patch, PatchConflict, PatchSet, Witness, apply_patches, cluster_bootstrap, combine,
                              fit_witnesses, hash_inputs, interval_excludes_zero, load_keys, missing, placebo_test,
                              redact, require_key, revert_patches, sha256_file, shuffle_column, MissingKey)
from firewitness.core.keys import parse_env


def test_keys_parse_and_redact(tmp_path, monkeypatch):
    f = tmp_path / "keys.env"
    f.write_text("A=secretvalue123\n# c\nB='quoted12345'\n")
    monkeypatch.delenv("A", raising=False)
    k = load_keys(f)
    assert k == {"A": "secretvalue123", "B": "quoted12345"}
    assert redact("x secretvalue123 y", k) == "x <REDACTED:A> y"


def test_require_key_notes_need(tmp_path, monkeypatch):
    monkeypatch.delenv("NOPE_KEY", raising=False)
    needs = tmp_path / "NEEDS.md"
    with pytest.raises(MissingKey) as e:
        require_key("NOPE_KEY", needs, path=tmp_path / "absent.env")
    assert "NOPE_KEY" in str(e.value)
    assert "NOPE_KEY" in needs.read_text()
    with pytest.raises(MissingKey):
        require_key("NOPE_KEY", needs, path=tmp_path / "absent.env")
    assert needs.read_text().count("NOPE_KEY") == 1


def test_hash_inputs(tmp_path):
    (tmp_path / "a").write_text("hello")
    h = hash_inputs([tmp_path / "a"])
    assert h[str(tmp_path / "a")]["sha256"] == sha256_file(tmp_path / "a")


def recs():
    return {"1": {"acres": 100, "lon": 120.5}, "2": {"acres": 5, "lon": -100.0}}


def test_apply_revert_roundtrip_and_no_mutation():
    r = recs()
    ps = [Patch("1", "lon", 120.5, -120.5, "sign_flip", {"county": "x"}, 0.9),
          Patch("2", "acres", 5, 50, "unit", "ratio", 0.8),
          Patch("2", "note", missing(), "added", "r", None, 1.0)]
    out = apply_patches(r, ps)
    assert r == recs()
    assert out["1"]["lon"] == -120.5 and out["2"]["note"] == "added"
    back = revert_patches(out, ps)
    assert back == recs()


def test_conflict_when_old_differs():
    with pytest.raises(PatchConflict):
        apply_patches(recs(), [Patch("1", "acres", 999, 1, "r")])


def test_patch_validation():
    with pytest.raises(ValueError):
        Patch("1", "f", 1, 1, "r").validate()
    with pytest.raises(ValueError):
        Patch("1", "f", 1, 2, "").validate()
    with pytest.raises(ValueError):
        Patch("1", "f", 1, 2, "r", confidence=2).validate()


def test_patchset_file_roundtrip_and_tamper(tmp_path):
    ps = PatchSet(input_sha256="abc", tool="t")
    ps.add(Patch("1", "lon", 120.5, -120.5, "sign_flip", {"a": 1}, 0.9))
    ps.add(Patch("2", "note", missing(), "x", "r"))
    p = tmp_path / "p.jsonl"
    ps.write(p)
    back = PatchSet.read(p)
    assert back.patches == ps.patches and back.input_sha256 == "abc"
    lines = p.read_text().splitlines()
    d = json.loads(lines[1]); d["new"] = 0
    lines[1] = json.dumps(d)
    p.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError):
        PatchSet.read(p)


def test_combine_decisions():
    ws = [Witness("space", 0.95, 0.01), Witness("time", 0.9, 0.05), Witness("size", 0.8, 0.1)]
    assert combine(ws, [True, True, True], prior=0.01).decision == "yes"
    assert combine(ws, [False, False, False], prior=0.5).decision == "no"
    v = combine(ws, [True, None, None], prior=0.01)
    assert v.decision == "undecided"
    assert combine(ws, [None, None, None], prior=0.5).decision == "undecided"


def test_fit_witnesses_without_labels_recovers_params():
    rng = random.Random(1)
    true_m = [0.95, 0.9, 0.85]
    true_u = [0.05, 0.1, 0.2]
    pats = []
    for _ in range(6000):
        match = rng.random() < 0.2
        pats.append([rng.random() < (true_m[j] if match else true_u[j]) for j in range(3)])
    ws, pi = fit_witnesses(pats, ["a", "b", "c"])
    assert abs(pi - 0.2) < 0.05
    for w, m, u in zip(ws, true_m, true_u):
        assert abs(w.m - m) < 0.07 and abs(w.u - u) < 0.07


def test_placebo_and_bootstrap():
    rows = [{"x": i, "y": i} for i in range(50)]
    stat = lambda d: sum(r["x"] == r["y"] for r in d) / len(d)
    res = placebo_test(stat, rows, lambda d, rng: shuffle_column(d, "y", rng), n=50, seed=3)
    assert res["real"] == 1.0 and res["p"] < 0.05
    items = [(g, 1 if i % 4 else 0) for g in range(10) for i in range(20)]
    b = cluster_bootstrap(items, lambda t: t[0], lambda s: sum(x[1] for x in s) / len(s), n=200)
    assert b["lo"] <= b["estimate"] <= b["hi"]
    assert interval_excludes_zero({"lo": 0.1, "hi": 0.2})

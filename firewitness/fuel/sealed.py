"""The one-time sealed run (protocol section 8). Refuses to run twice or with rules different from the frozen ones."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from ..core.hashing import hash_inputs, hash_obj
from . import grade, runner
from .areas import SEALED, area_dir

RESULTS = Path(__file__).resolve().parents[2] / "results"


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def run_sealed():
    lock = RESULTS / "sealed_opened.json"
    if lock.exists():
        raise SystemExit("sealed areas were already opened (results/sealed_opened.json); this command runs once")
    frozen = json.loads((RESULTS / "RULES_FROZEN.json").read_text())
    cfg = runner.region_cfg()
    if runner.code_hash() != frozen["code_hash"] or hash_obj(cfg) != frozen["config_hash"]:
        raise SystemExit("rules differ from the frozen version; refusing to open the sealed areas")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=RESULTS.parent).stdout.strip()
    lock.write_text(json.dumps({"opened_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "commit": commit,
                                "code_hash": frozen["code_hash"], "config_hash": frozen["config_hash"]}, indent=1))
    out = {}
    for mk in ("M22", "M16"):
        for t in SEALED:
            runner.run_area(t, mk, cfg)
        res, df = grade.evaluate(SEALED, mk, f"sealed_{mk}", allow_sealed=True)
        res["code_hash"] = frozen["code_hash"]
        (RESULTS / f"sealed_{mk}.json").write_text(json.dumps(res, indent=1, default=str))
        df.to_pickle(runner.OUT_ROOT / f"sealed_{mk}_plots.pkl")
        out[mk] = res
    # F3 on the sealed inputs: hashes unchanged, re-run byte-identical
    f3 = {}
    for t in SEALED:
        files = sorted(p for p in area_dir(t).iterdir() if p.is_file())
        before = hash_inputs(files)
        names = ["verdict.tif", "rules.tif", "suggest.tif", "overlay.json", "cards.npy.gz"]
        with tempfile.TemporaryDirectory() as a:
            runner.run_area(t, "M22", cfg, out_root=Path(a))
            same = all(_sha(Path(a) / "M22" / t / n) == _sha(runner.OUT_ROOT / "M22" / t / n) for n in names)
        f3[t] = {"inputs_unchanged": before == hash_inputs(files), "rerun_identical": same}
    (RESULTS / "sealed_F3.json").write_text(json.dumps(f3, indent=1))
    return out, f3

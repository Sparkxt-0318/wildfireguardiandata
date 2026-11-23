"""Assemble release/growth-v0.1 from the collected parts, freeze the thresholds, render the results (protocol §6, §9)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from . import report as rp
from . import stats as st
from .common import CFG_FILE, sha256_file

HERE = Path(__file__).resolve().parent
THR_FILE = HERE.parent / "config" / "growth_thresholds_us.json"
REL = Path("release/growth-v0.1")


def merge_parts(parts: list[Path], rel: Path = REL) -> Path:
    """parts: folders holding growth_{fires,runs,series,placebo}_{open|sealed}.* (from the collect step)."""
    rel.mkdir(parents=True, exist_ok=True)
    def cat(pattern, reader):
        fs = [f for p in parts for f in sorted(Path(p).glob(pattern))]
        return pd.concat([reader(f) for f in fs], ignore_index=True) if fs else None
    fires = cat("growth_fires_*.csv", lambda f: pd.read_csv(f, dtype={"perm_id": str}))
    fires = fires.sort_values(["fire_id", "sat"]).reset_index(drop=True)
    fires.to_csv(rel / "growth_fires.csv", index=False)
    runs = cat("growth_runs_*.csv", pd.read_csv).sort_values("fire_id").reset_index(drop=True)
    runs.to_csv(rel / "growth_runs.csv", index=False)
    ser = cat("growth_series_*.parquet", pd.read_parquet).sort_values(["fire_id", "sat", "tau_min"]).reset_index(drop=True)
    ser.to_parquet(rel / "growth_series_fire.parquet", index=False, compression="zstd")
    pla = cat("growth_placebo_*.parquet", pd.read_parquet).sort_values(["fire_id", "sat", "day", "di", "dj", "tau_min"]).reset_index(drop=True)
    pla.to_parquet(rel / "growth_series_placebo.parquet", index=False, compression="zstd")
    shutil.copy(CFG_FILE, rel / "growth_us.json")
    for f in ("growth_fires_set_a.csv", "growth_fires_set_b.csv"):
        shutil.copy(Path("protocol") / f, rel / f)
    shutil.copy(HERE / "stats.py", rel / "growth_stats.py")
    shutil.copy(HERE / "report.py", rel / "growth_report.py")
    shutil.copy(HERE / "recompute.py", rel / "growth_recompute.py")
    shutil.copy(Path("docs/growth_data_card.md"), rel / "DATA_CARD.md")
    if THR_FILE.is_file():
        shutil.copy(THR_FILE, rel / "growth_thresholds_us.json")
    return rel


def freeze_thresholds(rel: Path = REL) -> dict:
    """Thresholds from the placebo anchors of Set A and dev only (protocol §6); written to config and the release."""
    d = rp.load(rel)
    if (d["fires"].split == "sealed").any():
        raise SystemExit("refusing: sealed fires are present in the release folder; thresholds use Set A and dev only")
    thr, pa = rp.thresholds_from(d)
    out = {"protocol": "protocol/GROWTH_PROTOCOL.md §6", "quantile": d["cfg"]["placebo"]["quantile"],
           "from": "placebo anchors of Set A and Set B dev fires", "n_anchors": int(pa.split.isin(["A", "dev"]).sum()),
           "thresholds": thr}
    THR_FILE.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    shutil.copy(THR_FILE, rel / "growth_thresholds_us.json")
    return out


def build(rel: Path = REL, results_md: Path = Path("results/GROWTH_RESULTS.md"), prov: dict | None = None) -> dict:
    if prov is not None:
        (rel / "growth_provenance.json").write_text(json.dumps(prov, indent=1, sort_keys=True) + "\n")
    res = rp.compute(rel)
    rp.write_outputs(res, rel)
    md = rp.render(res["numbers"], res["prov"])
    (rel / "GROWTH_RESULTS.md").write_text(md)
    results_md.parent.mkdir(parents=True, exist_ok=True)
    results_md.write_text(md)
    rp.figure(res["curves"], rel / "growth_curves_sealed.png", res["curve_part"])
    return res

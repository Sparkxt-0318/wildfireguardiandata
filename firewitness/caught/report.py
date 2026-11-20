"""Small result tables for results/ (markdown + CSV). Everything here is derived from labels.parquet files."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .stats import c1_table, c2_table, clopper_pearson

CLASSES = list("ABCDEFG")


def headline_table(lab: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for k in CLASSES + ["all"]:
        d = lab if k == "all" else lab[lab.FIRE_SIZE_CLASS == k]
        if not len(d):
            continue
        std = d.std_label.astype(bool)
        ns = d[~std]
        rows.append({
            "class": k, "records": len(d), "std_labelled": int(std.sum()), "no_std_label": len(ns),
            "no_std_now_verified": int((ns.tier == "verified").sum()),
            "no_std_now_probable": int((ns.tier == "probable").sum()),
            "no_std_record_only": int((ns.tier == "record-only").sum()),
            "verified_all": int((d.tier == "verified").sum()), "probable_all": int((d.tier == "probable").sum()),
            "record_only_all": int((d.tier == "record-only").sum()),
            "searched": int(d.searched.astype(bool).sum()),
        })
    t = pd.DataFrame(rows)
    lo, hi = zip(*[clopper_pearson(int(a), int(b)) for a, b in zip(t.no_std_now_verified, t.no_std_label)])
    t["verified_share_of_no_std"] = t.no_std_now_verified / t.no_std_label.where(t.no_std_label > 0)
    t["ci_lo"], t["ci_hi"] = lo, hi
    return t


def reasons_table(lab: pd.DataFrame) -> pd.DataFrame:
    ro = lab[lab.tier == "record-only"]
    return ro.groupby(["FIRE_SIZE_CLASS", "reason"]).size().unstack(fill_value=0)


def witness_table(lab: pd.DataFrame) -> pd.DataFrame:
    """Which looks carried the newly labelled fires (no standard label, verified)."""
    d = lab[(~lab.std_label.astype(bool)) & (lab.tier != "record-only")]
    rows = []
    for t in ("verified", "probable"):
        x = d[d.tier == t]
        c = {}
        for ws in x.witnesses.fillna(""):
            for wname in ws.split(","):
                if wname:
                    c[wname] = c.get(wname, 0) + 1
        for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
            rows.append({"tier": t, "witness": k, "fires": v})
    return pd.DataFrame(rows)


def md(df: pd.DataFrame, floatfmt=3) -> str:
    def f(v):
        if isinstance(v, float):
            return "" if pd.isna(v) else f"{v:.{floatfmt}f}"
        return str(v)
    cols = list(df.columns)
    out = "| " + " | ".join(map(str, cols)) + " |\n|" + "---|" * len(cols) + "\n"
    for _, r in df.iterrows():
        out += "| " + " | ".join(f(r[c]) for c in cols) + " |\n"
    return out


def write_slice(out_dir: Path, name: str, lab_r: pd.DataFrame, lab_p: pd.DataFrame) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    h = headline_table(lab_r)
    c1 = c1_table(lab_p)
    r = reasons_table(lab_r)
    w = witness_table(lab_r)
    h.to_csv(out_dir / f"{name}_headline.csv", index=False)
    c1.to_csv(out_dir / f"{name}_placebo.csv", index=False)
    r.to_csv(out_dir / f"{name}_record_only_reasons.csv")
    w.to_csv(out_dir / f"{name}_witnesses.csv", index=False)
    return {"headline": h, "c1": c1, "reasons": r, "witnesses": w}

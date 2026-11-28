"""Verified-tier audit, step 6: unblind, combine the two raters (rubric section 5) and count with Wilson intervals.

Reads $FIREWITNESS_RAW/audit_cases/{cases_key.csv, cases_public.jsonl, ratings_r1.jsonl, ratings_r2.jsonl};
writes results/verified_audit/{cases.csv, counts.csv, agreement.csv}.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from firewitness.caught.fetch import RAW_ROOT

IN = RAW_ROOT / "audit_cases"
OUT = Path("results/verified_audit")


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def kappa(a: pd.Series, b: pd.Series) -> float:
    cats = sorted(set(a) | set(b))
    n = len(a)
    po = float((a.values == b.values).mean())
    pe = sum((a == c).mean() * (b == c).mean() for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def read_ratings(name):
    rows = {}
    for line in open(IN / f"ratings_{name}.jsonl"):
        line = line.strip()
        if not line:
            continue
        j = json.loads(line)
        rows[j["case"]] = j
    return pd.DataFrame(rows.values())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    key = pd.read_csv(IN / "cases_key.csv")
    pub = pd.DataFrame([json.loads(l) for l in open(IN / "cases_public.jsonl")]).drop_duplicates("case", keep="last")
    r1, r2 = read_ratings("r1"), read_ratings("r2")
    d = key.merge(pub.drop(columns=["text"], errors="ignore"), on="case", how="left")
    for nm, r in (("r1", r1), ("r2", r2)):
        r = r.rename(columns={c: f"{nm}_{c}" for c in r.columns if c != "case"})
        d = d.merge(r, on="case", how="left")
    missing = d[d.r1_class.isna() | d.r2_class.isna()].case.tolist()
    d["r1_class"] = d.r1_class.fillna("c")
    d["r2_class"] = d.r2_class.fillna("c")
    d["final"] = [a if a == b else "c" for a, b in zip(d.r1_class, d.r2_class)]
    d["final_subtag"] = [s1 if a == b and s1 == s2 else (s1 if a == b else "raters_disagree")
                         for a, b, s1, s2 in zip(d.r1_class, d.r2_class, d.r1_subtag, d.r2_subtag)]
    keep = ["case", "arm", "rid", "of_rid", "FIRE_SIZE_CLASS", "FIRE_YEAR", "STATE", "std_label", "witnesses",
            "status", "pre_date", "post_date", "firms_in", "static_days", "fod_10km", "agency_polys", "agency_detail",
            "facts_status", "facts_all", "r1_class", "r1_subtag", "r1_confidence", "r1_reason", "r2_class",
            "r2_subtag", "r2_confidence", "r2_reason", "final", "final_subtag"]
    d[[c for c in keep if c in d]].sort_values(["arm", "case"]).to_csv(OUT / "cases.csv", index=False)
    rows, agr = [], []
    for arm, g in d.groupby("arm"):
        subsets = [("all", g)]
        if arm == "R":
            subsets.append(("no standard label", g[~g.std_label.astype(bool)]))
            subsets.append(("with standard label", g[g.std_label.astype(bool)]))
        for sub, gg in subsets:
            n = len(gg)
            for who, col in (("final", "final"), ("rater 1", "r1_class"), ("rater 2", "r2_class")):
                for cl in ("a", "b", "c"):
                    k = int((gg[col] == cl).sum())
                    lo, hi = wilson(k, n)
                    rows.append({"arm": arm, "subset": sub, "who": who, "class": cl, "k": k, "n": n,
                                 "share": k / n if n else float("nan"), "wilson_lo": lo, "wilson_hi": hi})
        agr.append({"arm": arm, "n": len(g), "raw_agreement": float((g.r1_class == g.r2_class).mean()),
                    "kappa": kappa(g.r1_class, g.r2_class)})
        bsub = g[g.final == "b"].final_subtag.value_counts().to_dict()
        for st, k in bsub.items():
            rows.append({"arm": arm, "subset": "all", "who": "final b subtag", "class": st, "k": int(k), "n": len(g),
                         "share": k / len(g), "wilson_lo": wilson(int(k), len(g))[0], "wilson_hi": wilson(int(k), len(g))[1]})
    pd.DataFrame(rows).to_csv(OUT / "counts.csv", index=False)
    pd.DataFrame(agr).to_csv(OUT / "agreement.csv", index=False)
    print(pd.DataFrame(rows).query("who == 'final'").to_string())
    print(pd.DataFrame(agr).to_string())
    print("cases missing a rating (counted as c):", missing)


if __name__ == "__main__":
    main()

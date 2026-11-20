"""Export examples of records from several sources collapsing into one fire (for the video track).

One JSON file per fire: its source records, the pairwise decisions with the witnesses behind them, the merged record,
and the raw records untouched. Schema is in docs/RECORDS_EXPORT.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import ids, link_tasks as LT, paths


def _day(d):
    return None if not np.isfinite(d) else str(pd.Timestamp("1970-01-01") + pd.Timedelta(days=float(d)))[:10]


def export(n: int, out: Path, seed: int = 0) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    fod, mtbs, ics = LT.load_tables()
    Tm, pm, Xm, dm, _ = LT.decide_all("fod_mtbs")
    Ti, pi, Xi, di, _ = LT.decide_all("fod_ics")
    lm = dm[dm.outcome == "link"].copy(); li_ = di[di.outcome == "link"].copy()
    lm["fid"] = Tm["left"].fid.to_numpy()[lm.li.to_numpy()]; lm["mid"] = Tm["right"].mid.to_numpy()[lm.ri.to_numpy()]
    li_["fid"] = Ti["left"].fid.to_numpy()[li_.li.to_numpy()]; li_["iid"] = Ti["right"].iid.to_numpy()[li_.ri.to_numpy()]
    both = lm.merge(li_, on="fid", suffixes=("_m", "_i"))
    both = both[(both.post_m >= .97) & (both.post_i >= .97)]
    cnt = both.groupby("iid").fid.nunique()
    # fires seen by 3 sources, with a few FOD records under one ICS incident (complex or duplicates)
    cand_i = cnt[(cnt >= 1) & (cnt <= 6)].index
    rng = np.random.default_rng(seed)
    pick = rng.choice(cand_i, size=min(n, len(cand_i)), replace=False)
    fod_i = fod.set_index("fid"); mt = mtbs.set_index("mid"); ic = ics.set_index("iid")
    files = []
    for k, iid in enumerate(pick):
        rows = both[both.iid == iid]
        members = []
        for fid in rows.fid.unique():
            r = fod_i.loc[fid]
            members.append({"source": "fpa_fod", "record_id": str(fid), "name": r["name"], "date": _day(r.day), "lat": float(r.lat), "lon": float(r.lon), "acres": float(r.acres), "state": r.state})
        r = ic.loc[iid]
        members.append({"source": "ics209plus", "record_id": str(iid), "name": r["name"], "date": _day(r.day), "lat": float(r.lat), "lon": float(r.lon), "acres": None if pd.isna(r.acres) else float(r.acres), "state": r.state})
        for mid in rows.mid.unique():
            r = mt.loc[mid]
            members.append({"source": "mtbs", "record_id": str(mid), "name": r["name"], "date": _day(r.day), "lat": float(r.lat), "lon": float(r.lon), "acres": float(r.acres), "state": r.state})
        pairs = []
        for _, rr in rows.iterrows():
            pairs.append({"a": str(rr.fid), "b": str(iid), "probability": float(rr.post_i), "outcome": "link"})
            pairs.append({"a": str(rr.fid), "b": str(rr.mid), "probability": float(rr.post_m), "outcome": "link"})
        big = max(members, key=lambda m: (m["acres"] or 0))
        dates = [m["date"] for m in members if m["date"]]
        merged = {"name": big["name"], "date": min(dates) if dates else None, "lat": big["lat"], "lon": big["lon"], "acres": big["acres"], "state": big["state"], "n_sources": len({m["source"] for m in members})}
        fire = pd.DataFrame({"key": ["x"], "day": [pd.Timestamp(merged["date"]).value / 86400e9 if merged["date"] else np.nan], "lat": [merged["lat"]], "lon": [merged["lon"]], "acres": [merged["acres"]]})
        pid = ids.assign_ids(fire).perm_id.iloc[0]
        ex = {"example_id": f"ex{k:03d}", "cluster_id": pid, "members": [dict(m, cluster_id=pid) for m in members], "pairs": pairs, "merged": merged, "raw_kept": members}
        p = out / f"ex{k:03d}_{pid}.json"
        p.write_text(json.dumps(ex, indent=1, default=str))
        files.append(p)
    return files

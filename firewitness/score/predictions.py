"""Predictions: per fire a float32 (T,H,W) score aligned with the dataset (NaN = not scored) and the declared
information horizon `info_until` (ordinal day of the latest input used) per target day."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json

import numpy as np


class Predictions:
    def __init__(self, scores: dict, info_until: dict | None = None, meta: dict | None = None):
        self.scores = scores                  # fire_id -> float32 (T,H,W)
        self.info_until = info_until or {}    # fire_id -> int32 (T) ordinal day, or missing
        self.meta = meta or {}

    def sha256(self) -> str:
        h = hashlib.sha256()
        for fid in sorted(self.scores):
            a = np.nan_to_num(self.scores[fid].astype(np.float32), nan=-9e9)
            h.update(fid.encode()); h.update(np.ascontiguousarray(a).tobytes())
            if fid in self.info_until:
                h.update(np.ascontiguousarray(self.info_until[fid].astype(np.int32)).tobytes())
        h.update(json.dumps(self.meta, sort_keys=True).encode())
        return h.hexdigest()

    def save(self, path: str) -> None:
        arrs = {f"score__{k}": v for k, v in self.scores.items()}
        arrs.update({f"info__{k}": v for k, v in self.info_until.items()})
        arrs["meta"] = np.array(json.dumps(self.meta, sort_keys=True))
        np.savez_compressed(path, **arrs)

    @staticmethod
    def load(path: str) -> "Predictions":
        z = np.load(path, allow_pickle=False)
        sc = {k[7:]: z[k] for k in z.files if k.startswith("score__")}
        inf = {k[6:]: z[k] for k in z.files if k.startswith("info__")}
        return Predictions(sc, inf, json.loads(str(z["meta"])) if "meta" in z.files else {})

    @staticmethod
    def from_csv(path: str, ds, meta: dict | None = None) -> "Predictions":
        """Sparse rows: fire_id,date,y,x,score[,info_until]. Cells not listed are not flagged (-inf).
        Row order is irrelevant. Duplicate cells keep the maximum score."""
        sc, inf = {}, {}
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                fid = row["fire_id"]
                s = ds.scenes[fid]
                if fid not in sc:
                    sc[fid] = np.full(s.state.shape, -np.inf, np.float32)
                d = dt.date.fromisoformat(row["date"]).toordinal()
                t = int(np.searchsorted(s.dates, d))
                if t >= len(s.dates) or s.dates[t] != d:
                    continue
                y, x = int(row["y"]), int(row["x"])
                v = float(row["score"])
                if v > sc[fid][t, y, x]:
                    sc[fid][t, y, x] = v
                if row.get("info_until"):
                    arr = inf.setdefault(fid, np.full(len(s.dates), -1, np.int32))
                    iu = dt.date.fromisoformat(row["info_until"]).toordinal()
                    arr[t] = max(arr[t], iu)
        return Predictions(sc, inf, meta or {})

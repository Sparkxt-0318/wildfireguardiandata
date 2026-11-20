"""Blocked splits: by fire, in space blocks and time, with a buffer. Published as JSON with its own hash."""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np

from .dataset import Dataset

SCHEMES = ("space", "time", "random_fire", "random_rows")
VERSION = 1


def _h(*parts) -> float:
    d = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(d[:8], "big") / 2 ** 64


def fire_descriptor(s) -> dict:
    return {"lat": s.lat0, "lon": s.lon0, "t0": int(s.dates[0]), "t1": int(s.dates[-1]),
            "half_km": max(s.state.shape[1:]) * s.cell_km / 2, "year": int(s.year)}


def _xy_km(lat, lon):
    return lon * 111.32 * math.cos(math.radians(40.0)), lat * 111.32


def _gap_km(a, b) -> float:
    ax, ay = _xy_km(a["lat"], a["lon"])
    bx, by = _xy_km(b["lat"], b["lon"])
    r = a["half_km"] + b["half_km"]
    return math.hypot(max(0.0, abs(ax - bx) - r), max(0.0, abs(ay - by) - r))


def _gap_days(a, b) -> int:
    return max(0, max(a["t0"], b["t0"]) - min(a["t1"], b["t1"]))


def _assign_groups(groups, order, n, test_frac, val_frac):
    fold, cnt = {}, {"test": 0, "val": 0}
    for g in order:
        if cnt["test"] < test_frac * n:
            k = "test"
        elif cnt["val"] < val_frac * n:
            k = "val"
        else:
            k = "train"
        if k in cnt:
            cnt[k] += len(groups[g])
        for f in groups[g]:
            fold[f] = k
    return fold


def make(ds: Dataset, scheme: str = "space", seed: int = 54, test_frac: float = 0.2, val_frac: float = 0.15,
         block_km: float = 100.0, buffer_km: float = 50.0, buffer_days: int = 30) -> dict:
    if scheme not in SCHEMES:
        raise ValueError(f"scheme must be one of {SCHEMES}")
    ids = ds.ids()
    desc = {f: fire_descriptor(ds.scenes[f]) for f in ids}
    n = len(ids)
    fold_of, blocks = {}, {}
    if scheme == "random_rows":
        fold_of = {f: "train" for f in ids}
    elif scheme == "random_fire":
        order = sorted(ids, key=lambda f: _h(seed, "fire", f))
        fold_of = _assign_groups({f: [f] for f in order}, order, n, test_frac, val_frac)
    elif scheme == "space":
        groups = {}
        for f in ids:
            x, y = _xy_km(desc[f]["lat"], desc[f]["lon"])
            groups.setdefault((int(x // block_km), int(y // block_km)), []).append(f)
        order = sorted(groups, key=lambda b: _h(seed, "block", *b))
        fold_of = _assign_groups({b: groups[b] for b in order}, order, n, test_frac, val_frac)
        blocks = {f"{b[0]}_{b[1]}": fold_of[groups[b][0]] for b in order}
    else:  # time
        years = sorted({desc[f]["year"] for f in ids})
        test_y = years[-1]
        val_y = years[-2] if len(years) > 2 else None
        fold_of = {f: ("test" if desc[f]["year"] == test_y else "val" if desc[f]["year"] == val_y else "train") for f in ids}
    dropped = []
    if scheme != "random_rows":
        rank = {"train": 0, "val": 1, "test": 2}
        for f in ids:
            for g in ids:
                if rank[fold_of[g]] > rank[fold_of[f]] and _gap_km(desc[f], desc[g]) < buffer_km \
                        and _gap_days(desc[f], desc[g]) < buffer_days:
                    dropped.append({"fire": f, "fold": fold_of[f], "near": g, "reason": "buffer"})
                    break
    drop_ids = {d["fire"] for d in dropped}
    folds = {k: sorted(f for f in ids if fold_of[f] == k and f not in drop_ids) for k in ("train", "val", "test")}
    out = {"version": VERSION, "dataset": ds.name, "scheme": scheme,
           "params": {"seed": seed, "test_frac": test_frac, "val_frac": val_frac, "block_km": block_km,
                      "buffer_km": buffer_km, "buffer_days": buffer_days},
           "input_fires_sha256": hashlib.sha256(",".join(ids).encode()).hexdigest(),
           "folds": folds, "dropped": sorted(dropped, key=lambda d: d["fire"]), "blocks": blocks,
           "row_level": scheme == "random_rows"}
    if scheme == "random_rows":
        out["folds"] = {"train": ids, "val": ids, "test": ids}
        out["row_fractions"] = {"test": test_frac, "val": val_frac}
        out["note"] = "NAIVE cell-day random split, for gate N1 only; never report scores from it"
    out["sha256"] = _digest(out)
    return out


def _digest(obj) -> str:
    o = {k: v for k, v in obj.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write(split: dict, path: str) -> None:
    with open(path, "w") as f:
        json.dump(split, f, sort_keys=True, indent=1)


def load(path: str) -> dict:
    sp = json.load(open(path))
    if sp.get("sha256") != _digest(sp):
        raise ValueError(f"split file {path} was edited: hash mismatch")
    return sp


def row_fold(split: dict, fire_idx, t, y, x) -> np.ndarray:
    """Vectorised cell-day fold for the naive random_rows scheme: 0 train, 1 val, 2 test."""
    seed = np.uint64(split["params"]["seed"])
    m = np.uint64
    with np.errstate(over="ignore"):
        v = (np.asarray(fire_idx).astype(np.uint64) * m(0x9E3779B97F4A7C15)) ^ (np.asarray(t).astype(np.uint64) * m(0xC2B2AE3D27D4EB4F)) \
            ^ (np.asarray(y).astype(np.uint64) * m(0x165667B19E3779F9)) ^ (np.asarray(x).astype(np.uint64) * m(0x27D4EB2F165667C5)) ^ seed
        v ^= v >> m(33)
        v *= m(0xFF51AFD7ED558CCD)
        v ^= v >> m(33)
    u = (v >> m(11)).astype(np.float64) / 2 ** 53
    tf, vf = split["row_fractions"]["test"], split["row_fractions"]["val"]
    return np.where(u < tf, 2, np.where(u < tf + vf, 1, 0)).astype(np.int8)

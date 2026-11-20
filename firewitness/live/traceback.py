"""Part A: trace-back from the first standard detection to the first distinguishable frame (protocol §4, §5)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import signal as sg
from .extract import BOX, HALF, NDAYS, NSLOT, SERIES_DIR, load_series
from .firelist import GridIndex, haversine_km, load_firms

K_REF = 0.5
SPATIAL_OFFSETS = [(12, 0), (-12, 0), (0, 12), (0, -12), (12, 12), (12, -12), (-12, 12), (-12, -12)]
DERIVED = SERIES_DIR.parent / "derived"


def anchor_slot(tscan_day0: np.ndarray, T0: float) -> int:
    """Index of the first slot whose scan start is >= T0 (slots before it are 'before the anchor')."""
    ok = np.isfinite(tscan_day0)
    idx = np.where(ok & (tscan_day0 >= T0 - 1))[0]
    return int(idx[0]) if len(idx) else NSLOT


def onset_from_u(u: np.ndarray, a: int, h: float, k: float = K_REF):
    """CUSUM over u[0:a]; returns dict(S_pre, t_D index or None, tau index or None)."""
    S, _ = sg.cusum(u[:a, None], k)
    S = S[:, 0]
    if a == 0:
        return {"S_pre": 0.0, "iD": None, "itau": None, "S": S}
    S_pre = float(S[a - 1])
    if S_pre < h:
        return {"S_pre": S_pre, "iD": None, "itau": None, "S": S}
    # run active at the anchor: back from a-1 to the last frame with S == 0
    j = a - 1
    while j >= 0 and S[j] > 0:
        j -= 1
    itau = j + 1
    iD = itau + int(np.argmax(S[itau:a] >= h))
    return {"S_pre": S_pre, "iD": iD, "itau": itau, "S": S}


class FirmsClean:
    def __init__(self):
        self.idx = GridIndex(load_firms())

    def clean(self, lat, lon, t0, t1, km=5.0):
        return len(self.idx.near(lat, lon, km, t0 - 86400, t1 + 86400)) == 0


def fdc_clean(fdc_day: np.ndarray, i: int, j: int) -> bool:
    w = fdc_day[:, i - 2:i + 3, j - 2:j + 3]
    return not (((w >= 10) & (w <= 15)) | ((w >= 30) & (w <= 35))).any()


VARIANTS = {"A0": "dT", "A1": "dTd", "A2": "dT_c4"}


def process_fire_sat(meta: dict, sat: str, firms: FirmsClean, nboot: int = 200, seed: int = 0, variant: str = "A0"):
    """Compute site series, the fire's CUSUM evidence, placebo anchors and the bootstrap. Returns a dict."""
    s = load_series(meta["fire_id"], sat)
    sm = meta["sats"][sat]
    ukey = VARIANTS[variant]
    f = sg.feature(s, "dT")
    r = sg.residual(f)
    if ukey.startswith("dTd"):
        from .replay import sameday_ref
        r = r - sameday_ref(r)
    z_raw = sg.zscore_all(r, NDAYS)
    z = sg.scene_filter(z_raw)
    if ukey.endswith("_c4"):
        z = sg.compact_filter(z, 4)
    scene_drop = np.isfinite(z_raw) & ~np.isfinite(z)
    u = sg.site_u(z)
    c = HALF
    T0 = meta["T0"]
    a = anchor_slot(s["tscan"][0], T0)
    out = {"fire_id": meta["fire_id"], "sat": sat, "role": sm["role"], "anchor_slot": a, "T0": T0,
           "u_site": u[0, :, c, c].tolist(), "tscan0": s["tscan"][0].tolist(), "tavail0": s["tavail"][0].tolist(),
           "n_clear_pre": int(np.isfinite(u[0, :a, c, c]).sum()), "n_pre": a}
    # placebo anchors (same clock slot a), with their own S_pre
    pl = []
    for d in range(NDAYS):
        offs = SPATIAL_OFFSETS + ([(0, 0)] if d > 0 else [])
        for (di, dj) in offs:
            i, j = c + di, c + dj
            if not fdc_clean(s["FDC"][d], i, j):
                continue
            ts = s["tscan"][d]
            if not np.isfinite(ts).any():
                continue
            t0, t1 = np.nanmin(ts), np.nanmax(ts)
            if not firms.clean(float(s["lat"][i, j]), float(s["lon"][i, j]), t0, t1):
                continue
            Sp, _ = sg.cusum(u[d, :a, i, j][:, None], K_REF)
            pl.append({"day": d, "di": di, "dj": dj, "S_pre": float(Sp[-1, 0]) if a else 0.0,
                       "kind": "temporal" if (di, dj) == (0, 0) else "spatial",
                       "n_clear_pre": int(np.isfinite(u[d, :a, i, j]).sum())})
    out["placebo"] = pl
    out["fire_S_full"] = sg.cusum(u[0, :, c, c][:, None], K_REF)[0][:, 0].tolist()
    # bootstrap of the background days for the fire site (u recomputed for the 3x3 site only)
    rng = np.random.default_rng(seed)
    boots = []
    days = sg.bg_days(0, NDAYS)
    for b in range(nboot):
        ds = list(rng.choice(days, size=len(days), replace=True))
        ub = sg.site_z_boot(r, (c, c), ds, drop=scene_drop[0, :, c - 1:c + 2, c - 1:c + 2])
        boots.append(ub[:a].astype(np.float32))
    out["_boot_u"] = boots
    # FDC first per sat and with low codes (from extraction meta)
    out["fdc_first"] = sm["fdc_first"]
    out["fdc_first_low"] = sm["fdc_first_low"]
    return out


def finalize(rec: dict, h: float) -> dict:
    """Apply the E1 threshold h to one fire-satellite record: t_D, tau, bootstrap interval."""
    a = rec["anchor_slot"]
    u = np.array(rec["u_site"], float)
    ts = np.array(rec["tscan0"], float)
    o = onset_from_u(u, a, h)
    res = {"S_pre": o["S_pre"], "onset": o["iD"] is not None}
    if o["iD"] is not None:
        res["t_D"] = float(ts[o["iD"]]) if np.isfinite(ts[o["iD"]]) else None
        res["tau"] = float(ts[o["itau"]]) if np.isfinite(ts[o["itau"]]) else None
        tb = []
        for ub in rec.get("_boot_u", []):
            ob = onset_from_u(np.asarray(ub, float), a, h)
            if ob["iD"] is not None and np.isfinite(ts[ob["iD"]]):
                tb.append(float(ts[ob["iD"]]))
        nb = max(1, len(rec.get("_boot_u", [])))
        res["boot_share"] = len(tb) / nb
        if tb:
            lo, hi = np.percentile(tb, [2.5, 97.5])
            res["t_D_lo"] = float(lo) - 300.0
            res["t_D_hi"] = float(hi)
        else:
            res["t_D_lo"] = res["t_D_hi"] = None
    return res


def threshold(placebo_S: list[float], q: float = 99.0) -> float:
    x = np.asarray(placebo_S, float)
    return float(np.percentile(x, q)) if len(x) else float("inf")


# ---------------------------------------------------------------- runner
def series_meta(fid: str):
    p = SERIES_DIR / f"{fid}.json"
    return json.loads(p.read_text()) if p.is_file() else None


def run_fire(fid: str, firms: FirmsClean, out_dir: Path = None, force=False, variant: str = "A0"):
    """Process every satellite of one extracted fire; save a pickle per fire-satellite."""
    import pickle
    out_dir = out_dir or (DERIVED / "traceback" / variant)
    meta = series_meta(fid)
    if meta is None:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    recs = {}
    for sat in meta["sats"]:
        f = out_dir / f"{fid}_{sat}.pkl"
        if f.is_file() and not force:
            recs[sat] = pickle.loads(f.read_bytes())
            continue
        rec = process_fire_sat(meta, sat, firms, variant=variant)
        rec["meta"] = {k: v for k, v in meta.items() if k != "sats"}
        f.write_bytes(pickle.dumps(rec))
        recs[sat] = rec
    return recs


def load_records(fids, out_dir: Path = None, variant: str = "A0"):
    import pickle
    out_dir = out_dir or (DERIVED / "traceback" / variant)
    out = []
    for fid in fids:
        for f in sorted(out_dir.glob(f"{fid}_G*.pkl")):
            out.append(pickle.loads(f.read_bytes()))
    return out

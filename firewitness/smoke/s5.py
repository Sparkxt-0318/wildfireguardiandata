"""S5: re-run identity and sensitivity to the background window. Credit: HPWREN, http://hpwren.ucsd.edu/ (image data)."""
from __future__ import annotations
import hashlib, json, os, tempfile, shutil
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import cv2
from . import pipeline, seq, s1 as S1
from .params import get as get_params

RAW = "/home/user/wildfire 3 (1)/firewitness_raw/figlib/"
WINDOWS = [dict(pre_end_offset=-300, pre_start_offset=-2400), dict(pre_end_offset=-600, pre_start_offset=-2400),
           dict(pre_end_offset=-1200, pre_start_offset=-2400), dict(pre_end_offset=-300, pre_start_offset=-1800)]


def dir_hash(d):
    """Hash of every output file; the opacity archive is hashed by its decompressed arrays."""
    h = hashlib.sha256()
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        h.update(f.encode())
        if f.endswith(".npz"):
            z = np.load(p)
            for k in sorted(z.files):
                h.update(k.encode()); h.update(np.ascontiguousarray(z[k]).tobytes())
        else:
            h.update(open(p, "rb").read())
    return h.hexdigest()


def _identity(args):
    name, raw = args
    from . import cli
    import argparse
    out = []
    for i in range(2):
        d = tempfile.mkdtemp(prefix="s5_")
        ns = argparse.Namespace(sequence=os.path.join(raw, name), out=d, cache=None)
        cli._label(ns)
        out.append(dir_hash(d)); shutil.rmtree(d)
    return dict(name=name, hash1=out[0], hash2=out[1], identical=out[0] == out[1])


def _window(args):
    name, raw = args
    sq = seq.load_sequence(os.path.join(raw, name), "/home/user/cache")
    res = []
    for w in WINDOWS:
        p = get_params(**w)
        r = pipeline.label_sequence(sq, p)
        if r["excluded"]:
            res.append(None); continue
        res.append(r)
    base = res[0]
    rows = []
    for w, r in zip(WINDOWS, res):
        row = dict(name=name, window=w)
        if r is None or base is None:
            row["excluded"] = True; rows.append(row); continue
        row["first_offset"] = r["first_offset"]
        row["first_shift_s"] = None if (r["first_offset"] is None or base["first_offset"] is None) else r["first_offset"] - base["first_offset"]
        # edge position at 0.20 at the base run's confirmation frame, inside a window around the base smoke lineage
        e = None
        if base["main"] is not None:
            t = base["main"]["t_conf"]
            pb, pr = base["prep"], r["prep"]
            if t < len(pr["alpha"]):
                win = np.zeros((seq.H, seq.W), np.uint8)
                for tt, i in base["main"]["nodes"]:
                    if tt == t:
                        win |= base["nodes"][tt][i]["mask"].astype(np.uint8)
                win = cv2.dilate(win, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (81, 81))).astype(bool)
                m0 = (pb["alpha"][t] >= np.maximum(0.2, pb["T"])) & win
                m1 = (pr["alpha"][t] >= np.maximum(0.2, pr["T"])) & win
                e = S1.boundary_dist(m0, m1)
        row["edge_shift_px"] = None if e is None or not np.isfinite(e) else float(e)
        rows.append(row)
    return rows


def run_identity(names, workers=4, raw=RAW):
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(_identity, [(n, raw) for n in names]))


def run_window(names, workers=4, raw=RAW):
    with ProcessPoolExecutor(workers) as ex:
        return [r for rows in ex.map(_window, [(n, raw) for n in names]) for r in rows]


def summarise(identity, window):
    out = dict(n_identity=len(identity), identical=int(sum(r["identical"] for r in identity)))
    by = {}
    for r in window:
        if r.get("excluded") or r["window"] == WINDOWS[0]:
            continue
        k = f"end{r['window']['pre_end_offset']}_start{r['window']['pre_start_offset']}"
        d = by.setdefault(k, dict(shift=[], edge=[], n=0, lost=0))
        d["n"] += 1
        if r["first_shift_s"] is not None:
            d["shift"].append(r["first_shift_s"])
        elif r["first_offset"] is None:
            d["lost"] += 1
        if r["edge_shift_px"] is not None:
            d["edge"].append(r["edge_shift_px"])
    for k, d in by.items():
        s = np.array(d["shift"], float); e = np.array(d["edge"], float)
        out[k] = dict(n=d["n"], detected_in_both=len(s), lost_detection=d["lost"],
                      first_shift_median_abs_s=float(np.median(np.abs(s))) if len(s) else None,
                      first_shift_median_s=float(np.median(s)) if len(s) else None,
                      first_shift_iqr_s=[float(np.quantile(s, .25)), float(np.quantile(s, .75))] if len(s) else None,
                      edge_shift_median_px=float(np.median(e)) if len(e) else None, edge_n=len(e))
    return out

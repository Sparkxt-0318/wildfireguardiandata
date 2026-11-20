"""S4: where do existing human boxes sit on the opacity scale?
For each human box, the opacity level whose region (grown from inside the box) has the best-matching bounding box.
Credit: HPWREN, http://hpwren.ucsd.edu/ (images and the HPWREN-BB box CSVs)."""
from __future__ import annotations
import csv, glob, os, re
import numpy as np
import cv2
from . import pipeline, seq

LEVELS = [("noise", None), ("0.10", 0.10), ("0.20", 0.20), ("0.40", 0.40), ("0.60", 0.60)]
_FN = re.compile(r"([^/]+)/(\d+)_([+-]\d+)\.jpg$")


def load_hpwren_boxes(csv_dir):
    """{sequence: {offset: [(x0, y0, x1, y1) at 512x384]}} (CSV boxes are in 2048x1536 pixels)."""
    out = {}
    for f in sorted(glob.glob(os.path.join(csv_dir, "*.csv"))):
        with open(f, newline="") as fh:
            for r in csv.DictReader(fh):
                m = _FN.search(r["Filename"])
                if not m:
                    continue
                s, off = m.group(1), int(m.group(3))
                b = [float(r[k]) / 4.0 for k in ("MinX", "MinY", "MaxX", "MaxY")]
                out.setdefault(s, {}).setdefault(off, []).append(tuple(b))
    return out


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1]); x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def region_bbox_from_box(alpha_t, T, level, box, grow=20):
    """Bounding box of the connected components of {alpha >= max(level, T)} that touch the (grown) human box."""
    thr = T if level is None else np.maximum(level, T)
    m = (alpha_t >= thr).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    gx0, gy0 = max(x0 - grow, 0), max(y0 - grow, 0)
    gx1, gy1 = min(x1 + grow, seq.W), min(y1 + grow, seq.H)
    ids = set(np.unique(lab[gy0:gy1, gx0:gx1]).tolist()) - {0}
    ids = [k for k in ids if st[k, cv2.CC_STAT_AREA] >= 20]
    if not ids:
        return None
    mm = np.isin(lab, ids)
    ys, xs = np.where(mm)
    return (float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1))


def s4_sequence(res, boxes_for_seq, source="hpwren"):
    """res = pipeline.label_sequence result; boxes_for_seq = {offset: [box...]}. Returns list of rows."""
    pr = res["prep"]
    rows = []
    offs = pr["offsets"]
    for off, bl in sorted(boxes_for_seq.items()):
        t = int(np.argmin(np.abs(offs - off)))
        if abs(offs[t] - off) > 5:
            continue
        for box in bl:
            row = dict(sequence=pr["info"]["name"], source=source, offset=int(off), box=[round(v, 1) for v in box])
            best = (None, -1.0)
            for nm, lv in LEVELS:
                bb = region_bbox_from_box(pr["alpha"][t], pr["T"], lv, box)
                v = 0.0 if bb is None else iou(bb, box)
                row[f"iou_{nm}"] = round(v, 4)
                if v > best[1]:
                    best = (nm, v)
            x0, y0, x1, y1 = [int(round(v)) for v in box]
            inside = pr["alpha"][t][max(y0, 0):y1, max(x0, 0):x1]
            row["alpha_median_in_box"] = float(np.median(inside)) if inside.size else None
            row["alpha_p90_in_box"] = float(np.quantile(inside, 0.9)) if inside.size else None
            row["share_box_above_noise"] = float((inside >= pr["T"][max(y0, 0):y1, max(x0, 0):x1]).mean()) if inside.size else None
            row["effective_level"] = best[0] if best[1] > 0 else None
            row["best_iou"] = round(best[1], 4)
            rows.append(row)
    return rows


def summarise(rows):
    out = dict(n=len(rows))
    if not rows:
        return out
    lv = [r["effective_level"] for r in rows]
    out["effective_level_counts"] = {nm: int(sum(1 for x in lv if x == nm)) for nm, _ in LEVELS}
    out["no_region"] = int(sum(1 for x in lv if x is None))
    b = np.array([r["best_iou"] for r in rows])
    out["best_iou_median"] = float(np.median(b)); out["best_iou_quartiles"] = [float(np.quantile(b, q)) for q in (0.25, 0.75)]
    for nm, _ in LEVELS:
        v = np.array([r[f"iou_{nm}"] for r in rows]); out[f"iou_{nm}_median"] = float(np.median(v))
    am = np.array([r["alpha_median_in_box"] for r in rows if r["alpha_median_in_box"] is not None])
    out["alpha_median_in_box_median"] = float(np.median(am)) if len(am) else None
    out["share_box_above_noise_median"] = float(np.median([r["share_box_above_noise"] for r in rows if r["share_box_above_noise"] is not None]))
    return out

"""S4 on Pyro-SDIS (PyroNear, Apache-2.0, https://huggingface.co/datasets/pyronear/pyro-sdis): human YOLO boxes on the opacity scale.
Background rule (protocol amendment A2): same camera, no box, within 3 days and within 90 minutes of the same time of day, >= 3 images."""
from __future__ import annotations
import glob, io, os
import numpy as np
import pandas as pd
from PIL import Image
from . import pipeline, s4, seq
from .params import get as get_params

PYRO = "/home/user/wildfire 3 (1)/firewitness_raw/pyro-sdis/"


def build_index(pyro_dir=PYRO):
    import pyarrow.parquet as pq
    dfs = []
    for f in sorted(glob.glob(os.path.join(pyro_dir, "*.parquet"))):
        t = pq.read_table(f, columns=["annotations", "image_name", "partner", "camera", "date"]).to_pandas()
        t["file"] = os.path.basename(f); t["row"] = range(len(t))
        dfs.append(t)
    df = pd.concat(dfs, ignore_index=True)
    df["ts"] = pd.to_datetime(df["date"], format="%Y-%m-%dT%H-%M-%S")
    df["has"] = df.annotations.str.strip().str.len() > 0
    df["tod"] = df.ts.dt.hour * 60 + df.ts.dt.minute
    return df.sort_values(["camera", "ts"]).reset_index(drop=True)


def find_events(df, max_gap_h=3, min_boxes=2, min_bg=3, n_bg=10, max_ev=12):
    out = []
    for cam, g in df.groupby("camera"):
        g = g.reset_index(drop=True); cur = []
        evs = []
        for _, r in g.iterrows():
            if r.has:
                if cur and (r.ts - cur[-1].ts).total_seconds() > max_gap_h * 3600:
                    evs.append(cur); cur = []
                cur.append(r)
        if cur:
            evs.append(cur)
        nob = df[(df.camera == cam) & (~df.has)]
        for cur in evs:
            t0 = cur[0].ts
            dd = (nob.ts - t0).abs()
            td = (nob.tod - cur[0].tod).abs(); td = np.minimum(td, 1440 - td)
            ok = nob[(dd <= pd.Timedelta(days=3)) & (td <= 90)].copy()
            if len(cur) >= min_boxes and len(ok) >= min_bg:
                ok["d"] = (ok.ts - t0).abs()
                bg = ok.sort_values("d").head(n_bg).sort_values("ts")
                out.append(dict(camera=cam, event=cur[:max_ev], bg=bg))
    return out


def _decode(row, cache):
    f = row["file"]
    if f not in cache:
        import pyarrow.parquet as pq
        cache.clear()
        cache[f] = pq.read_table(os.path.join(PYRO, f), columns=["image"]).column("image")
    b = cache[f][int(row["row"])].as_py()["bytes"]
    im = Image.open(io.BytesIO(b)).convert("RGB")
    return im.size, np.asarray(im.resize((seq.W, seq.H), Image.BILINEAR))


def boxes_from_yolo(ann):
    out = []
    for l in ann.strip().split("\n"):
        p = l.split()
        if len(p) >= 5:
            xc, yc, w, h = [float(v) for v in p[1:5]]
            out.append(((xc - w / 2) * seq.W, (yc - h / 2) * seq.H, (xc + w / 2) * seq.W, (yc + h / 2) * seq.H))
    return out


def run_event(ev):
    cache = {}
    frames, offsets, boxes = [], [], {}
    nb = len(ev["bg"])
    for i, (_, r) in enumerate(ev["bg"].iterrows()):
        _, a = _decode(r, cache); frames.append(a); offsets.append(-86400 + i)
    t0 = ev["event"][0].ts
    for r in ev["event"]:
        _, a = _decode(r, cache)
        o = int((r.ts - t0).total_seconds()) + 1000
        frames.append(a); offsets.append(o); boxes[o] = boxes_from_yolo(r.annotations)
    sq = dict(frames=np.stack(frames), offsets=np.array(offsets, np.int32), epochs=np.zeros(len(offsets), np.int64),
              name=f"pyro_{ev['camera']}_{t0:%Y%m%dT%H%M%S}")
    p = get_params(min_frames=4, min_pre_frames=3, null_block=1, null_gap=0, pre_end_offset=-1, pre_start_offset=-10 ** 9, max_shift_px=6.0)
    prep = pipeline.prepare(sq, p, pre_idx=np.arange(nb))
    if prep["info"].get("excluded"):
        return [], prep["info"]["excluded"]
    rows = s4.s4_sequence(dict(prep=prep), boxes, source="pyro-sdis")
    return rows, None


def run_all(workers=1):
    df = build_index()
    evs = find_events(df)
    rows, skipped = [], []
    for ev in evs:
        r, why = run_event(ev)
        rows += r
        if why:
            skipped.append((ev["camera"], str(ev["event"][0].ts), why))
    return rows, skipped, len(evs)

"""Duplicate records collapsing into one fire (track records export: results/collapse_examples/*.json)."""
from __future__ import annotations
import glob, json, os
import numpy as np
import cv2
from PIL import Image
from . import draw
from .draw import W, H, OI, FG, MUTED

SRC_COL = {"fpa_fod": OI["sky"], "ics209plus": OI["orange"], "mtbs": OI["green"]}
SRC_LAB = {"fpa_fod": "FPA FOD", "ics209plus": "ICS-209-PLUS", "mtbs": "MTBS"}


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


class Example:
    def __init__(self, path):
        self.d = json.load(open(path))
        self.members = self.d["members"][:4]
        self.merged = self.d["merged"]
        self.pairs = self.d.get("pairs", [])
        self.pos = {}
        for i, m in enumerate(self.members):
            self.pos[m["record_id"]] = (120 + (i % 2) * 1000 - (0 if i % 2 == 0 else 0), 120 + (i // 2) * 265)

    def frame(self, f, nf, idx, total):
        cv = draw.canvas()
        draw.banner(cv, "Duplicate records collapse into one fire", f"{self.d.get('cluster_id', '')}   ({idx + 1} of {total})")
        t = f / max(nf - 1, 1)
        n = len(self.members)
        cw, ch = 680, 205
        merge = ease((t - 0.62) / 0.3)
        tx, ty = 620, 665                          # merged card position
        centres = {}
        for i, m in enumerate(self.members):
            x, y = self.pos[m["record_id"]]
            x = x + (tx - x) * merge; y = y + (ty - y) * merge
            centres[m["record_id"]] = (x + cw // 2, y + ch // 2)
        # links
        lk = ease((t - 0.25) / 0.25)
        for p in self.pairs:
            a, b = centres.get(p["a"]), centres.get(p["b"])
            if a is None or b is None or merge > 0.95:
                continue
            col = OI["yellow"]
            cv2.line(cv, (int(a[0]), int(a[1])), (int(a[0] + (b[0] - a[0]) * lk), int(a[1] + (b[1] - a[1]) * lk)), (0, 0, 0), 9)
            cv2.line(cv, (int(a[0]), int(a[1])), (int(a[0] + (b[0] - a[0]) * lk), int(a[1] + (b[1] - a[1]) * lk)), col, 5)
            if lk > 0.9:
                mx, my = int((a[0] + b[0]) / 2), int((a[1] + b[1]) / 2)
                draw.text(cv, (mx + 18, my - 18), f"same fire: {p['probability'] * 100:.2f}%", 28, FG, True, stroke=4)
        for i, m in enumerate(self.members):
            x, y = self.pos[m["record_id"]]
            x = int(x + (tx - x) * merge); y = int(y + (ty - y) * merge)
            col = SRC_COL.get(m["source"], OI["grey"])
            cv2.rectangle(cv, (x, y), (x + cw, y + ch), (34, 37, 47), -1)
            cv2.rectangle(cv, (x, y), (x + cw, y + ch), col, 6)
            draw.text(cv, (x + 20, y + 12), SRC_LAB.get(m["source"], m["source"]), 30, col, True)
            draw.text(cv, (x + 20, y + 56), str(m.get("name") or "(no name)"), 40, FG, True)
            ac = m.get("acres")
            draw.text(cv, (x + 20, y + 112), f"{m['date']}   {m.get('state', '')}", 30, FG)
            draw.text(cv, (x + 20, y + 150), (f"{ac:,.0f} acres" if ac is not None else "acres: n/a") + f"   ({m['lat']:.3f}, {m['lon']:.3f})", 26, MUTED)
        # merged card
        if merge > 0.9:
            mg = self.merged
            x, y = tx, ty
            cv2.rectangle(cv, (x - 10, y - 10), (x + cw + 10, y + ch + 40), (34, 37, 47), -1)
            cv2.rectangle(cv, (x - 10, y - 10), (x + cw + 10, y + ch + 40), OI["vermillion"], 8)
            draw.text(cv, (x + 20, y + 4), "ONE FIRE", 30, OI["vermillion"], True)
            draw.text(cv, (x + 20, y + 48), str(mg.get("name") or "(no name)"), 44, FG, True)
            draw.text(cv, (x + 20, y + 108), f"{mg['date']}   {mg.get('state', '')}", 32, FG)
            ac = mg.get("acres")
            draw.text(cv, (x + 20, y + 148), (f"{ac:,.0f} acres" if ac is not None else "acres: n/a") + f"   from {mg.get('n_sources', n)} sources", 30, MUTED)
            draw.text(cv, (x + 20, y + 196), "permanent ID " + str(self.d.get("cluster_id", "")), 26, MUTED)
        cap = f"{n} records from different sources describe the same fire; the linker joins them and keeps the raw records unchanged."
        draw.caption(cv, draw.wrap(cap, 32, W - 60), 30, 945, 32)
        draw.footer(cv, credit="Records: FPA FOD (USFS), ICS-209-PLUS, MTBS (USGS/USFS); linker: track records")
        cv[H - 8:H, :] = (40, 44, 54); cv[H - 8:H, :int(W * (idx + t) / total)] = OI["sky"]
        return cv


def render_collapse(d, out_mp4, per=4.0, max_ex=6, fps=30, gif=True, stills=True, crf=28):
    files = sorted(glob.glob(os.path.join(d, "*.json")))
    exs = [Example(p) for p in files if len(json.load(open(p)).get("members", [])) >= 2][:max_ex]
    if not exs:
        raise SystemExit("no collapse examples in " + d)
    wr = draw.Writer(out_mp4, fps, crf)
    sd = os.path.splitext(out_mp4)[0] + "_stills"
    if stills:
        os.makedirs(sd, exist_ok=True)
    nf = int(per * fps)
    for i, ex in enumerate(exs):
        for f in range(nf):
            cv = ex.frame(f, nf, i, len(exs)); wr.write(cv)
            if stills and f in (int(nf * 0.45), int(nf * 0.95)) and i == 0:
                Image.fromarray(cv).save(os.path.join(sd, f"collapse_{f:03d}.png"))
    wr.close()
    if gif:
        draw.to_gif(out_mp4, os.path.splitext(out_mp4)[0] + ".gif")
    n, dur, w, h, ok = draw.probe(out_mp4)
    return dict(path=out_mp4, frames=n, seconds=round(dur, 2), size=f"{w}x{h}", decodes_start_to_end=ok, examples=len(exs))

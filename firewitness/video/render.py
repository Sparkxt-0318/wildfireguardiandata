"""Render a labelled FIgLib sequence: layouts a (raw + opacity + nested edges), b (vector), c (timeline), d (classes).
Credit burnt into every frame: HPWREN, http://hpwren.ucsd.edu/"""
from __future__ import annotations
import json, os
import numpy as np
import cv2
from PIL import Image
from . import draw
from .draw import W, H, OI, FG, MUTED, BG

LEVEL_NAMES = ["noise level", "0.10", "0.20", "0.40", "0.60"]
S = 512  # label working width


class Clip:
    def __init__(self, seq_dir, labels_dir, display=(1024, 768)):
        from ..smoke import seq
        self.seq_dir = seq_dir
        self.meta = json.load(open(os.path.join(labels_dir, "labels.json")))
        if self.meta.get("excluded"):
            raise SystemExit("sequence was excluded: %s" % self.meta["excluded"])
        z = np.load(os.path.join(labels_dir, "opacity.npz"))
        self.alpha = z["alpha"].astype(np.float32) / 255.0
        self.T = z["noise_threshold"].astype(np.float32) / 255.0
        self.classes = z["classes"]; self.offsets = z["offsets"]
        self.edges = json.load(open(os.path.join(labels_dir, "edges.json")))
        self.n = len(self.offsets)
        self.raw = []
        for off, ep, f in seq.list_frames(seq_dir):
            im = Image.open(f); im.draft("RGB", display); im = im.convert("RGB")
            if im.size != display:
                im = im.resize(display, Image.BILINEAR)
            self.raw.append(np.asarray(im))
        assert len(self.raw) == self.n, "labels do not match the sequence"
        self.name = self.meta["name"]
        smoke = [c for c in self.meta["chains"] if c["cls"] == "smoke"]
        self.main = max(smoke, key=lambda c: c["mass"]) if smoke else None
        self.first = self.meta.get("first_smoke_offset_s")
        self.area_all = (self.classes > 0).reshape(self.n, -1).sum(1).astype(float)
        self.area_smoke = (self.classes == 1).reshape(self.n, -1).sum(1).astype(float)
        self._prep = None; self._vec = {}

    # --- time mapping
    def pos(self, f, nf):
        p = f / max(nf - 1, 1) * (self.n - 1)
        i = int(np.floor(p)); i = min(i, self.n - 2) if self.n > 1 else 0
        return i, p - i, int(round(p))

    def raw_at(self, i, w):
        a = self.raw[i].astype(np.float32); b = self.raw[min(i + 1, self.n - 1)].astype(np.float32)
        return ((1 - w) * a + w * b).astype(np.uint8)

    def alpha_at(self, i, w):
        return (1 - w) * self.alpha[i] + w * self.alpha[min(i + 1, self.n - 1)]

    def time_label(self, k):
        o = int(self.offsets[k])
        return f"t = {o // 60:+d} min  ({o:+d} s from the human first-smoke label)"

    def prep(self):
        if self._prep is None:
            from ..smoke import pipeline, seq
            self._prep = pipeline.prepare(seq.load_sequence(self.seq_dir), self.meta["params"])
        return self._prep

    def vector(self, k):
        if k not in self._vec:
            from ..smoke import vector
            att = (self.classes[k] == 1)
            self._vec[k] = vector.vector_frame(self.prep(), k, att)
        return self._vec[k]

    # --- shared pieces
    def progress(self, cv, frac):
        cv[H - 8:H, :] = (40, 44, 54)
        cv[H - 8:H, :int(W * frac)] = OI["sky"]

    def raw_panel(self, k, i, w, pw, ph, marker=True):
        img = cv2.resize(self.raw_at(i, w), (pw, ph), interpolation=cv2.INTER_AREA)
        if marker and self.main and self.offsets[k] >= self.first:
            cx, cy = self.main["seed_xy"]
            p = (int(cx / S * pw), int(cy / S * pw))
            cv2.circle(img, p, 26, (0, 0, 0), 7, cv2.LINE_AA); cv2.circle(img, p, 26, OI["yellow"], 4, cv2.LINE_AA)
        return img

    def opacity_panel(self, k, i, w, pw, ph, contours=True):
        a = self.alpha_at(i, w)
        img = draw.apply_cmap(cv2.resize(a, (pw, ph), interpolation=cv2.INTER_LINEAR), "cividis", 0, 1)
        if contours:
            e = self.edges[str(int(self.offsets[k]))]
            for nm, col in zip(["noise", "0.10", "0.20", "0.40", "0.60"], draw.LEVEL_COLOURS):
                draw.draw_contours(img, e.get(nm, []), col, 3, pw / S)
        return img

    # --- layouts
    def frame_a(self, f, nf):
        i, w, k = self.pos(f, nf)
        cv = draw.canvas()
        draw.banner(cv, "A  Opacity map and nested edges", self.name)
        pw, ph = 920, 690
        draw.put(cv, self.raw_panel(k, i, w, pw, ph), 20, 104)
        draw.put(cv, self.opacity_panel(k, i, w, pw, ph), 980, 104)
        draw.text(cv, (28, 112), "camera frame", 34, FG, True, stroke=3)
        draw.text(cv, (988, 112), "opacity of the smoke veil (0 clear, 1 opaque)", 34, FG, True, stroke=3)
        lines = draw.wrap("Opacity is how much the smoke dims and veils the camera's own smoke-free background. "
                          "Each coloured line is one edge: a contour of the map at a stated opacity.", 40, W - 80)
        draw.caption(cv, lines, 30, 808, 40)
        draw.line_swatch_legend(cv, list(zip(draw.LEVEL_COLOURS, ["noise floor", "0.10", "0.20", "0.40", "0.60"])), 30, 928, 32)
        draw.text(cv, (W - 30, 936), self.time_label(k), 30, MUTED, anchor="ra")
        draw.footer(cv); self.progress(cv, f / max(nf - 1, 1))
        return cv

    def frame_b(self, f, nf):
        i, w, k = self.pos(f, nf)
        cv = draw.canvas()
        draw.banner(cv, "B  Seven measured variables per pixel", self.name)
        draw.put(cv, self.raw_panel(k, i, w, 1000, 750), 20, 104)
        v = self.vector(k)
        region = (self.classes[k] > 0)
        names = [("opacity", "cividis", 0, 1), ("colour shift", "magma", 0, 0.15), ("texture loss", "viridis", 0, 1),
                 ("speed, px/min", "viridis", 0, 40), ("direction", "twilight", 0, 360), ("attached to source", "cividis", 0, 1),
                 ("growth /min", "PuOr", -0.2, 0.2)]
        pw, ph = 280, 210
        for j, (nm, cm, lo, hi) in enumerate(names):
            r, c = divmod(j, 3)
            x, y = 1040 + c * 292, 104 + r * 252
            ch = v[j].copy()
            ch[~region] = np.nan
            img = draw.apply_cmap(cv2.resize(ch, (pw, ph), interpolation=cv2.INTER_NEAREST), cm, lo, hi)
            draw.put(cv, img, x, y + 38)
            draw.text(cv, (x, y), nm, 30, FG, True)
        # legend cell
        draw.text(cv, (1040 + 2 * 292, 104 + 2 * 252), "grey = below the", 28, MUTED)
        draw.text(cv, (1040 + 2 * 292, 104 + 2 * 252 + 34), "noise level", 28, MUTED)
        lines = draw.wrap("Each pixel carries a vector of measurements. Classes are plain-sentence rules on this vector; "
                          "no trained model decides a class.", 40, W - 80)
        draw.caption(cv, lines, 30, 880, 40)
        draw.text(cv, (W - 30, 972), self.time_label(k), 30, MUTED, anchor="ra")
        draw.footer(cv); self.progress(cv, f / max(nf - 1, 1))
        return cv

    def frame_c(self, f, nf):
        i, w, k = self.pos(f, nf)
        cv = draw.canvas()
        draw.banner(cv, "C  First smoke: this method and the human label", self.name)
        pw, ph = 800, 600
        draw.put(cv, self.raw_panel(k, i, w, pw, ph), 60, 100)
        draw.put(cv, self.opacity_panel(k, i, w, pw, ph), 1060, 100)
        txt = (f"This method: first smoke at {self.first:+d} s." if self.first is not None else "This method: no smoke confirmed.") + "  Human label: 0 s."
        draw.text(cv, (60, 712), txt, 44, FG, True)
        # timeline
        x0, x1, y0, y1 = 150, 1850, 800, 990
        o0, o1 = float(self.offsets[0]), float(self.offsets[-1])
        def X(o): return int(x0 + (o - o0) / (o1 - o0) * (x1 - x0))
        cv[y0:y1 + 1, x0:x1 + 1] = (30, 33, 42)
        mx = max(self.area_all.max(), 1.0)
        for arr, col, th in [(self.area_all, OI["grey"], 3), (self.area_smoke, OI["vermillion"], 5)]:
            pts = np.array([[X(self.offsets[j]), int(y1 - (arr[j] / mx) * (y1 - y0 - 10))] for j in range(self.n)], np.int32)
            cv2.polylines(cv, [pts], False, col, th, cv2.LINE_AA)
        for o in range(int(np.ceil(o0 / 600) * 600), int(o1) + 1, 600):
            cv2.line(cv, (X(o), y1), (X(o), y1 + 10), MUTED, 2)
            draw.text(cv, (X(o), y1 + 12), f"{o // 60:+d}", 26, MUTED, anchor="ma")
        draw.text(cv, (x0 - 10, y0), "area above", 24, MUTED, anchor="ra"); draw.text(cv, (x0 - 10, y0 + 26), "noise", 24, MUTED, anchor="ra")
        draw.text(cv, (x1, y1 + 40), "minutes from the human first-smoke label", 24, MUTED, anchor="ra")
        for o, col, lab, dy in [(0, OI["blue"], "human label 0 s", 0), (self.first, OI["yellow"], None, 34)]:
            if o is None:
                continue
            cv2.line(cv, (X(o), y0 - 6), (X(o), y1), (0, 0, 0), 9); cv2.line(cv, (X(o), y0 - 6), (X(o), y1), col, 5)
        draw.text(cv, (X(0) + 12, y0 - 38), "human label", 30, OI["blue"], True, stroke=2)
        if self.first is not None:
            left = self.first < 0
            draw.text(cv, (X(self.first) + (-12 if left else 12), y0 - 38 - (0 if abs(self.first) > 500 else 36)),
                      "this method", 30, OI["yellow"], True, anchor="ra" if left else "la", stroke=2)
        cx = X(float(self.offsets[k]))
        cv2.line(cv, (cx, y0), (cx, y1), FG, 2, cv2.LINE_AA)
        draw.text(cv, (W - 30, 722), self.time_label(k), 28, MUTED, anchor="ra")
        draw.footer(cv, extra="grey: all regions above noise; vermillion: smoke class"); self.progress(cv, f / max(nf - 1, 1))
        return cv

    def frame_d(self, f, nf):
        i, w, k = self.pos(f, nf)
        cv = draw.canvas()
        draw.banner(cv, "D  Classes from plain rules", self.name)
        pw, ph = 920, 690
        raw = self.raw_panel(k, i, w, pw, ph, marker=False).astype(np.float32)
        cm = cv2.resize(self.classes[k], (pw, ph), interpolation=cv2.INTER_NEAREST)
        order = ["none", "smoke", "cloud", "haze_fog", "dust", "other"]
        present = []
        for ci, nm in enumerate(order):
            if ci == 0:
                continue
            m = cm == ci
            if m.any():
                present.append(nm)
                col = np.array(draw.CLASS_COLOURS[nm], np.float32)
                raw[m] = 0.45 * raw[m] + 0.55 * col
        img = raw.astype(np.uint8)
        for ci, nm in enumerate(order):
            if ci and (cm == ci).any():
                cs, _ = cv2.findContours((cm == ci).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(img, cs, -1, (0, 0, 0), 4, cv2.LINE_AA); cv2.drawContours(img, cs, -1, draw.CLASS_COLOURS[nm], 2, cv2.LINE_AA)
        draw.put(cv, img, 20, 104)
        draw.put(cv, self.opacity_panel(k, i, w, pw, ph, contours=False), 980, 104)
        draw.text(cv, (28, 112), "classes", 34, FG, True, stroke=3); draw.text(cv, (988, 112), "opacity", 34, FG, True, stroke=3)
        rules = {}
        for c in self.meta["chains"]:
            rules.setdefault(c["cls"], c["rule"])
        from ..smoke.pipeline import RULES
        shown = None
        for nm in ["smoke", "dust", "cloud", "haze_fog", "other"]:
            if nm in present:
                shown = nm; break
        if shown is None:
            line = "No region above the noise level at this time."
            col = MUTED
        else:
            line = f"{draw.CLASS_LABEL[shown].capitalize()}: " + RULES[shown].split(" is ", 1)[0] + " is " + RULES[shown].split(" is ", 1)[1] if " is " in RULES[shown] else RULES[shown]
            col = draw.CLASS_COLOURS[shown]
        draw.caption(cv, draw.wrap(line, 40, W - 80), 30, 808, 40, colour=FG)
        draw.swatch_legend(cv, [(draw.CLASS_COLOURS[n], draw.CLASS_LABEL[n]) for n in ["smoke", "cloud", "haze_fog", "dust", "other"]], 30, 940, 32)
        draw.text(cv, (W - 30, 944), self.time_label(k), 28, MUTED, anchor="ra")
        draw.footer(cv); self.progress(cv, f / max(nf - 1, 1))
        return cv

    def title_card(self, f, nf, lines):
        cv = draw.canvas()
        y = 300
        for s, size, bold in lines:
            draw.text(cv, (W // 2, y), s, size, FG, bold, anchor="ma"); y += int(size * 1.5)
        draw.footer(cv)
        return cv


def render_clip(seq_dir, labels_dir, out_mp4, layout="all", seconds=None, fps=30, gif=True, stills=True, crf=28):
    clip = Clip(seq_dir, labels_dir)
    fns = dict(a=clip.frame_a, b=clip.frame_b, c=clip.frame_c, d=clip.frame_d)
    if layout == "all":
        acts = [("title", 2.5), ("a", 8), ("b", 7), ("c", 8), ("d", 8)]
    else:
        acts = [(layout, seconds or 24)]
    wr = draw.Writer(out_mp4, fps, crf)
    still_dir = os.path.splitext(out_mp4)[0] + "_stills"
    if stills:
        os.makedirs(still_dir, exist_ok=True)
    parts = clip.name.split("_")
    date = parts[0]; cam = parts[-1]
    for act, sec in acts:
        nf = int(sec * fps)
        for f in range(nf):
            if act == "title":
                cv = clip.title_card(f, nf, [("Smoke as a measured opacity map", 76, True), (f"Sequence {clip.name}", 44, False),
                                             (f"{date[:4]}-{date[4:6]}-{date[6:]}  camera {cam}", 40, False),
                                             ("No trained model decides a class", 40, False)])
            else:
                cv = fns[act](f, nf)
            wr.write(cv)
            if stills and act != "title" and f == int(nf * 0.75):
                Image.fromarray(cv).save(os.path.join(still_dir, f"{act}.png"))
    wr.close()
    if gif:
        draw.to_gif(out_mp4, os.path.splitext(out_mp4)[0] + ".gif")
    return probe_ok(out_mp4)


def probe_ok(mp4):
    n, dur, w, h, ok = draw.probe(mp4)
    return dict(path=mp4, frames=n, seconds=round(dur, 2), size=f"{w}x{h}", decodes_start_to_end=ok)

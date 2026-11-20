"""Known-truth demo (test S1): composite smoke of known opacity over real smoke-free frames, the truth contours and the
estimated contours side by side. Credit: HPWREN, http://hpwren.ucsd.edu/ (background frames)."""
from __future__ import annotations
import os
import numpy as np
import cv2
from PIL import Image
from . import draw
from .draw import W, H, OI, FG, MUTED
from ..smoke import s1 as S1, pipeline, seq

LEVELS = [("0.10", 0.10), ("0.20", 0.20), ("0.40", 0.40)]


def contours(a, lv):
    cs, _ = cv2.findContours((a >= lv).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    return [c.reshape(-1, 2).tolist() for c in cs if len(c) >= 4 and cv2.contourArea(c) >= 8]


def render_truth(seq_dir, out_mp4, amax=0.6, endm="grey055", k=0, seconds=24, fps=30, gif=True, stills=True, crf=28):
    sq = seq.load_sequence(seq_dir)
    frames, a_true, src = S1.make_case(sq, k, amax, endm)
    p = pipeline.get_params(min_frames=30)
    s2 = dict(frames=frames, offsets=sq["offsets"][:len(frames)], epochs=sq["epochs"][:len(frames)], name=sq["name"])
    r = pipeline.label_sequence(s2, p, pre_idx=np.arange(0, S1.PRE_END + 1))
    pr = r["prep"]; al = pr["alpha"]
    ts = list(range(S1.START, len(frames)))
    errs = {}
    for nm, lv in LEVELS:
        errs[nm] = [S1.boundary_dist(a_true[t] >= lv, (al[t] >= np.maximum(lv, pr["T"])) &
                                     cv2.dilate((a_true[t] > 0.005).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (81, 81))).astype(bool))
                    for t in ts]
    wr = draw.Writer(out_mp4, fps, crf)
    sd = os.path.splitext(out_mp4)[0] + "_stills"
    if stills:
        os.makedirs(sd, exist_ok=True)
    nf = int(seconds * fps)
    pw, ph = 600, 450
    cols = [OI["yellow"], OI["orange"], OI["vermillion"]]
    for f in range(nf):
        p_ = f / max(nf - 1, 1) * (len(ts) - 1)
        i = int(np.floor(p_)); i = min(i, len(ts) - 2); w = p_ - i
        t = ts[int(round(p_))]
        cv = draw.canvas()
        draw.banner(cv, "Known truth: a planted plume", sq["name"])
        raw = cv2.resize(frames[t], (pw, ph), interpolation=cv2.INTER_AREA)
        at = cv2.resize(a_true[t], (pw, ph)); ae = cv2.resize(al[t], (pw, ph))
        imT = draw.apply_cmap(at, "cividis", 0, 1); imE = draw.apply_cmap(ae, "cividis", 0, 1)
        for (nm, lv), col in zip(LEVELS, cols):
            draw.draw_contours(imT, [[[x * pw / seq.W, y * ph / seq.H] for x, y in c] for c in contours(a_true[t], lv)], col, 3)
            draw.draw_contours(imE, [[[x * pw / seq.W, y * ph / seq.H] for x, y in c] for c in contours(al[t], lv)], col, 3)
        for j, (img, lab) in enumerate([(raw, "composite frame (real camera + planted plume)"), (imT, "planted opacity (truth)"), (imE, "opacity measured by the method")]):
            x = 20 + j * 630
            draw.put(cv, img, x, 130)
            draw.text(cv, (x, 100), lab, 26, FG, True)
        draw.line_swatch_legend(cv, [(c, f"edge at {nm}") for (nm, _), c in zip(LEVELS, cols)], 30, 610, 32)
        e = [np.nanmean([x for x in errs[nm][:int(round(p_)) + 1] if np.isfinite(x)] or [np.nan]) for nm, _ in LEVELS]
        draw.text(cv, (30, 680), "Mean edge position error so far (pixels at 512 x 384): " + ",  ".join(f"{nm}: {v:.1f}" for (nm, _), v in zip(LEVELS, e) if np.isfinite(v)), 32, FG)
        sm = r["first_frame"]
        msg = f"Planted opacity at most {amax}, smoke colour {endm}. The truth is never used to fit the method."
        draw.caption(cv, draw.wrap(msg, 36, W - 60), 30, 760, 36)
        found = "smoke found from the planted frame" if (r["main"] is not None and r["first_frame"] == S1.START) else ("smoke found" if r["main"] is not None else "not found")
        draw.text(cv, (30, 880), f"Result for this case: {found}.", 40, OI["yellow"], True)
        draw.footer(cv); cv[H - 8:H, :] = (40, 44, 54); cv[H - 8:H, :int(W * f / max(nf - 1, 1))] = OI["sky"]
        wr.write(cv)
        if stills and f == int(nf * 0.85):
            Image.fromarray(cv).save(os.path.join(sd, "truth.png"))
    wr.close()
    if gif:
        draw.to_gif(out_mp4, os.path.splitext(out_mp4)[0] + ".gif")
    n, dur, ww, hh, ok = draw.probe(out_mp4)
    return dict(path=out_mp4, frames=n, seconds=round(dur, 2), size=f"{ww}x{hh}", decodes_start_to_end=ok)

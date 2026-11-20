"""Before-and-after scar pairs (track caught export): swipe from the pre chip to the post chip, scar outline, dNBR.
Expected: <dir>/scar_pairs/<rid>/{pre.png, post.png, mask.png, dnbr.png, meta.json} (or <dir>/<rid>/...) and optional INDEX.json."""
from __future__ import annotations
import glob, json, os
import numpy as np
import cv2
from PIL import Image
from . import draw
from .draw import W, H, OI, FG, MUTED


def find_pairs(d):
    root = os.path.join(d, "scar_pairs") if os.path.isdir(os.path.join(d, "scar_pairs")) else d
    out = []
    for m in sorted(glob.glob(os.path.join(root, "*", "meta.json"))):
        p = os.path.dirname(m)
        if all(os.path.exists(os.path.join(p, f)) for f in ("pre.png", "post.png", "mask.png")):
            out.append(p)
    return out


class Pair:
    def __init__(self, p):
        self.meta = json.load(open(os.path.join(p, "meta.json")))
        ld = lambda n: np.asarray(Image.open(os.path.join(p, n)).convert("RGB"))
        self.pre, self.post = ld("pre.png"), ld("post.png")
        self.mask = np.asarray(Image.open(os.path.join(p, "mask.png")).convert("L")) > 127
        self.dnbr = ld("dnbr.png") if os.path.exists(os.path.join(p, "dnbr.png")) else None
        self.name = self.meta.get("fire_name") or "unnamed fire"
        self.rid = self.meta.get("rid", os.path.basename(p))
        cs, _ = cv2.findContours(self.mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.cs = [c.reshape(-1, 2).astype(np.float32) for c in cs if len(c) >= 4]
        self.area_ha = float(self.mask.sum() * 20 * 20 / 10000.0)    # 20 m pixels

    def frame(self, f, nf, idx, total):
        cv = draw.canvas()
        draw.banner(cv, "Before and after: where the burn scar is", f"{self.rid}   ({idx + 1} of {total})")
        S = 760
        up = lambda im: cv2.resize(im, (S, S), interpolation=cv2.INTER_CUBIC)
        pre, post = up(self.pre), up(self.post)
        t = f / max(nf - 1, 1)
        if t < 0.55:
            x = int(S * (t / 0.55))                      # swipe pre -> post
            img = pre.copy(); img[:, :x] = post[:, :x]
            cv2.line(img, (x, 0), (x, S), (0, 0, 0), 9); cv2.line(img, (x, 0), (x, S), FG, 4)
            label = f"swipe: after on the left of the line, before on the right"
        else:
            img = post.copy()
            label = "after, with the scar outline"
        if t >= 0.5:
            a = min((t - 0.5) / 0.2, 1.0)
            ov = img.copy()
            sc = S / self.mask.shape[1]
            for c in self.cs:
                pts = (c * sc).astype(np.int32).reshape(-1, 1, 2)
                cv2.polylines(ov, [pts], True, (0, 0, 0), 9, cv2.LINE_AA); cv2.polylines(ov, [pts], True, OI["yellow"], 5, cv2.LINE_AA)
            img = cv2.addWeighted(ov, a, img, 1 - a, 0)
        draw.put(cv, img, 30, 110)
        draw.text(cv, (38, 118), label, 28, FG, True, stroke=3)
        if self.dnbr is not None:
            draw.put(cv, cv2.resize(self.dnbr, (420, 420), interpolation=cv2.INTER_CUBIC), 820, 110)
            draw.text(cv, (820, 80 + 0), "", 1)
            draw.text(cv, (830, 118), "burn signal (dNBR)", 28, FG, True, stroke=3)
        m = self.meta
        x0 = 1280 if self.dnbr is not None else 820
        info = [("fire", self.name), ("before", str(m.get("pre_date", ""))), ("after", str(m.get("post_date", ""))),
                ("scar area", f"{self.area_ha:,.0f} ha"), ("median dNBR", f"{m['score_median_dnbr']:.2f}" if m.get("score_median_dnbr") is not None else "n/a"),
                ("tier", str(m.get("tier", "")))]
        y = 112
        for k, v in info:
            draw.text(cv, (x0, y), k, 24, MUTED); draw.text(cv, (x0, y + 26), v, 34, FG, True); y += 82
        cap = draw.wrap("Pixels the scar finder accepts as burned are outlined in yellow. Chips are Sentinel-2 at 20 m.", 32, W - 60)
        draw.caption(cv, cap, 30, 905, 32)
        draw.footer(cv, credit="Imagery: Copernicus Sentinel-2 (ESA); scar finder: track caught", extra=str(m.get("method", ""))[:70])
        cv[H - 8:H, :] = (40, 44, 54); cv[H - 8:H, :int(W * (idx + t) / total)] = OI["sky"]
        return cv


def render_scars(d, out_mp4, per_pair=4.0, max_pairs=6, fps=30, gif=True, stills=True, crf=28):
    pairs = [Pair(p) for p in find_pairs(d)[:max_pairs]]
    if not pairs:
        raise SystemExit("no scar pairs found in " + d)
    wr = draw.Writer(out_mp4, fps, crf)
    sd = os.path.splitext(out_mp4)[0] + "_stills"
    if stills:
        os.makedirs(sd, exist_ok=True)
    nf = int(per_pair * fps)
    for i, pr in enumerate(pairs):
        for f in range(nf):
            cv = pr.frame(f, nf, i, len(pairs)); wr.write(cv)
            if stills and f == int(nf * 0.85) and i < 3:
                Image.fromarray(cv).save(os.path.join(sd, f"scar_{i}.png"))
    wr.close()
    if gif:
        draw.to_gif(out_mp4, os.path.splitext(out_mp4)[0] + ".gif")
    n, dur, w, h, ok = draw.probe(out_mp4)
    return dict(path=out_mp4, frames=n, seconds=round(dur, 2), size=f"{w}x{h}", decodes_start_to_end=ok, pairs=len(pairs))

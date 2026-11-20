"""Drawing helpers for the video tool: 1080p canvas, big captions, colour-blind-safe palette (Okabe-Ito + cividis)."""
from __future__ import annotations
import os, subprocess, shutil
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
CREDIT = "Image data: HPWREN, http://hpwren.ucsd.edu/"

# Okabe-Ito (colour-blind safe)
OI = dict(black=(0, 0, 0), orange=(230, 159, 0), sky=(86, 180, 233), green=(0, 158, 115), yellow=(240, 228, 66),
          blue=(0, 114, 178), vermillion=(213, 94, 0), purple=(204, 121, 167), grey=(153, 153, 153), white=(255, 255, 255))
LEVEL_COLOURS = [OI["sky"], OI["yellow"], OI["orange"], OI["vermillion"], OI["purple"]]   # noise, .10, .20, .40, .60
CLASS_COLOURS = {"smoke": OI["vermillion"], "cloud": OI["sky"], "haze_fog": OI["green"], "dust": OI["orange"], "other": OI["grey"]}
CLASS_LABEL = {"smoke": "smoke", "cloud": "cloud", "haze_fog": "haze or fog", "dust": "dust", "other": "other"}
BG = (18, 20, 26)
FG = (245, 245, 245)
MUTED = (170, 175, 185)

_FONTS = {}


def _font_path(bold):
    names = (["Inter-SemiBold.otf", "Inter-Bold.otf"] if bold else ["Inter-Regular.otf"])
    for d in ["/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter"]:
        for n in names:
            if os.path.exists(os.path.join(d, n)):
                return os.path.join(d, n)
    import matplotlib
    f = os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
    return f


def font(size, bold=False):
    k = (size, bold)
    if k not in _FONTS:
        _FONTS[k] = ImageFont.truetype(_font_path(bold), size)
    return _FONTS[k]


def canvas():
    return np.full((H, W, 3), BG, np.uint8)


def lut(name):
    import matplotlib
    cm = matplotlib.colormaps[name]
    return (cm(np.linspace(0, 1, 256))[:, :3] * 255).astype(np.uint8)


_LUTS = {}


def apply_cmap(x, name, vmin=0.0, vmax=1.0, nan_colour=(40, 42, 50)):
    if name not in _LUTS:
        _LUTS[name] = lut(name)
    x = np.asarray(x, np.float32)
    bad = ~np.isfinite(x)
    v = np.clip((np.where(bad, vmin, x) - vmin) / max(vmax - vmin, 1e-9), 0, 1)
    out = _LUTS[name][(v * 255).astype(np.uint8)]
    out[bad] = nan_colour
    return out


def put(cv, img, x, y, w=None, h=None):
    """Paste RGB image at (x, y), resized to (w, h) if given."""
    if w is not None:
        img = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA if img.shape[1] > w else cv2.INTER_NEAREST if img.shape[1] * 3 < w else cv2.INTER_LINEAR)
    hh, ww = img.shape[:2]
    cv[y:y + hh, x:x + ww] = img
    return cv


def text(cv, xy, s, size=40, colour=FG, bold=False, anchor="la", stroke=0, stroke_colour=(0, 0, 0)):
    im = Image.fromarray(cv)
    d = ImageDraw.Draw(im)
    d.text(xy, s, font=font(size, bold), fill=colour, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_colour)
    cv[:] = np.asarray(im)
    return cv


def wrap(s, size, max_w, bold=False):
    f = font(size, bold)
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.getlength(t) <= max_w:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def caption(cv, lines, x, y, size=44, colour=FG, line_gap=1.25, bold=False):
    for i, ln in enumerate(lines):
        text(cv, (x, int(y + i * size * line_gap)), ln, size, colour, bold)
    return cv


def banner(cv, title, sub=None):
    cv[0:92] = (28, 31, 40)
    text(cv, (30, 14), title, 52, FG, True)
    if sub:
        text(cv, (W - 30, 30), sub, 34, MUTED, False, anchor="ra")
    return cv


def footer(cv, credit=CREDIT, extra=None):
    text(cv, (30, H - 40), credit, 26, MUTED)
    if extra:
        text(cv, (W - 30, H - 40), extra, 26, MUTED, anchor="ra")
    return cv


def swatch_legend(cv, items, x, y, size=34, gap=14, colw=64):
    """items: list of (rgb, label). Horizontal layout."""
    for rgb, lab in items:
        cv2.rectangle(cv, (x, y + 6), (x + colw, y + size - 2), rgb, -1)
        cv2.rectangle(cv, (x, y + 6), (x + colw, y + size - 2), (255, 255, 255), 1)
        text(cv, (x + colw + 12, y), lab, size, FG)
        x += colw + 12 + int(font(size).getlength(lab)) + 36
    return cv


def line_swatch_legend(cv, items, x, y, size=34):
    for rgb, lab in items:
        cv2.line(cv, (x, y + size // 2 + 3), (x + 60, y + size // 2 + 3), (0, 0, 0), 9, cv2.LINE_AA)
        cv2.line(cv, (x, y + size // 2 + 3), (x + 60, y + size // 2 + 3), rgb, 5, cv2.LINE_AA)
        text(cv, (x + 74, y), lab, size, FG)
        x += 74 + int(font(size).getlength(lab)) + 34
    return cv


def draw_contours(img, polys, colour, thick=3, scale=1.0):
    """Draw polygons (list of [[x,y],...]) with a dark under-stroke so lines read on any background."""
    for pl in polys:
        pts = (np.array(pl, np.float32) * scale).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [pts], True, (0, 0, 0), thick + 3, cv2.LINE_AA)
    for pl in polys:
        pts = (np.array(pl, np.float32) * scale).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [pts], True, colour, thick, cv2.LINE_AA)
    return img


class Writer:
    """Pipe RGB frames to ffmpeg (libx264, yuv420p, faststart)."""
    def __init__(self, path, fps=30, crf=27, preset="medium"):
        self.path = path
        self.p = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
             "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart",
             "-threads", "1", "-r", str(fps), path], stdin=subprocess.PIPE)
        self.n = 0

    def write(self, frame):
        self.p.stdin.write(np.ascontiguousarray(frame).tobytes()); self.n += 1

    def close(self):
        self.p.stdin.close(); self.p.wait()
        return self.n


def to_gif(mp4, gif, width=640, fps=10):
    pal = gif + ".pal.png"
    vf = f"fps={fps},scale={width}:-1:flags=lanczos"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-vf", vf + ",palettegen=max_colors=128", pal], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-i", pal, "-lavfi", vf + "[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4", gif], check=True)
    os.remove(pal)


def probe(mp4):
    """Frames decodable from start to end: returns (n_frames, duration_s, width, height)."""
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_frames,width,height,duration", "-of", "default=nw=1", mp4], capture_output=True, text=True).stdout
    d = dict(l.split("=") for l in out.split())
    dec = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-f", "null", "-"], capture_output=True, text=True)
    return int(d["nb_read_frames"]), float(d.get("duration", 0)), int(d["width"]), int(d["height"]), dec.stderr.strip() == ""

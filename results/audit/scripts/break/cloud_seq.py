"""Build smoke-free sequences from the 40 pre-ignition frames of one FIgLib sequence (played forward then
backward, 81 frames, offsets -2400..+2400). Variant 'cloud': from offset -600 on, a bright, soft cloud bank
moves across the sky at about 1/6 of the frame width per minute (fast cloud). Variant 'plain': no cloud."""
import sys, os, numpy as np
from PIL import Image
src, out, variant = sys.argv[1], sys.argv[2], sys.argv[3]
fr = sorted([f for f in os.listdir(src) if f.endswith(".jpg") and "_-" in f], key=lambda f: int(f.split("_")[1][:-4]))
seq = fr + fr[::-1][:41]                       # 81 frames, all smoke-free
os.makedirs(out, exist_ok=True)
t0 = 1600000000
H, W = 1536, 2048
yy, xx = np.mgrid[0:H, 0:W]
for k, f in enumerate(seq):
    off = -2400 + 60 * k
    im = np.asarray(Image.open(os.path.join(src, f)).convert("RGB")).astype(np.float32)
    if variant == "cloud" and off >= -600:
        cx = -400 + (off + 600) / 60 * (W / 6.0)
        a = np.zeros((H, W), np.float32)
        for dx, dy, r in [(0, 300, 260), (220, 360, 200), (-200, 380, 220), (420, 330, 180)]:
            a += np.exp(-(((xx - (cx + dx)) / r) ** 2 + ((yy - dy) / (0.5 * r)) ** 2))
        a = np.clip(a, 0, 0.85)[..., None]
        im = im * (1 - a) + 235.0 * a
    Image.fromarray(np.clip(im, 0, 255).astype(np.uint8)).save(os.path.join(out, f"{t0 + 60*k}_{off:+06d}.jpg"), quality=92)
print(len(seq), "frames ->", out)

"""Sequence loading. HPWREN FIgLib: file name = <epoch>_<offset seconds from visible plume>.jpg.
Credit: HPWREN, http://hpwren.ucsd.edu/"""
from __future__ import annotations
import glob, os, re
import numpy as np

W, H = 512, 384
BANNER = 10          # rows ignored at top and bottom (time stamp banner)
CREDIT = "Image data: HPWREN, http://hpwren.ucsd.edu/"
_NAME = re.compile(r"^(\d+)_([+-]\d+)\.jpg$")


def list_frames(seq_dir):
    files = []
    for f in glob.glob(os.path.join(seq_dir, "**", "*.jpg"), recursive=True):
        m = _NAME.match(os.path.basename(f))
        if m:
            files.append((int(m.group(2)), int(m.group(1)), f))
    files.sort()
    return files


def load_sequence(seq_dir, cache_dir=None):
    """Returns dict(frames uint8 (T,H,W,3), offsets (T,) seconds, epochs (T,), name)."""
    from PIL import Image
    name = os.path.basename(os.path.normpath(seq_dir))
    cache = os.path.join(cache_dir, name + ".npz") if cache_dir else None
    if cache and os.path.exists(cache):
        z = np.load(cache)
        return dict(frames=z["frames"], offsets=z["offsets"], epochs=z["epochs"], name=name)
    files = list_frames(seq_dir)
    frames = []
    for off, ep, f in files:
        im = Image.open(f)
        im.draft("RGB", (W, H))          # DCT-domain 1/4 scaling, deterministic
        im = im.convert("RGB")
        if im.size != (W, H):
            im = im.resize((W, H), Image.BOX)
        frames.append(np.asarray(im))
    out = dict(frames=np.stack(frames) if frames else np.zeros((0, H, W, 3), np.uint8),
               offsets=np.array([o for o, _, _ in files], np.int32),
               epochs=np.array([e for _, e, _ in files], np.int64), name=name)
    if cache:
        os.makedirs(cache_dir, exist_ok=True)
        np.savez(cache, frames=out["frames"], offsets=out["offsets"], epochs=out["epochs"])
    return out

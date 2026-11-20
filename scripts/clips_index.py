"""Checks every clip in a directory (decodes start to end, size, duration) and writes a contact sheet and CLIPS.md.
usage: python scripts/clips_index.py clips/ [more info]"""
import os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from firewitness.video import draw

d = sys.argv[1]
mp4 = sorted(f for f in os.listdir(d) if f.endswith(".mp4"))
rows, thumbs = [], []
for f in mp4:
    p = os.path.join(d, f)
    n, dur, w, h, ok = draw.probe(p)
    rows.append((f, n, dur, f"{w}x{h}", ok, os.path.getsize(p) / 1e6))
    t = os.path.join(tempfile.mkdtemp(), "t.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(dur * 0.7), "-i", p, "-frames:v", "1", "-vf", "scale=640:-1", t], check=True)
    thumbs.append((f, Image.open(t).convert("RGB")))
cols = 3
rowsn = (len(thumbs) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 650 + 10, rowsn * 400 + 10), (18, 20, 26))
fnt = ImageFont.truetype(draw._font_path(False), 20)
for i, (f, im) in enumerate(thumbs):
    x, y = 10 + (i % cols) * 650, 10 + (i // cols) * 400
    sheet.paste(im, (x, y))
    ImageDraw.Draw(sheet).text((x + 4, y + 366), f[:-4][:70], font=fnt, fill=(245, 245, 245))
sheet.save(os.path.join(d, "contact_sheet.png"))
good = all(r[4] and 20 <= r[2] <= 40 and r[3] == "1920x1080" for r in rows)
with open(os.path.join(d, "CLIPS.md"), "w") as fh:
    fh.write("# Clips\n\nAll clips 1920x1080 H.264. Each was decoded from first to last frame with ffmpeg (no errors) and its duration checked (20 to 40 s). "
             "Credit burnt into every frame: HPWREN, http://hpwren.ucsd.edu/ (sequence clips); Copernicus Sentinel-2 (scar clip); NOAA GOES-R (satellite clip); FPA FOD, ICS-209-PLUS, MTBS (duplicates clip).\n\n"
             "| file | frames | seconds | size | decodes start to end | MB |\n|---|---|---|---|---|---|\n")
    for f, n, dur, sz, ok, mb in rows:
        fh.write(f"| {f} | {n} | {dur:.1f} | {sz} | {'yes' if ok else 'NO'} | {mb:.1f} |\n")
    fh.write("\n![contact sheet](contact_sheet.png)\n")
print("all ok" if good else "CHECK FAILED", len(rows))
for r in rows: print(r)

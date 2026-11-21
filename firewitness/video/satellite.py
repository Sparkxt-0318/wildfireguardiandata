"""Satellite series layout: frame series, pixel signal and each method's detection time (track `live` export).
Expected directory (results/live_export/<fire_id>/): fire.json, frames_<sat>_<band>.npz (t, bt, cloud),
signal_<sat>.csv (t_utc, bt7, bt14, dT, background_pred, z, cusum, cloud_flag, fdc_mask), detections.csv (method, sat, t_utc, note)."""
from __future__ import annotations
import csv, glob, json, os
from datetime import datetime, timezone
import numpy as np
import cv2
from PIL import Image
from . import draw
from .draw import W, H, OI, FG, MUTED

METHOD_LABEL = {"agency_discovery": "agency discovery", "goes_fdc_first": "GOES fire product", "viirs_first": "VIIRS",
                "modis_first": "MODIS", "polar_first": "polar orbiter", "traceback_onset": "trace-back onset",
                "traceback_distinguishable": "trace-back distinguishable", "live_detector_alert": "live detector",
                "goes_fdc_first_incl_low": "GOES fire product, low prob. included", "traceback_evidence_start": "trace-back evidence starts"}
PALETTE = [OI["vermillion"], OI["sky"], OI["orange"], OI["green"], OI["purple"], OI["yellow"], OI["blue"], OI["grey"]]


def _t(s):
    s = s.strip()
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()


def _read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


class SatClip:
    def __init__(self, d, sat=None, band="7"):
        self.d = d
        self.fire = json.load(open(os.path.join(d, "fire.json")))
        cands = sorted(glob.glob(os.path.join(d, f"frames_*_{band}.npz")) + glob.glob(os.path.join(d, f"frames_*_C{int(band):02d}.npz")))
        if not cands:
            cands = sorted(glob.glob(os.path.join(d, "frames_*.npz")))
        if not cands:
            raise SystemExit("no frames_<sat>_<band>.npz in " + d)
        fp = cands[0] if sat is None else [c for c in cands if f"_{sat}_" in c][0]
        self.sat = os.path.basename(fp).split("_")[1]
        z = np.load(fp)
        self.t = z["t"].astype(float); self.bt = z["bt"].astype(np.float32)
        self.cloud = z["cloud"] if "cloud" in z else np.zeros(self.bt.shape, np.uint8)
        sp = os.path.join(d, f"signal_{self.sat}.csv")
        if not os.path.exists(sp):
            alt = glob.glob(os.path.join(d, "signal_*.csv"))
            sp = alt[0] if alt else sp
        self.sig = _read_csv(sp) if os.path.exists(sp) else []
        self.sig_t = np.array([_t(r["t_utc"]) for r in self.sig], float) if self.sig else self.t
        def col(k): return np.array([float(r[k]) if r.get(k, "") not in ("", None) else np.nan for r in self.sig], float) if self.sig else np.full(len(self.t), np.nan)
        self.dT = col("dT"); self.bt7 = col("bt7"); self.z = col("z"); self.cflag = col("cloud_flag")
        self.det = []
        dp = os.path.join(d, "detections.csv")
        if os.path.exists(dp):
            for r in _read_csv(dp):
                t = _t(r.get("t_utc", ""))
                sv = (r.get("sat") or "").upper()
                if sv in ("", self.sat.upper()) or self.sat.upper() in sv.split("+") or sv in ("ALL",) or not sv.startswith("G"):
                    self.det.append((r["method"], r.get("sat", ""), t, r.get("note", "")))
        self.n = len(self.t)
        ref = [t for m, s, t, n in self.det if m == "agency_discovery" and t]
        if not ref and self.fire.get("discovery_utc"):
            ref = [_t(self.fire["discovery_utc"])]
        self.t0 = ref[0] if ref else self.t[0]
        self.name = self.fire.get("name", self.fire.get("fire_id", "fire"))

    def clock(self, tt):
        return datetime.fromtimestamp(tt, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def rel_min(self, tt):
        return (tt - self.t0) / 60.0

    def frame(self, f, nf):
        p = f / max(nf - 1, 1) * (self.n - 1)
        k = int(round(p))
        cv = draw.canvas()
        draw.banner(cv, f"Satellite series: {self.name}", f"{self.sat.upper()}  |  {self.clock(self.t[k])}")
        # frame panel
        b = self.bt[k]
        lo, hi = np.nanpercentile(self.bt, 1), np.nanpercentile(self.bt, 99.5)
        img = draw.apply_cmap(b, "inferno", lo, hi)
        pw = 640
        img = cv2.resize(img, (pw, pw), interpolation=cv2.INTER_NEAREST)
        cm = cv2.resize((self.cloud[k] >= 2).astype(np.uint8), (pw, pw), interpolation=cv2.INTER_NEAREST).astype(bool)
        img[cm] = (0.55 * img[cm] + 0.45 * np.array(OI["sky"])).astype(np.uint8)
        ny, nx = b.shape
        cy, cx = ny // 2, nx // 2
        s = pw / nx
        cv2.rectangle(img, (int(cx * s), int(cy * s)), (int((cx + 1) * s), int((cy + 1) * s)), (0, 0, 0), 6)
        cv2.rectangle(img, (int(cx * s), int(cy * s)), (int((cx + 1) * s), int((cy + 1) * s)), OI["yellow"], 3)
        draw.put(cv, img, 40, 120)
        draw.text(cv, (48, 126), f"brightness temperature, {self.bt.shape[2]} x {self.bt.shape[1]} pixels", 30, FG, True, stroke=3)
        draw.caption(cv, draw.wrap("Yellow box: the fire pixel. Blue wash: cloud in the satellite cloud mask.", 28, 640), 40, 775, 28, MUTED)
        # signal chart
        x0, x1, y0, y1 = 780, 1860, 150, 560
        draw.text(cv, (x0, 112), "signal at the fire pixel", 34, FG, True)
        cv[y0:y1 + 1, x0:x1 + 1] = (30, 33, 42)
        tt0, tt1 = self.t[0], self.t[-1]
        def X(t): return int(x0 + (t - tt0) / (tt1 - tt0) * (x1 - x0))
        series = self.dT if np.isfinite(self.dT).any() else self.bt7
        ok = np.isfinite(series)
        if ok.any():
            vmin, vmax = np.nanmin(series), np.nanmax(series)
            vmax = max(vmax, vmin + 1e-3)
            pts = np.array([[X(self.sig_t[j]), int(y1 - (series[j] - vmin) / (vmax - vmin) * (y1 - y0 - 20) - 10)] for j in range(len(series)) if ok[j]], np.int32)
            cv2.polylines(cv, [pts], False, OI["orange"], 4, cv2.LINE_AA)
            draw.text(cv, (x1, y0 - 34), "dT: K above the predicted background" if series is self.dT else "BT band 7, K", 26, MUTED, anchor="ra")
        for m, sat, t, note in self.det:
            if t is None or not (tt0 <= t <= tt1):
                continue
            col = PALETTE[list(METHOD_LABEL).index(m) % len(PALETTE)] if m in METHOD_LABEL else OI["grey"]
            cv2.line(cv, (X(t), y0), (X(t), y1), (0, 0, 0), 7); cv2.line(cv, (X(t), y0), (X(t), y1), col, 3)
        cx_ = X(self.t[k])
        cv2.line(cv, (cx_, y0), (cx_, y1), FG, 2, cv2.LINE_AA)
        for hh in np.linspace(0, 1, 5):
            tm = tt0 + hh * (tt1 - tt0)
            draw.text(cv, (X(tm), y1 + 10), datetime.fromtimestamp(tm, timezone.utc).strftime("%H:%M"), 26, MUTED, anchor="ma")
        # detection strip
        draw.text(cv, (780, 606), "when each method sees the fire (minutes from agency discovery)", 32, FG, True)
        rows = sorted([(t, m, s) for m, s, t, n in self.det if t is not None], key=lambda r: r[0])
        for j, (t, m, s) in enumerate(rows[:8]):
            y = 652 + j * 36
            col = PALETTE[list(METHOD_LABEL).index(m) % len(PALETTE)] if m in METHOD_LABEL else OI["grey"]
            cv2.rectangle(cv, (780, y + 4), (812, y + 28), col, -1)
            lab = METHOD_LABEL.get(m, m) + (f" ({s})" if s and s not in ("", "all") else "")
            reached = t <= self.t[k]
            draw.text(cv, (826, y), lab, 27, FG if reached else MUTED, reached)
            draw.text(cv, (1860, y), f"{self.rel_min(t):+.0f} min", 27, FG if reached else MUTED, reached, anchor="ra")
        sub = f"Final size {self.fire['final_acres']:,.0f} acres" + (f", {self.fire['state']}" if self.fire.get("state") else "") + ". " if self.fire.get("final_acres") else ""
        draw.caption(cv, draw.wrap(sub + "Each coloured line is the time a method first flags this fire; the white cursor is the frame shown.", 32, W - 80), 30, 940, 32)
        draw.footer(cv, credit="Satellite data: NOAA GOES-R ABI (public domain); detection times from the live track")
        cv[H - 8:H, :] = (40, 44, 54); cv[H - 8:H, :int(W * f / max(nf - 1, 1))] = OI["sky"]
        return cv


def render_satellite(d, out_mp4, seconds=24, fps=30, gif=True, stills=True, crf=28):
    clip = SatClip(d)
    nf = int(seconds * fps)
    wr = draw.Writer(out_mp4, fps, crf)
    sd = os.path.splitext(out_mp4)[0] + "_stills"
    if stills:
        os.makedirs(sd, exist_ok=True)
    for f in range(nf):
        cv = clip.frame(f, nf)
        wr.write(cv)
        if stills and f in (int(nf * 0.3), int(nf * 0.9)):
            Image.fromarray(cv).save(os.path.join(sd, f"sat_{f:04d}.png"))
    wr.close()
    if gif:
        draw.to_gif(out_mp4, os.path.splitext(out_mp4)[0] + ".gif")
    n, dur, w, h, ok = draw.probe(out_mp4)
    return dict(path=out_mp4, frames=n, seconds=round(dur, 2), size=f"{w}x{h}", decodes_start_to_end=ok)


def make_fixture(d, n=60, seed=0):
    """Small synthetic export in the agreed format (for tests only; not real data)."""
    os.makedirs(d, exist_ok=True)
    rng = np.random.default_rng(seed)
    t0 = 1_700_000_000
    t = t0 + 300 * np.arange(n)
    bt = 295 + rng.normal(0, 0.4, (n, 32, 32)).astype(np.float32)
    on = 25
    for k in range(on, n):
        bt[k, 15:17, 15:17] += 4 + 1.5 * (k - on)
    cloud = np.zeros((n, 32, 32), np.uint8); cloud[:, :10, :12] = 3
    np.savez(os.path.join(d, "frames_g16_7.npz"), t=t, bt=bt, cloud=cloud)
    iso = lambda s: datetime.fromtimestamp(s, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(os.path.join(d, "signal_g16.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["t_utc", "bt7", "bt14", "dT", "background_pred", "z", "cusum", "cloud_flag", "fdc_mask"])
        for k in range(n):
            v = float(bt[k, 15, 15]); w.writerow([iso(t[k]), v, 280.0, v - 295, 295, (v - 295) / 0.4, 0, 0, 0])
    with open(os.path.join(d, "detections.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["method", "sat", "t_utc", "note"])
        w.writerow(["agency_discovery", "", iso(t[on + 8]), ""]); w.writerow(["traceback_onset", "g16", iso(t[on - 1]), "synthetic"])
        w.writerow(["goes_fdc_first", "g16", iso(t[on + 4]), "synthetic"]); w.writerow(["live_detector_alert", "g16", iso(t[on + 1]), "synthetic"])
    json.dump(dict(fire_id="fixture", name="Synthetic fixture (not a real fire)", final_acres=1234, satellites=["g16"]), open(os.path.join(d, "fire.json"), "w"))

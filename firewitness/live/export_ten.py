"""Ten-fire export for track 52 (protocol deliverable): frames, pixel signal and every method's detection times."""
from __future__ import annotations

import csv
import json
import tarfile
from pathlib import Path

from . import export
from .extract import load_fires
from .traceback import series_meta

TEN = {
    "2023-ORWIF-230266": "both satellites; detector 5 min before the operational product; onsets disagree by 40 min",
    "2025-CALAC-009087": "Eaton fire (Los Angeles, Jan 2025): saturated first hot pixel flagged as cloud by ACM; detector late",
    "2024-AZTNF-001687": "two witnesses agree on the onset; detector 80 min before the operational product (sealed test)",
    "2023-MTFHA-000098": "two witnesses agree; detector 5 min after the operational product",
    "2024-IDPAF-005673": "one witness; detector 50 min before the operational product",
    "2023-TXTXS-232562": "GOES-East only; detector 20 min before the operational product (sealed test)",
    "2024-ORVAD-240159": "missed: thunderstorm cloud over the site (BT14 far colder than clear sky)",
    "2024-NMMEA-000382": "South Fork (NM, 2024): onset traced 12 h before the operational product, detector never alerts (sealed test)",
    "2025-MOMTF-000242": "GOES-East only, Missouri; detector 45 min before the operational product",
    "2024-CARRU-110705": "one witness; detector 30 min after the operational product (sealed test)",
}


def run(out_root=Path("results/live_export"), tar_path=Path("release/live-v0.1/live_export_v0.1.tar.gz")):
    fires = {f["fire_id"]: f for f in load_fires("protocol/live_fires.csv")}
    tbs = {(r["fire_id"], r["sat"]): r for r in csv.DictReader(open("results/live/traceback_all_A2_by_satellite.csv"))}
    rep = {}
    for s in ("dev", "test"):
        for r in csv.DictReader(open(f"results/live/replay_{s}_by_fire.csv")):
            rep[r["fire_id"]] = r
    det_doc = json.loads(Path("firewitness/live/config/detector_us.json").read_text())
    I = export._iso
    dirs = []
    for fid, why in TEN.items():
        f = fires[fid]
        m = series_meta(fid)
        det = [{"method": "agency_discovery", "sat": "", "t_utc": I(m["discovery_t"]), "note": "WFIGS FireDiscoveryDateTime"},
               {"method": "polar_first", "sat": f["polar_first_sensor"], "t_utc": I(m["polar_first_t"]),
                "note": "FIRMS archive (VIIRS S-NPP n/h, MODIS >= 30), acquisition time"}]
        for sat, v in m["sats"].items():
            det.append({"method": "goes_fdc_first", "sat": sat, "t_utc": I(v["fdc_first"][0]) if v["fdc_first"] else "",
                        "note": "FDCC codes 10-14/30-34 in the 5x5 window, scan start; available " +
                                (I(v["fdc_first"][1]) if v["fdc_first"] else "never")})
            det.append({"method": "goes_fdc_first_incl_low", "sat": sat,
                        "t_utc": I(v["fdc_first_low"][0]) if v["fdc_first_low"] else "", "note": "FDCC incl. low probability 15/35"})
            t = tbs.get((fid, sat))
            if t:
                det.append({"method": "traceback_distinguishable", "sat": sat, "t_utc": t["t_D"] or "",
                            "note": f"Part A (variant A2): 95% interval {t['t_D_lo'] or '-'} to {t['t_D_hi'] or '-'}; "
                                    f"S at anchor {t['S_pre']} vs h_A {t['h_A']}"})
                det.append({"method": "traceback_evidence_start", "sat": sat, "t_utc": t["tau"] or "",
                            "note": "earliest plausible start (CUSUM run start)"})
        r = rep.get(fid, {})
        det.append({"method": "live_detector_alert", "sat": "+".join(m["sats"]), "t_utc": r.get("alert_utc") or "",
                    "note": f"frozen detector replay, strictly causal (availability times), h={det_doc['h']:.1f} at 1e-4 "
                            f"false alerts per pixel-site-day; lead vs operational {r.get('lead_min')} min"})
        d = export.export_fire({**f}, out_root, det)
        info = json.loads((d / "fire.json").read_text())
        info["why_chosen"] = why
        info["split"] = f["split"]
        (d / "fire.json").write_text(json.dumps(info, indent=1))
        dirs.append(d)
    tar_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "w:gz") as tf:
        for d in dirs:
            tf.add(d, arcname=f"live_export/{d.name}")
    return dirs, tar_path

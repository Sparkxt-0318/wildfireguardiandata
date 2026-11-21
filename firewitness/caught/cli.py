"""firewitness caught run | export | floor | truth"""
from __future__ import annotations

import json

HELP = "labels for recorded fires that standard satellite products missed (scar finder, more looks, floors)"


def register(parser):
    sub = parser.add_subparsers(dest="cmd")
    r = sub.add_parser("run", help="run a slice (S1 California 2020, S2 US 2020, S3 US 2018-2020): records + placebos")
    r.add_argument("slice", choices=["S1", "S2", "S3"])
    r.add_argument("--tag", default="final")
    r.add_argument("--threads", type=int, default=40)
    r.add_argument("--dev", action="store_true", help="dev split only")
    r.add_argument("--limit", type=int, default=None)
    r.add_argument("--params", default=None, help="JSON overriding scar parameters")
    r.add_argument("--out", default="results/caught", help="where the slice tables go (full runs only)")
    r.set_defaults(func=_run)
    t = sub.add_parser("truth", help="run the C2 truth fires (dev or sealed)")
    t.add_argument("split", choices=["dev", "sealed"])
    t.add_argument("--tag", default="final")
    t.add_argument("--threads", type=int, default=40)
    t.set_defaults(func=_truth)
    e = sub.add_parser("export", help="write the label set (GeoParquet + GeoJSON lines), data card and checksums")
    e.add_argument("--tag", default="final")
    e.add_argument("--slices", default="S3")
    e.add_argument("--out", default="release/caught_v0.1")
    e.set_defaults(func=_export)
    f = sub.add_parser("floor", help="detection floors: the published table, or one place and time")
    f.add_argument("--sensor", default=None, help="MODIS|VIIRS|AVHRR|GOES|S2|LANDSAT")
    f.add_argument("--view", type=float, default=None, help="view/scan angle in degrees (default: edge of scan)")
    f.add_argument("--night", action="store_true")
    f.add_argument("--t4", type=float, default=None, help="background 4 um brightness temperature (K)")
    f.add_argument("--sigma", type=float, default=2.0, help="background noise (K)")
    f.add_argument("--threshold", type=float, default=0.10, help="dNBR threshold for a scar look")
    f.set_defaults(func=_floor)


def _run(a) -> int:
    import time
    from pathlib import Path
    from firewitness.core.hashing import hash_inputs
    from . import report
    from .fetch import RAW_ROOT
    from .pipeline import run_slice, summarize
    t = time.time()
    p = json.loads(a.params) if a.params else None
    rec, plc, lr, lp = run_slice(a.slice, threads=a.threads, params=p, tag=a.tag, only_dev=a.dev, limit=a.limit)
    s = summarize(lr, lp, None)
    if a.out and not a.dev and not a.limit:
        out = Path(a.out)
        report.write_slice(out, a.slice, lr, lp)
        s["wall_s"] = time.time() - t
        s["inputs"] = hash_inputs(sorted((RAW_ROOT / "firms").glob("*.csv")) +
                                  [RAW_ROOT / "fpafod/RDS-2013-0009.7_Data_Format4_SQLITE.zip",
                                   RAW_ROOT / "mtbs/mtbs_perimeter_data.zip"])
        (out / f"{a.slice}_summary.json").write_text(json.dumps(s, indent=1, default=str))
    print(json.dumps({k: v for k, v in s.items() if k != "inputs"}, indent=1, default=str))
    return 0


def _truth(a) -> int:
    from .pipeline import run_truth, summarize
    lt = run_truth(a.split, tag=a.tag, threads=a.threads)
    print(json.dumps(summarize(None, None, lt), indent=1, default=str))
    return 0


def _export(a) -> int:
    from .export import export
    export(a.tag, a.slices.split(","), a.out)
    return 0


def _floor(a) -> int:
    from .floor import Background, floor_table, heat_floor_m2, reflective_floor_m2, scar_floor_m2
    if a.sensor is None:
        for row in floor_table(None):
            print(json.dumps(row))
        return 0
    s = a.sensor.upper()
    if s in ("S2", "LANDSAT"):
        px = 20.0 if s == "S2" else 30.0
        print(json.dumps({"sensor": s, "scar_floor_m2": scar_floor_m2(a.threshold, px),
                          "hotspot_floor_m2": reflective_floor_m2(s)}))
        return 0
    day = not a.night
    bg = Background(a.t4 or (305.0 if day else 285.0), (a.t4 or (305.0 if day else 285.0)) - (5.0 if day else 0.0),
                    a.sigma, day)
    print(json.dumps({"sensor": s, "view_deg": a.view if a.view is not None else "edge", "day": day,
                      "floor_m2": heat_floor_m2(s, a.view, bg)}))
    return 0

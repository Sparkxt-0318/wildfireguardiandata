"""firewitness fuel ... : check a fuel map cell by cell without fieldwork."""
from __future__ import annotations
import json
from pathlib import Path

HELP = "check a LANDFIRE fuel map cell by cell against independent layers (rules only)"


def _resolve(target: str, map_key: str):
    """-> (area name, Grid or None). Tile ids, 'lon0,lat0,lon1,lat1' boxes, or a fire name from the 29-fire catalog."""
    from .areas import tile_grid
    from .grid import Grid, lonlat_to_5070
    if target.startswith("T") and len(target) == 8 and target[4] == "_":
        return target, tile_grid(target)
    if "," in target and target.replace(",", "").replace(".", "").replace("-", "").isdigit():
        w, s, e, n = (float(v) for v in target.split(","))
        x0, y0 = lonlat_to_5070(w, s)
        x1, y1 = lonlat_to_5070(e, n)
        g = Grid.from_bounds(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        return "BOX_" + target.replace(",", "_").replace(".", "p").replace("-", "m"), g
    cat = Path(__file__).parent / "fires29" / "catalog.json"
    if cat.exists():
        for f in json.loads(cat.read_text()):
            if target.lower() in (str(f.get("id", "")).lower(), str(f.get("name", "")).lower()):
                from .fetch.rawindex import RAW_ROOT
                meta = json.loads((RAW_ROOT / "fires29" / f["id"] / "meta.json").read_text())
                return "F_" + f["id"], Grid.from_dict(meta["grid"])
    raise SystemExit(f"cannot resolve '{target}': give a tile id (T012_030), a lon/lat box, or a fire name from fires29/catalog.json")


def run_check(args) -> int:
    from . import report, runner
    from .areas import area_dir
    from .fetch.area import fetch_area
    from .layers import load
    from . import agent
    cfg = runner.region_cfg(args.region)
    name, grid = _resolve(args.target, args.map)
    d = area_dir(name)
    if not (d / "DONE").exists():
        year = cfg["maps"][args.map]["landfire_release"]
        fetch_area(name, grid, maps=(year,))
    man = runner.run_area(name, args.map, cfg, out_root=Path(args.out) if args.out else None)
    out = Path(args.out) if args.out else runner.OUT_ROOT
    out = out / args.map / name
    L = load(d, args.map, cfg)
    import numpy as np
    from .grid import read_tif
    verdict, _ = read_tif(out / "verdict.tif")
    res = agent.check(L, cfg)
    report.map_png(res, out / "map.png", f"{name} {args.map}")
    rows, cols = np.nonzero(res.verdict == agent.CONTRADICTED)
    pick = np.linspace(0, len(rows) - 1, min(5, len(rows))).astype(int) if len(rows) else []
    examples = [report.card_text(report.card(L, res, int(rows[i]), int(cols[i]), cfg)) for i in pick]
    (out / "report.md").write_text(report.report_md(name, args.map, man, examples))
    print(json.dumps({"area": name, "map": args.map, "counts": man["counts"], "out": str(out)}))
    return 0


def run_card(args) -> int:
    from . import report, runner
    from .areas import area_dir
    from .layers import load
    from . import agent
    cfg = runner.region_cfg(args.region)
    name, _ = _resolve(args.target, args.map)
    L = load(area_dir(name), args.map, cfg)
    res = agent.check(L, cfg)
    r, c = (int(v) for v in args.cell.split(","))
    print(report.card_text(report.card(L, res, r, c, cfg)))
    return 0


def run_grade(args) -> int:
    from . import grade
    from .areas import DEV
    df = grade.grade_tiles(DEV, args.map)
    print(json.dumps(grade.summarize(df, "dev"), indent=1, default=str))
    return 0


def register(parser):
    sub = parser.add_subparsers(dest="cmd")
    sp = sub.add_parser("check", help="check a fuel map for an area (tile id, lon/lat box or fire name)")
    sp.add_argument("target")
    sp.add_argument("--map", default="M22", choices=["M22", "M16"])
    sp.add_argument("--region", default="us")
    sp.add_argument("--out", default=None, help="output folder (default: next to the raw folder, fuel_out/)")
    sp.set_defaults(func=run_check)
    sp = sub.add_parser("card", help="print the evidence card of one cell: --cell row,col")
    sp.add_argument("target")
    sp.add_argument("--cell", required=True)
    sp.add_argument("--map", default="M22", choices=["M22", "M16"])
    sp.add_argument("--region", default="us")
    sp.set_defaults(func=run_card)
    sp = sub.add_parser("grade-dev", help="grade the dev areas against held-out plots (development only)")
    sp.add_argument("--map", default="M22", choices=["M22", "M16"])
    sp.set_defaults(func=run_grade)

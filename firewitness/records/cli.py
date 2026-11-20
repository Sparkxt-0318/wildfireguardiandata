"""firewitness records ... (track 49). Commands: clean, link, ids, revert, report."""
from __future__ import annotations

import json
from pathlib import Path

HELP = "records: clean, link, ids, revert, report (fire-record cleaning)"


def _read_csv(path, encoding="latin-1"):
    import pandas as pd
    return pd.read_csv(path, dtype=str, encoding=encoding, keep_default_na=False, na_values=[], low_memory=False)


def cmd_clean(a):
    import pandas as pd
    from ..core import PatchSet, load_region, sha256_file
    from . import frame_ops, paths, values
    if a.national:
        from . import pipeline
        r = pipeline.run_national(Path(a.out), [int(y) for y in a.years.split(",")] if a.years else None, a.region)
        print(json.dumps({k: v for k, v in r.items() if k not in ("inputs", "links")}, indent=1, default=str))
        return 0
    cfg = load_region(paths.REPO / "firewitness" / "records", a.region)
    df = _read_csv(a.input)
    if a.id_col not in df.columns:
        df.insert(0, a.id_col, [f"row:{i}" for i in range(len(df))])
        print(f"no id column '{a.id_col}': row numbers used as record ids")
    patches, flags = values.clean_values(df, a.table, cfg, a.id_col)
    ps = PatchSet(patches, frame_ops.sha256_frame(df), "records.clean", {"table": a.table, "region": a.region, "input_file_sha256": sha256_file(a.input), "serialisation": "csv, latin-1 bytes, LF, minimal quoting"})
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ps.write(out / "patches.jsonl")
    clean = frame_ops.apply_frame(df, patches, a.id_col)
    frame_ops.write_csv(clean, out / "clean.csv", "utf-8")
    flags.to_csv(out / "flags.csv", index=False)
    (out / "input_columns.json").write_text(json.dumps(list(df.columns)))
    print(f"{len(patches)} patches, {len(flags)} flags -> {out}")
    return 0


def cmd_revert(a):
    from ..core import PatchSet
    from . import frame_ops
    ps = PatchSet.read(a.patches)
    clean = _read_csv(a.clean, "utf-8")
    cols = json.loads(Path(a.columns).read_text()) if a.columns else [c for c in clean.columns]
    back = frame_ops.revert_frame(clean, ps.patches, a.id_col, cols)
    h = frame_ops.write_csv(back, a.out)
    print("reverted; sha256", h)
    if ps.input_sha256:
        print("equals the input recorded in the patch file (canonical serialisation):", h == ps.input_sha256)
        print("equals the input file byte for byte:", h == ps.meta.get("input_file_sha256"))
    return 0


def cmd_link(a):
    from . import link_tasks as LT
    import numpy as np
    for name in (a.task or list(LT.TASKS)):
        r, m, _ = LT.run_task(name, split=a.split, verbose=False)
        print(json.dumps({k: v for k, v in r.items()}, indent=1, default=float))
    if a.export_examples:
        from . import examples
        examples.export(a.export_examples, Path(a.out_examples))
    return 0


def cmd_ids(a):
    from . import pipeline
    r = pipeline.run_national(Path(a.out), [int(y) for y in a.years.split(",")] if a.years else None, a.region, skip_values=True)
    print(json.dumps(r["ids"], indent=1))
    return 0


def cmd_report(a):
    from . import report
    report.write(Path(a.out))
    return 0


def register(parser):
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("clean", help="values, location/time, duplicates -> patches + clean table (any CSV, or --national for the US run)")
    p.add_argument("--input"); p.add_argument("--table", default="generic", choices=["generic", "fpafod", "ics_sitreps", "ics_incidents"])
    p.add_argument("--id-col", default="rid"); p.add_argument("--region", default="us"); p.add_argument("--out", default="records_out")
    p.add_argument("--national", action="store_true"); p.add_argument("--years", default=None)
    p.set_defaults(func=cmd_clean)
    p = sub.add_parser("link", help="link fire records across sources (fod_mtbs, fod_ics, ics_fired)")
    p.add_argument("--task", action="append", choices=["fod_mtbs", "fod_ics", "ics_fired"]); p.add_argument("--split", default="dev", choices=["dev", "test"])
    p.add_argument("--export-examples", type=int, default=0); p.add_argument("--out-examples", default="results/collapse_examples")
    p.set_defaults(func=cmd_link)
    p = sub.add_parser("ids", help="permanent fire IDs and crosswalk"); p.add_argument("--region", default="us"); p.add_argument("--years", default=None); p.add_argument("--out", default="records_out")
    p.set_defaults(func=cmd_ids)
    p = sub.add_parser("revert", help="revert a cleaned CSV with its patch file (byte for byte)")
    p.add_argument("--patches", required=True); p.add_argument("--clean", required=True); p.add_argument("--out", required=True)
    p.add_argument("--id-col", default="rid"); p.add_argument("--columns", default=None, help="input_columns.json written by clean")
    p.set_defaults(func=cmd_revert)
    p = sub.add_parser("report", help="coverage flags per state, year, agency and the summary report"); p.add_argument("--out", default="records_out")
    p.set_defaults(func=cmd_report)

"""firewitness live: trace-back, replay and the live service (track 51)."""
from __future__ import annotations

import json
import time
from pathlib import Path

HELP = "early onset of known fires (traceback), detector replay, live service (run)"


def register(parser):
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("traceback", help="Part A: trace back fires to the first distinguishable frame")
    p.add_argument("--fires", default="protocol/live_fires.csv")
    p.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    p.add_argument("--extract", action="store_true", help="read GOES series first (network, ~3 min per fire)")
    p.add_argument("--variant", default="A0", choices=["A0", "A1", "A2"], help="protocol amendment 4")
    p.add_argument("--out", default="results/live")
    p.set_defaults(func=cmd_traceback)
    p = sub.add_parser("replay", help="Part B: causal replay of the detector on dev or sealed-test fires")
    p.add_argument("--split", default="dev", choices=["dev", "test"])
    p.add_argument("--detector", default=None, help="detector JSON (default config/detector_us.json)")
    p.add_argument("--out", default="results/live")
    p.add_argument("--i-am-opening-the-sealed-test", action="store_true", dest="open_test")
    p.set_defaults(func=cmd_replay)
    p = sub.add_parser("fit", help="Part B: fit the detector on dev fires (cross-validated forward selection)")
    p.add_argument("--labels", default="results/live/traceback_dev_A0_by_satellite.csv")
    p.add_argument("--out", default="results/live")
    p.add_argument("--freeze", action="store_true", help="write config/detector_us.json (frozen)")
    p.set_defaults(func=cmd_fit)
    p = sub.add_parser("run", help="Part C: run the live detector on the current GOES stream")
    p.add_argument("--log-repo", default="live-log-wt", help="checkout of branch live-log")
    p.add_argument("--hours", type=float, default=0.25)
    p.add_argument("--cache", default="live-cache")
    p.add_argument("--publish", action="store_true", help="sign and push records to live-log")
    p.add_argument("--no-sign", action="store_true")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("reconcile", help="Part C: match past candidates with agency and satellite records")
    p.add_argument("--log-repo", default="live-log-wt")
    p.add_argument("--min-age-h", type=float, default=24)
    p.set_defaults(func=cmd_reconcile)


def cmd_traceback(a):
    from .pipeline import traceback_main
    return traceback_main(a)


def cmd_replay(a):
    from .pipeline import replay_main
    return replay_main(a)


def cmd_fit(a):
    from .fit import fit_dev
    r = fit_dev(Path(a.out), Path(a.labels), freeze=a.freeze)
    print(json.dumps({k: r[k] for k in ("final_config", "final_h", "cv_held_out_score", "cv_held_out_stats")}, default=str))
    return 0


def cmd_run(a):
    from .service import run
    n = run(Path(a.log_repo), time.time() + a.hours * 3600, a.publish, Path(a.cache), sign_records=not a.no_sign)
    print(json.dumps({"cycles": n}))
    return 0


def cmd_reconcile(a):
    from .reconcile import reconcile
    print(json.dumps(reconcile(Path(a.log_repo), a.min_age_h)))
    return 0

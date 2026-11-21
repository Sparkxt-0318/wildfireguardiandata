"""firewitness score ... : negatives sample, splits make, card (score), build, contract-template, gates."""
from __future__ import annotations

import json
import os
import sys

HELP = "score: negatives sample, splits make, card (score a prediction file), build, contract-template, gates"


def _ds(path):
    from .dataset import Dataset
    return Dataset.load(path)


def run_build(a):
    if a.adapter == "synthetic":
        from .adapters import synthetic
        ds = synthetic.build(a.n_fires, a.size, a.seed)
    elif a.adapter == "caught":
        from .adapters import caught
        ds = caught.read_parquet(a.input)
    elif a.adapter == "live":
        from .adapters import live
        ds = live.read_csv(a.input)
    else:
        from .adapters import wildfirespreadts
        ds = wildfirespreadts.build_dataset(a.raw, workers=a.workers)
    ds.save(a.out)
    print(json.dumps(ds.summary()))
    return 0


def run_neg(a):
    from . import negatives, splits
    ds = _ds(a.dataset)
    sp = splits.load(a.split)
    ids = sp["folds"][a.fold]
    r = negatives.sample(ds, ids, k=a.k, seed=a.seed, buffer_cells=a.buffer_cells, hard_share=a.hard_share, matched=not a.random)
    negatives.save(r, a.out)
    print(json.dumps(r["stats"], indent=1, sort_keys=True))
    return 0


def run_splits(a):
    from . import splits
    ds = _ds(a.dataset)
    sp = splits.make(ds, a.scheme, seed=a.seed, test_frac=a.test_frac, val_frac=a.val_frac, block_km=a.block_km,
                     buffer_km=a.buffer_km, buffer_days=a.buffer_days)
    splits.write(sp, a.out)
    print(json.dumps({"scheme": a.scheme, "folds": {k: len(v) for k, v in sp["folds"].items()}, "dropped": len(sp["dropped"]), "sha256": sp["sha256"]}))
    return 0


def run_contract(a):
    from . import contract
    contract.write_template(a.out)
    print(f"wrote {a.out}")
    return 0


def run_card(a):
    from . import card, contract, splits
    from .predictions import Predictions
    ds = _ds(a.dataset)
    sp = splits.load(a.split)
    c = contract.load(a.contract)
    p = Predictions.load(a.predictions) if a.predictions.endswith(".npz") else Predictions.from_csv(a.predictions, ds, {"info_until_lag_days": a.info_lag} if a.info_lag else {})
    cd = card.build_card(ds, sp, p, c, a.model_name, fold=a.fold)
    os.makedirs(a.out_dir, exist_ok=True)
    open(os.path.join(a.out_dir, f"card_{a.model_name}.json"), "w").write(card.to_json(cd))
    txt = card.render(cd)
    open(os.path.join(a.out_dir, f"card_{a.model_name}.md"), "w").write(txt)
    print(txt)
    return 0


def run_gates(a):
    from . import gates
    return gates.main(a)


def add_sample_args(s):
    s.add_argument("--dataset", required=True)
    s.add_argument("--split", required=True)
    s.add_argument("--fold", default="train")
    s.add_argument("--k", type=int, default=3)
    s.add_argument("--seed", type=int, default=54)
    s.add_argument("--buffer-cells", type=int, default=1)
    s.add_argument("--hard-share", type=float, default=0.25)
    s.add_argument("--random", action="store_true", help="naive random negatives (for comparison only)")
    s.add_argument("--out", required=True)
    s.set_defaults(func=run_neg)


def add_make_args(m):
    m.add_argument("--dataset", required=True)
    m.add_argument("--scheme", default="space_time", choices=["space_time", "space", "time", "random_fire", "random_rows"])
    m.add_argument("--seed", type=int, default=54)
    m.add_argument("--test-frac", type=float, default=0.2)
    m.add_argument("--val-frac", type=float, default=0.15)
    m.add_argument("--block-km", type=float, default=100.0)
    m.add_argument("--buffer-km", type=float, default=50.0)
    m.add_argument("--buffer-days", type=int, default=30)
    m.add_argument("--out", required=True)
    m.set_defaults(func=run_splits)


def add_card_args(cd, required=True):
    cd.add_argument("--dataset", required=required)
    cd.add_argument("--split", required=required)
    cd.add_argument("--contract", required=required)
    cd.add_argument("--predictions", required=required, help=".npz (dense) or .csv (fire_id,date,y,x,score[,info_until])")
    cd.add_argument("--model-name", default="model")
    cd.add_argument("--fold", default="test")
    cd.add_argument("--info-lag", type=int, default=0, help="csv only: declare inputs end this many days before the valid day")
    cd.add_argument("--out-dir", default="results/cards")
    cd.set_defaults(func=run_card)


def run_default(a):
    """`firewitness score` with card arguments scores a prediction file (the brief's `firewitness score`)."""
    if not (a.dataset and a.split and a.contract and a.predictions):
        print("usage: firewitness score --dataset D --split S.json --contract C.json --predictions P [--model-name N]\n"
              "       or a subcommand: build, negatives sample, splits make, card, contract-template, gates")
        return 2
    return run_card(a)


def register(parser):
    add_card_args(parser, required=False)
    parser.set_defaults(func=run_default)
    sub = parser.add_subparsers(dest="cmd")
    sp = sub.add_parser("build", help="build a scene dataset from a benchmark's own masks")
    sp.add_argument("--adapter", choices=["wildfirespreadts", "synthetic", "caught", "live"], default="wildfirespreadts")
    sp.add_argument("--input", help="caught: states parquet; live: live_fires.csv (or onset table)")
    sp.add_argument("--raw", default="/home/user/wildfire 3 (1)/firewitness_raw/wildfirespreadts")
    sp.add_argument("--out", required=True)
    sp.add_argument("--workers", type=int, default=3)
    sp.add_argument("--n-fires", type=int, default=60)
    sp.add_argument("--size", type=int, default=48)
    sp.add_argument("--seed", type=int, default=0)
    sp.set_defaults(func=run_build)

    ng = sub.add_parser("negatives", help="matched negative sampling")
    ngs = ng.add_subparsers(dest="ncmd")
    add_sample_args(ngs.add_parser("sample", help="sample negatives matched to positives from verified no-fire cells"))

    sg = sub.add_parser("splits", help="blocked splits")
    sgs = sg.add_subparsers(dest="scmd")
    add_make_args(sgs.add_parser("make", help="make a published split file (blocked in space/time, by fire, with a buffer)"))

    ct = sub.add_parser("contract-template", help="write a contract template")
    ct.add_argument("--out", required=True)
    ct.set_defaults(func=run_contract)

    add_card_args(sub.add_parser("card", help="score a prediction file against a split and a contract"))

    g = sub.add_parser("gates", help="run gates N1-N5 and write results")
    g.add_argument("--dataset", required=True)
    g.add_argument("--out", default="results/SCORE_GATES.json")
    g.add_argument("--name", default="benchmark")
    g.add_argument("--scheme", default="space", choices=["space_time", "space", "time", "random_fire"])
    g.set_defaults(func=run_gates)

"""firewitness smoke ... Credit: image data HPWREN, http://hpwren.ucsd.edu/"""
import json, os, sys

HELP = "smoke edge, first frame and class rules (opacity map, contours, vector, classes)"


def _label(args):
    import numpy as np
    from . import pipeline, seq
    from .params import get as get_params, cfg_hash
    from ..core import hashing
    p = get_params()
    sq = seq.load_sequence(args.sequence, args.cache)
    files = [f for _, _, f in seq.list_frames(args.sequence)]
    r = pipeline.label_sequence(sq, p)
    out = args.out
    os.makedirs(out, exist_ok=True)
    meta = dict(name=sq["name"], credit=seq.CREDIT, params_hash=cfg_hash(p), params=p,
                inputs=hashing.hash_inputs(files), working_size=[seq.W, seq.H])
    if r["excluded"]:
        meta["excluded"] = r["excluded"]
        with open(os.path.join(out, "labels.json"), "w") as f:
            json.dump(meta, f, indent=1, sort_keys=True)
        print("excluded:", r["excluded"])
        return 0
    pr = r["prep"]; T = len(pr["alpha"])
    levels = [("noise", None)] + [(f"{l:.2f}", l) for l in p["levels"]]
    edges = {str(int(pr["offsets"][t])): {nm: pipeline.contours_at(pr["alpha"][t], pr["T"], lv) for nm, lv in levels}
             for t in range(T)}
    post0 = int(pr["pre_idx"][-1]) + 1
    cls = np.zeros((T, seq.H, seq.W), np.uint8)
    for t in range(post0, T):
        cls[t] = pipeline.class_map(r["nodes"], t)
    np.savez_compressed(os.path.join(out, "opacity.npz"), alpha=np.round(np.clip(pr["alpha"], 0, 1) * 255).astype(np.uint8),
                        noise_threshold=np.round(np.clip(pr["T"], 0, 1) * 255).astype(np.uint8), offsets=pr["offsets"],
                        classes=cls, class_names=np.array(pipeline.CLASSES))
    with open(os.path.join(out, "edges.json"), "w") as f:
        json.dump(edges, f, sort_keys=True, separators=(",", ":"))
    chains = [dict(cls=c["cls"], rule=c["rule"], first_offset=int(pr["offsets"][c["t_first"]]), last_offset=int(pr["offsets"][c["ts"][-1]]),
                   seed_xy=[round(v, 1) for v in c["seed_xy"]], seed_area=c["seed_area"], area_at_confirmation=c["area_conf"],
                   on_ground=c["on_ground"], grown=c["grown"], texture_loss=c["texture_loss"], mass=round(c["mass"], 2))
              for c in sorted(r["chains"], key=lambda c: (c["t_first"], c["root"]))]
    meta.update(excluded=None, L0=round(float(pr["L0"]), 5), endmember=[round(float(x), 4) for x in pr["S"]], endmember_fitted=pr["S_fitted"],
                masked_share=round(pr["info"].get("masked_share", 0), 4), first_smoke_offset_s=r["first_offset"],
                first_smoke_frame=None if r["first_frame"] is None else int(r["first_frame"]),
                human_offset_s=0, chains=chains, placebo_smoke_frames=[int(t) for t in r["placebo_frames"]],
                levels=["noise"] + [f"{l:.2f}" for l in p["levels"]], offsets=[int(o) for o in pr["offsets"]])
    with open(os.path.join(out, "labels.json"), "w") as f:
        json.dump(meta, f, indent=1, sort_keys=True)
    print("first smoke offset (s):", r["first_offset"], "| wrote", out)
    return 0


def _eval(args):
    from . import evaluate as E
    from .params import get as get_params
    names = [n.strip() for n in open(args.list) if n.strip()]
    p = get_params()
    res = {}
    if "s23" in args.tests:
        r = E.run_s23(names, p, raw=args.raw); res["s2_s3"] = E.summarise_s23(r); res["s2_s3_rows"] = r
    if "s1" in args.tests:
        rows = E.run_s1(E.S1.full_cases(names) if args.full else E.S1.lite_cases(names), p, raw=args.raw)
        res["s1"] = E.summarise_s1(rows); res["s1_rows"] = rows
    with open(args.out, "w") as f:
        json.dump(res, f, indent=1, default=str)
    print("wrote", args.out)
    return 0


def register(parser):
    sub = parser.add_subparsers(dest="cmd")
    sp = sub.add_parser("label", help="label one FIgLib sequence directory: opacity map, edges, vector classes, first smoke")
    sp.add_argument("sequence", help="directory of <epoch>_<offset>.jpg frames")
    sp.add_argument("--out", required=True)
    sp.add_argument("--cache", default=None, help="optional directory for decoded frames")
    sp.set_defaults(func=_label)
    ev = sub.add_parser("eval", help="run tests S1, S2/S3 over a list of sequence names")
    ev.add_argument("list", help="text file, one sequence name per line")
    ev.add_argument("--raw", default="/home/user/wildfire 3 (1)/firewitness_raw/figlib/")
    ev.add_argument("--tests", nargs="+", default=["s23", "s1"])
    ev.add_argument("--full", action="store_true", help="full S1 grid (default: lite)")
    ev.add_argument("--out", required=True)
    ev.set_defaults(func=_eval)

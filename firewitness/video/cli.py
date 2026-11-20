"""firewitness video ... Credit: image data HPWREN, http://hpwren.ucsd.edu/"""
import json
HELP = "render clips (MP4 1080p, GIF, stills) from labelled sequences and other tracks' exports"


def _render(args):
    from . import render
    info = render.render_clip(args.sequence, args.labels, args.out, args.layout, args.seconds, args.fps, not args.no_gif, not args.no_stills)
    print(json.dumps(info))
    return 0


def _sat(args):
    from . import satellite
    print(json.dumps(satellite.render_satellite(args.dir, args.out, args.seconds, args.fps, not args.no_gif, not args.no_stills)))
    return 0


def _truth(args):
    from . import truth
    print(json.dumps(truth.render_truth(args.sequence, args.out, args.alpha_max, args.endmember, 0, args.seconds)))
    return 0


def register(parser):
    sub = parser.add_subparsers(dest="cmd")
    sp = sub.add_parser("render", help="render a labelled FIgLib sequence")
    sp.add_argument("sequence", help="directory of frames")
    sp.add_argument("labels", help="output directory of `firewitness smoke label`")
    sp.add_argument("--out", required=True, help="output .mp4")
    sp.add_argument("--layout", default="all", choices=["a", "b", "c", "d", "all"])
    sp.add_argument("--seconds", type=float, default=None, help="length of a single-layout clip (20-40 s)")
    sp.add_argument("--fps", type=int, default=30)
    sp.add_argument("--no-gif", action="store_true"); sp.add_argument("--no-stills", action="store_true")
    sp.set_defaults(func=_render)
    st = sub.add_parser("satellite", help="render a satellite series export (track live): frames, pixel signal, detection times")
    st.add_argument("dir", help="results/live_export/<fire_id>/")
    st.add_argument("--out", required=True)
    st.add_argument("--seconds", type=float, default=24); st.add_argument("--fps", type=int, default=30)
    st.add_argument("--no-gif", action="store_true"); st.add_argument("--no-stills", action="store_true")
    st.set_defaults(func=_sat)
    tr = sub.add_parser("truth", help="known-truth demo (test S1): planted plume, truth contours, measured contours")
    tr.add_argument("sequence", help="directory of frames (smoke-free pre-ignition frames are used)")
    tr.add_argument("--out", required=True); tr.add_argument("--alpha-max", type=float, default=0.6)
    tr.add_argument("--endmember", default="grey055", choices=["grey030", "grey055", "grey085", "warm"])
    tr.add_argument("--seconds", type=float, default=24)
    tr.set_defaults(func=_truth)

HELP = "negatives: sample (alias of `firewitness score negatives sample`)"


def register(parser):
    from firewitness.score.cli import add_sample_args
    sub = parser.add_subparsers(dest="ncmd")
    add_sample_args(sub.add_parser("sample", help="sample negatives matched to positives from verified no-fire cells"))

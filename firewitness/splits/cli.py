HELP = "splits: make (alias of `firewitness score splits make`)"


def register(parser):
    from firewitness.score.cli import add_make_args
    sub = parser.add_subparsers(dest="scmd")
    add_make_args(sub.add_parser("make", help="make a published split file (blocked in space/time, by fire, with a buffer)"))

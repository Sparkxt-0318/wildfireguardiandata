"""firewitness records ... (track 49). Commands: clean, link, ids, revert, report."""
HELP = "records: clean, link, ids, revert, report (fire-record cleaning)"


def _todo(name):
    def run(args):
        print(f"records {name}: not implemented yet")
        return 3
    return run


def register(parser):
    sub = parser.add_subparsers(dest="cmd")
    for name, h in [("clean", "values, location/time repairs, duplicates -> patches + clean table"),
                    ("link", "link fire records across sources"),
                    ("ids", "permanent fire IDs and crosswalk"),
                    ("revert", "revert a cleaned table with its patch file"),
                    ("report", "coverage flags and summary report")]:
        sp = sub.add_parser(name, help=h)
        sp.set_defaults(func=_todo(name))

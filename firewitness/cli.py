"""The `firewitness` command. Tracks register commands without editing this file.

Convention: a track that has commands provides firewitness/<track>/cli.py with
    def register(parser): ...   # parser is the track's own argparse parser; add subcommands to it
and optionally HELP = "one line". Discovery imports firewitness.<track>.cli for every sub-package; a
track whose cli fails to import is reported as unavailable and does not break the others.
"""
from __future__ import annotations

import argparse
import importlib
import pkgutil
import sys

import firewitness


def discover() -> tuple[dict, dict]:
    found, failed = {}, {}
    for m in pkgutil.iter_modules(firewitness.__path__):
        if not m.ispkg:
            continue
        name = m.name
        try:
            importlib.import_module(f"firewitness.{name}")
            mod = importlib.import_module(f"firewitness.{name}.cli")
        except ModuleNotFoundError as e:
            if e.name == f"firewitness.{name}.cli":
                continue  # track has no commands yet
            failed[name] = f"{type(e).__name__}: {e}"
            continue
        except Exception as e:  # noqa: BLE001
            failed[name] = f"{type(e).__name__}: {e}"
            continue
        if hasattr(mod, "register"):
            found[name] = mod
    return found, failed


def build_parser() -> tuple[argparse.ArgumentParser, dict]:
    p = argparse.ArgumentParser(prog="firewitness", description="Wildfire data labelling and cleaning tool")
    p.add_argument("--version", action="store_true")
    sub = p.add_subparsers(dest="track")
    found, failed = discover()
    for name, mod in sorted(found.items()):
        sp = sub.add_parser(name, help=getattr(mod, "HELP", f"{name} commands"))
        mod.register(sp)
    return p, failed


def main(argv: list[str] | None = None) -> int:
    p, failed = build_parser()
    args = p.parse_args(argv)
    if args.version:
        from importlib.metadata import PackageNotFoundError, version
        try:
            print(version("firewitness"))
        except PackageNotFoundError:
            print("0.0.0+local")
        return 0
    for name, why in failed.items():
        print(f"[firewitness] track '{name}' unavailable: {why}", file=sys.stderr)
    func = getattr(args, "func", None)
    if func is None:
        p.print_help()
        return 0 if not args.track else 2
    return int(func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())

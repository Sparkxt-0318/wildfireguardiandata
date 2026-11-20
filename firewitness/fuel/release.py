"""Assemble release assets: overlays (verdict/rules/suggest/overlay.json/cards/map/report) for sealed areas and the 29 fires."""
from __future__ import annotations
import zipfile
from pathlib import Path

from . import report, runner
from .areas import SEALED
from .fires import fire_ids

KEEP = ["verdict.tif", "rules.tif", "suggest.tif", "overlay.json", "cards.npy.gz", "map.png", "report.md"]


def build(out_zip: Path, with_cards: bool = True):
    cfg = runner.region_cfg()
    items = [("M22", t) for t in SEALED] + [("M16", t) for t in SEALED] + [("M16", "F_" + f) for f in fire_ids()]
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for mk, name in items:
            d = runner.OUT_ROOT / mk / name
            if not (d / "overlay.json").exists():
                continue
            import json
            man = json.loads((d / "overlay.json").read_text())
            report.write_report(name, mk, cfg, man, d)
            for f in KEEP:
                if f == "cards.npy.gz" and not with_cards:
                    continue
                if (d / f).exists():
                    z.write(d / f, f"{mk}/{name}/{f}")
    return out_zip

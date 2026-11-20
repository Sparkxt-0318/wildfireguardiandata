"""Evidence items per window and the label tiers (protocol sections 3 and 5).

An evidence item: witness, kind, geometry (local metres, around the window centre), date interval, detail.
Verified = two items of independent kinds that agree with each other in place (geometries meet) and time
(intervals overlap, 1-day slack for UTC vs local dates). Probable = one kind. Record-only = none.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd

from firewitness.core.evidence import Witness, combine

KIND = {
    "MODIS": "HEAT", "VIIRS_SNPP": "HEAT", "VIIRS_NOAA20": "HEAT", "GOES": "HEAT", "AVHRR": "HEAT",
    "HMS_ANALYST": "HEAT", "S2_AF": "HEAT", "LANDSAT_AF": "HEAT", "DNB": "HEAT",
    "S2_SCAR": "SCAR", "LANDSAT_SCAR": "SCAR", "MCD64A1": "SCAR", "MTBS": "SCAR", "FIRECCI51": "SCAR",
    "HMS_SMOKE": "SMOKE",
    "PERIM": "PERIMETER",
}
STANDARD = {"MODIS", "VIIRS_SNPP", "VIIRS_NOAA20", "MCD64A1", "MTBS", "FIRECCI51"}
DEPENDENT = {frozenset({"MCD64A1", "MODIS"}), frozenset({"FIRECCI51", "MODIS"}), frozenset({"MTBS", "PERIM"})}
SLACK = timedelta(days=1)


@dataclass
class Item:
    witness: str
    geom: object            # shapely geometry in local metres (aeqd on the window centre)
    d0: date
    d1: date
    detail: dict = field(default_factory=dict)

    @property
    def kind(self):
        return KIND[self.witness]


def independent(a: Item, b: Item) -> bool:
    return a.kind != b.kind and frozenset({a.witness, b.witness}) not in DEPENDENT


def agree(a: Item, b: Item) -> bool:
    if a.d0 > b.d1 + SLACK or b.d0 > a.d1 + SLACK:
        return False
    if a.witness == "HMS_SMOKE" or b.witness == "HMS_SMOKE":
        return True  # smoke was attributed to this disc already (rule 6.3); its place is the disc
    return a.geom.intersects(b.geom)


def tier(items: list[Item]) -> tuple[str, list[tuple[str, str]]]:
    """('verified'|'probable'|'record-only', agreeing independent pairs)."""
    pairs = []
    by = {}
    for it in items:
        by.setdefault(it.witness, []).append(it)
    names = sorted(by)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            A, B = by[names[i]], by[names[j]]
            if not independent(A[0], B[0]):
                continue
            if any(agree(a, b) for a in A for b in B):
                pairs.append((names[i], names[j]))
    if pairs:
        return "verified", sorted(set(pairs))
    if items:
        return "probable", []
    return "record-only", []


def posterior(items: list[Item], witnesses: dict[str, Witness], prior: float, clear_negative: set[str]) -> float:
    """Posterior from core.combine. Observation True if the witness has an item, False if it had a clear look
    above the floor and found nothing, None otherwise."""
    ws = list(witnesses.values())
    have = {it.witness for it in items}
    obs = {w.name: (True if w.name in have else (False if w.name in clear_negative else None)) for w in ws}
    return combine(ws, obs, prior=prior).prob

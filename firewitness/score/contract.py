"""The score contract: unit, tolerances, threshold rule, readings, leak settings. Hashed and printed on every card."""
from __future__ import annotations

import hashlib
import json

TEMPLATE = {
    "name": "contract-template",
    "version": 1,
    "unit": {"cell_km": 0.75, "time": "day"},
    "horizon_days": 1,
    "tolerances": {"strict": {"space_cells": 0, "time_days": 0},
                   "mid": {"space_cells": 1, "time_days": 1},
                   "loose": {"space_cells": 3, "time_days": 3}},
    "threshold": {"rule": "max_f1_on_validation", "tolerance": "strict", "value": None},
    "label_readings": ["strict", "interval"],
    "event": {"min_new_cells": 5, "new_radius_cells": 1, "tolerance": "mid"},
    "leak": {"radius_cells": 3, "auc": 0.90, "min_positives": 30},
    "area_ratio_warn": 3.0,
    "hard": {"hard_km": 10.0},
    "bootstrap": {"n": 1000, "seed": 54},
}

ALLOWED_RULES = ("max_f1_on_validation", "fixed")


class ContractError(ValueError):
    pass


def validate(c: dict) -> dict:
    for k in ("unit", "horizon_days", "tolerances", "threshold", "label_readings", "event", "leak"):
        if k not in c:
            raise ContractError(f"contract is missing '{k}'")
    if c["threshold"].get("rule") not in ALLOWED_RULES:
        raise ContractError(f"threshold rule must be one of {ALLOWED_RULES} (never fitted on test)")
    if c["threshold"]["rule"] == "fixed" and not isinstance(c["threshold"].get("value"), (int, float)):
        raise ContractError("rule 'fixed' needs a numeric value")
    if len(c["tolerances"]) != 3:
        raise ContractError("exactly three named tolerances are required")
    for n in c["tolerances"].values():
        if n["space_cells"] < 0 or n["time_days"] < 0:
            raise ContractError("tolerances must be >= 0")
    if c["threshold"].get("tolerance", "strict") not in c["tolerances"]:
        raise ContractError("threshold.tolerance must name one of the tolerances")
    if c["event"].get("tolerance", "mid") not in c["tolerances"]:
        raise ContractError("event.tolerance must name one of the tolerances")
    if set(c["label_readings"]) - {"strict", "interval"} or not c["label_readings"]:
        raise ContractError("label_readings must be a non-empty subset of strict, interval")
    return c


def digest(c: dict) -> str:
    return hashlib.sha256(json.dumps(c, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(path: str) -> dict:
    return validate(json.load(open(path)))


def write_template(path: str) -> None:
    with open(path, "w") as f:
        json.dump(TEMPLATE, f, indent=1, sort_keys=True)

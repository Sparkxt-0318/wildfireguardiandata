"""Where things live. Raw downloads stay outside git; derived small tables go to results/ or release assets."""
from __future__ import annotations

import os
from pathlib import Path

WORKROOT = Path(os.environ.get("FIREWITNESS_ROOT", "/home/user/wildfire 3 (1)"))
RAW = WORKROOT / "firewitness_raw"
WORK = WORKROOT / "work"
CANON = WORK / "canon"
OUT = WORK / "out"
ICS_SRC = WORK / "ics209plus_src" / "ics209plus-source" / "excel"
RAW_PQ = WORK / "raw_parquet"
REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "results"

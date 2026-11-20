"""Region configuration. Every country-specific value lives in a JSON file so another region needs no code change."""
from __future__ import annotations

import json
from pathlib import Path


def load_region(track_dir: str | Path, region: str = "us") -> dict:
    """Load <track_dir>/config/<region>.json."""
    p = Path(track_dir) / "config" / f"{region}.json"
    if not p.is_file():
        raise FileNotFoundError(f"no region config {p}")
    return json.loads(p.read_text(encoding="utf-8"))

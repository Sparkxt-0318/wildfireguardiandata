"""Download helpers. Raw downloads go to firewitness_raw/ (outside git) and are added to its INDEX.md."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from firewitness.core.hashing import sha256_file

RAW = Path("/home/user/wildfire 3 (1)/firewitness_raw")


def index_add(rel: str, url: str, track: str = "records", raw: Path = RAW) -> None:
    p = raw / rel
    idx = raw / "INDEX.md"
    line = f"| {rel} | {url} | {datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ} | {p.stat().st_size} | {sha256_file(p)} | {track} |\n"
    text = idx.read_text() if idx.exists() else "# firewitness_raw index\n\n| path | source URL | fetched (UTC) | bytes | sha256 | track |\n|---|---|---|---|---|---|\n"
    if f"| {rel} |" not in text:
        idx.write_text(text + line)


def fetch_arcgis_layer(layer_url: str, rel_out: str, where: str = "1=1", page: int = 1000,
                       raw: Path = RAW, geometry: bool = True) -> int:
    """Page through an ArcGIS REST layer into newline-delimited GeoJSON features. Returns the feature count."""
    import requests
    out = raw / rel_out
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    offset = 0
    with open(out, "w", encoding="utf-8") as f:
        while True:
            r = requests.get(layer_url.rstrip("/") + "/query", timeout=120, params={
                "where": where, "outFields": "*", "f": "geojson", "resultOffset": offset,
                "resultRecordCount": page, "returnGeometry": "true" if geometry else "false",
                "orderByFields": "OBJECTID" if False else ""})
            r.raise_for_status()
            d = r.json()
            feats = d.get("features", [])
            for ft in feats:
                f.write(json.dumps(ft, separators=(",", ":")) + "\n")
            n += len(feats)
            if not feats or not (d.get("exceededTransferLimit") or d.get("properties", {}).get("exceededTransferLimit")):
                if len(feats) < page:
                    break
            offset += len(feats)
    index_add(rel_out, layer_url, raw=raw)
    return n

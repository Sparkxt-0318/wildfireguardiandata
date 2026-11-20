"""Hourly weather at a point from the Open-Meteo archive API (ERA5-based reanalysis, keyless)."""
from __future__ import annotations
import time
from pathlib import Path

import requests

from ..fetch.rawindex import register

URL = "https://archive-api.open-meteo.com/v1/archive"
VARS = ["wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "temperature_2m", "relative_humidity_2m"]


def fetch_weather(lat: float, lon: float, start_date: str, end_date: str, out: Path, retries: int = 6) -> Path:
    out = Path(out)
    if out.exists():
        return out
    params = {"latitude": round(lat, 4), "longitude": round(lon, 4), "start_date": start_date, "end_date": end_date,
              "hourly": ",".join(VARS), "wind_speed_unit": "ms", "timezone": "UTC"}
    last = None
    for k in range(retries):
        try:
            r = requests.get(URL, params=params, timeout=120)
            if r.status_code == 429:
                time.sleep(20 * (k + 1))
                last = "429"
                continue
            r.raise_for_status()
            h = r.json()["hourly"]
            n = len(h["time"])
            lines = ["time," + ",".join(VARS)]
            for i in range(n):
                vals = [h[v][i] for v in VARS]
                lines.append(h["time"][i] + ":00Z," + ",".join("" if x is None else repr(x) for x in vals))
            tmp = out.with_suffix(".tmp")
            tmp.write_text("\n".join(lines) + "\n")
            tmp.rename(out)
            register(out, f"{URL}?latitude={params['latitude']}&longitude={params['longitude']}&start_date={start_date}"
                          f"&end_date={end_date}&hourly={params['hourly']}&wind_speed_unit=ms&timezone=UTC",
                     "Open-Meteo archive hourly weather at final-perimeter centroid")
            return out
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (k + 1))
    raise RuntimeError(f"Open-Meteo fetch failed: {last}")

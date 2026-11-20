"""Gridded weather (gridMET, 4 km daily) for the weather check of tool 1.

grid(lat, lon, date) -> {"temp_f": daily maximum air temperature in F, "rh": daily minimum relative humidity in percent}.
Reported temperature and humidity in an incident report are taken near the afternoon, so they sit between the daily
extremes; the check in values.py only flags or fixes unit slips (Celsius written as Fahrenheit, humidity as a fraction),
which are far larger than the gap between daily maximum and a reading.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import paths

VARS = {"tmmx": "air_temperature", "rmin": "relative_humidity"}


class GridMet:
    def __init__(self, years):
        import xarray as xr
        self.xr = xr
        self.years = sorted(set(int(y) for y in years))

    def lookup(self, lat, lon, dates) -> pd.DataFrame:
        """Vectorised nearest-cell lookup. dates: datetime64 array. Returns DataFrame temp_f, rh (NaN where unavailable)."""
        lat, lon = np.asarray(lat, float), np.asarray(lon, float)
        d = pd.to_datetime(pd.Series(dates))
        out = pd.DataFrame({"temp_f": np.nan, "rh": np.nan}, index=range(len(lat)))
        for y in self.years:
            sel = np.flatnonzero((d.dt.year == y).to_numpy() & np.isfinite(lat) & np.isfinite(lon))
            if not len(sel):
                continue
            for v, col in (("tmmx", "temp_f"), ("rmin", "rh")):
                f = paths.RAW / "gridmet" / f"{v}_{y}.nc"
                if not f.exists() or f.stat().st_size < 1_000_000:
                    continue
                ds = self.xr.open_dataset(f, mask_and_scale=False)     # packed integers: 0.6 GB per year, not 2 GB of floats
                v_ = ds[VARS[v]]
                la, lo, dy = ds["lat"].values, ds["lon"].values, ds["day"].values
                ii = np.abs(la[None, :] - lat[sel][:, None]).argmin(1)
                jj = np.abs(lo[None, :] - lon[sel][:, None]).argmin(1)
                ok = (np.abs(la[ii] - lat[sel]) < 0.1) & (np.abs(lo[jj] - lon[sel]) < 0.1)
                kk = np.searchsorted(dy, d.iloc[sel].dt.normalize().to_numpy(dtype="datetime64[ns]"))
                ok &= kk < len(dy)
                kk = np.minimum(kk, len(dy) - 1)
                raw = v_.values[kk, ii, jj].astype(float)
                sf, off, fill = float(v_.attrs.get("scale_factor", 1.0)), float(v_.attrs.get("add_offset", 0.0)), v_.attrs.get("_FillValue", v_.attrs.get("missing_value"))
                if fill is not None:
                    ok &= raw != float(np.asarray(fill).ravel()[0])
                vals = raw * sf + off
                if v == "tmmx":
                    vals = (vals - 273.15) * 1.8 + 32.0
                vals = np.where(ok, vals, np.nan)
                out.loc[sel, col] = vals
                ds.close()
        return out


def make_grid(df: pd.DataFrame, lat_col, lon_col, date_col, years) -> callable:
    """Precompute the lookup for every row of df and return a dict-backed grid(lat, lon, date) for values.clean_values."""
    lat = pd.to_numeric(df[lat_col], errors="coerce").to_numpy()
    lon = pd.to_numeric(df[lon_col], errors="coerce").to_numpy()
    lon = np.where(lon > 0, -lon, lon)
    dt = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
    g = GridMet(years).lookup(lat, lon, dt.to_numpy(dtype="datetime64[ns]"))
    table = {}
    for la, lo, d, t, r in zip(lat, lon, dt, g.temp_f, g.rh):
        if pd.notna(d) and np.isfinite(la):
            table[(round(float(la), 6), round(float(abs(lo)), 6), d.date())] = {"temp_f": t, "rh": r}

    def grid(la, lo, date):
        return table.get((round(float(la), 6), round(float(abs(lo)), 6), date))
    return grid

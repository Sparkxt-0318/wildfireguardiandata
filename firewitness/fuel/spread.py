"""Surface-fire head rate per fuel class from the published Rothermel implementation (pyretechnics).

Citation: Johnson, G. W., Waeselynck, V., Lautenberger, C., Saah, D. Pyretechnics (Sig-GIS), https://github.com/pyregence/pyretechnics
implementing Rothermel (1972) with the Albini (1976) / Andrews (2012) wind adjustment and Scott & Burgan (2005) fuel models.
Units follow the library: spread rate m/min, wind m/min, slope rise/run, aspect degrees clockwise from north.
"""
from __future__ import annotations
import os
import sys
from functools import lru_cache
from pathlib import Path

DEFAULT_SRC = Path(os.environ.get("FIREWITNESS_PYRETECHNICS", Path.home() / ".cache" / "firewitness" / "pyretechnics_src"))


class Unavailable(RuntimeError):
    pass


def _import():
    for cand in (DEFAULT_SRC, Path("/tmp/claude-0/pyrsrc")):
        if (cand / "pyretechnics").is_dir() and str(cand) not in sys.path:
            sys.path.insert(0, str(cand))
    try:
        import pyretechnics.surface_fire as sf
        import pyretechnics.fuel_models as fm
        return sf, fm
    except Exception as e:  # noqa: BLE001
        raise Unavailable("pyretechnics not found; run scripts/setup_pyretechnics.sh") from e


def available() -> bool:
    try:
        _import()
        return True
    except Unavailable:
        return False


@lru_cache(maxsize=None)
def _fuel(number: int):
    sf, fm = _import()
    return fm.get_fuel_model(int(number))


@lru_cache(maxsize=200000)
def head_rate(number: int, wind_mps: float, wind_from_deg: float, slope: float, aspect: float,
              canopy_height_m: float, canopy_cover: float, d1: float, d10: float, d100: float, herb: float, woody: float) -> float:
    """Maximum (head-fire) surface spread rate, m/min. wind_mps is the 20-ft wind (the 10 m wind is used unreduced,
    which is conservative for an upper bound). canopy_cover is 0-1. Returns 0 for non-burnable models."""
    sf, fm = _import()
    if number not in fm.list_fuel_model_numbers() or not fm.is_burnable_fuel_model_number(number):
        return 0.0
    base = _fuel(number)
    mfm = fm.moisturize(base, [d1, d10, d100, d1, herb, woody])
    fmin = sf.calc_surface_fire_behavior_no_wind_no_slope(mfm, 1.0)
    waf_wind = sf.calc_midflame_wind_speed(wind_mps * 60.0, mfm.delta, canopy_height_m * 3.28084, canopy_cover)
    fmax = sf.calc_surface_fire_behavior_max(fmin, waf_wind, wind_from_deg, slope, aspect)
    return float(fmax.max_spread_rate)

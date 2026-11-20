"""Small geodesy helpers (no pyproj needed)."""
from __future__ import annotations

import math

_A = 6378137.0
_F = 1 / 298.257223563
_K0 = 0.9996


def utm_to_latlon(easting: float, northing: float, zone: int, north: bool = True) -> tuple[float, float]:
    """Inverse UTM (WGS84), Krueger series; accurate to well below a metre for our use."""
    n = _F / (2 - _F)
    a_ = _A / (1 + n) * (1 + n ** 2 / 4 + n ** 4 / 64)
    x = (easting - 500000.0) / (_K0 * a_)
    y = (northing - (0 if north else 10000000.0)) / (_K0 * a_)
    b = [n / 2 - 2 * n ** 2 / 3 + 37 * n ** 3 / 96, n ** 2 / 48 + n ** 3 / 15, 17 * n ** 3 / 480]
    xi, eta = y, x
    for j, bj in enumerate(b, start=1):
        xi -= bj * math.sin(2 * j * y) * math.cosh(2 * j * x)
        eta -= bj * math.cos(2 * j * y) * math.sinh(2 * j * x)
    chi = math.asin(math.sin(xi) / math.cosh(eta))
    d = [2 * n - 2 * n ** 2 / 3 - 2 * n ** 3, 7 * n ** 2 / 3 - 8 * n ** 3 / 5, 56 * n ** 3 / 15]
    lat = chi + sum(dj * math.sin(2 * j * chi) for j, dj in enumerate(d, start=1))
    lon0 = math.radians((zone - 1) * 6 - 180 + 3)
    lon = lon0 + math.atan2(math.sinh(eta), math.cos(xi))
    return math.degrees(lat), math.degrees(lon)


def km_per_deg(lat: float) -> tuple[float, float]:
    """(km per degree latitude, km per degree longitude) at this latitude."""
    return 111.32, 111.32 * math.cos(math.radians(lat))


def distance_km(lat1, lon1, lat2, lon2) -> float:
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 12742.0 * math.asin(math.sqrt(a))

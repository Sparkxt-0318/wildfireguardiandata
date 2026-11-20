"""Small geometry helpers: great-circle neighbour search on unit vectors (works for Alaska, Hawaii, Puerto Rico)."""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial import cKDTree

R_EARTH = 6_371_008.8


def unit_xyz(lat, lon) -> np.ndarray:
    la = np.radians(np.asarray(lat, dtype=float))
    lo = np.radians(np.asarray(lon, dtype=float))
    return np.column_stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])


def chord(dist_m: float) -> float:
    return 2.0 * math.sin(min(dist_m / R_EARTH, math.pi) / 2.0)


def haversine_m(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * R_EARTH * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


class PointIndex:
    """Points with an extent (half_m) and a date interval; query by disc and date window."""

    def __init__(self, lat, lon, half_m, d0, d1):
        self.lat = np.asarray(lat, float)
        self.lon = np.asarray(lon, float)
        self.half = np.asarray(half_m, float)
        self.d0 = np.asarray(d0, dtype="datetime64[D]")
        self.d1 = np.asarray(d1, dtype="datetime64[D]")
        self.tree = cKDTree(unit_xyz(self.lat, self.lon)) if len(self.lat) else None
        self.maxhalf = float(self.half.max()) if len(self.half) else 0.0

    def query(self, lat: float, lon: float, r_m: float, t0, t1) -> np.ndarray:
        """Indices whose footprint (circle of radius half_m) meets the disc and whose interval meets [t0, t1]."""
        if self.tree is None:
            return np.zeros(0, int)
        idx = np.asarray(self.tree.query_ball_point(unit_xyz([lat], [lon])[0], chord(r_m + self.maxhalf)), int)
        if not len(idx):
            return idx
        d = haversine_m(lat, lon, self.lat[idx], self.lon[idx])
        t0 = np.datetime64(t0, "D")
        t1 = np.datetime64(t1, "D")
        ok = (d <= r_m + self.half[idx]) & (self.d0[idx] <= t1) & (self.d1[idx] >= t0)
        return idx[ok]

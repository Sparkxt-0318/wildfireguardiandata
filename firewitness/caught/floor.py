"""Detection floors: the smallest fire a look would have seen, from pixel size, noise, view angle and background.

Heat floors follow the tests of each sensor's published fire algorithm, applied to a pixel that holds a fire of
fraction p at temperature Tf over a background Tb (Planck mixing). The floor is the smallest p (times the pixel
area at that view angle) that passes the tests. Simplifications are stated in FLOOR_NOTES and in the data card:
band radiance is taken at the band centre wavelength; contextual tests use a stated background noise.

Scar floor: protocol section 7.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

C1 = 1.191042e8   # W um^4 m^-2 sr^-1   (2hc^2)
C2 = 1.4387752e4  # um K                (hc/k)
R_E = 6371.0

FLOOR_NOTES = (
    "Heat floors: band radiance at the band-centre wavelength; fire temperature 800 K (flaming); contextual tests "
    "with background noise sigma (default 2 K, homogeneous; 4 K heterogeneous); thresholds from Giglio et al. 2016 "
    "(MODIS C6), Schroeder et al. 2014 (VIIRS 375 m), Schroeder et al. 2016 (Landsat-8, also applied to Sentinel-2 "
    "B8A/B11/B12), GOES ABI FDC ATBD (Schmidt et al.), FIMMA AVHRR. Reflectance-based floors (Landsat, Sentinel-2) "
    "convert fire radiance to top-of-atmosphere reflectance with the band solar irradiance at sun zenith 40 deg.")


def planck(lam_um: float, t: float) -> float:
    return C1 / (lam_um ** 5 * (math.exp(C2 / (lam_um * t)) - 1.0))


def bt(lam_um: float, rad: float) -> float:
    return C2 / (lam_um * math.log(1.0 + C1 / (lam_um ** 5 * rad)))


def mix_bt(lam: float, p: float, tf: float, tb: float) -> float:
    return bt(lam, p * planck(lam, tf) + (1 - p) * planck(lam, tb))


# ------------------------------------------------------------------ pixel geometry
def scan_geometry(theta_deg: float, h_km: float) -> tuple[float, float]:
    """Growth factors (along-scan, along-track) of a whisk-broom pixel at scan angle theta, vs nadir."""
    th = math.radians(theta_deg)
    rs = R_E + h_km
    s = rs / R_E * math.sin(th)
    if s >= 1:
        return float("inf"), float("inf")
    alpha = math.asin(s) - th
    dadt = (rs / R_E) * math.cos(th) / math.sqrt(1 - s * s) - 1.0
    along_scan = dadt * R_E / h_km
    slant = R_E * math.sin(alpha) / math.sin(th) if th > 0 else h_km
    return along_scan, slant / h_km


def pixel_area_m2(sensor: str, view_deg: float | None = None) -> float:
    """Pixel area at a view (scan) angle; None = edge of scan (the floor that holds whatever the angle)."""
    if sensor == "MODIS":
        th = 55.0 if view_deg is None else view_deg
        a, b = scan_geometry(th, 705.0)
        return (1000 * a) * (1000 * b)
    if sensor.startswith("VIIRS"):
        th = 56.28 if view_deg is None else view_deg
        agg = 3 if th < 31.59 else 2 if th < 44.68 else 1
        a, b = scan_geometry(th, 829.0)
        return (125.0 * agg * a) * (375.0 * b)
    if sensor == "AVHRR":
        th = 55.4 if view_deg is None else view_deg
        a, b = scan_geometry(th, 833.0)
        return (1100 * a) * (1100 * b)
    if sensor == "GOES":
        vza = 65.0 if view_deg is None else view_deg  # CONUS edge for GOES-East/West
        # 2 km at the sub-satellite point; area grows ~ 1/cos^3 in the scan direction for a geostationary view
        return (2000.0 ** 2) / max(math.cos(math.radians(vza)), 0.2) ** 2.2
    if sensor == "LANDSAT":
        return 30.0 * 30.0
    if sensor == "S2":
        return 20.0 * 20.0
    raise ValueError(sensor)


# ------------------------------------------------------------------ thermal tests
@dataclass
class Background:
    t4: float = 305.0   # 4 um background brightness temperature (K); day includes reflected sunlight
    t11: float = 300.0
    sigma: float = 2.0  # background noise of T4 and of T4-T11 (K)
    day: bool = True


THERMAL = {
    # sensor: (lambda4, lambda11, abs_day, abs_night, prelim_t4_day, prelim_t4_night, prelim_dt_day, prelim_dt_night,
    #          ctx_dt_min, k_dt, k_t4)
    "MODIS": (3.96, 11.03, 360.0, 320.0, 310.0, 305.0, 10.0, 10.0, 6.0, 3.5, 3.0),
    "VIIRS": (3.74, 11.45, 367.0, 320.0, 325.0, 295.0, 25.0, 10.0, 6.0, 3.5, 3.0),
    "AVHRR": (3.74, 10.8, 360.0, 320.0, 315.0, 305.0, 15.0, 10.0, 6.0, 3.5, 3.0),
    "GOES": (3.9, 11.2, 360.0, 320.0, 300.0, 295.0, 8.0, 6.0, 4.0, 3.0, 3.0),
}


def _passes(sensor: str, p: float, tf: float, bg: Background) -> bool:
    l4, l11, ad, an, pt_d, pt_n, pd_d, pd_n, cmin, kdt, k4 = THERMAL[sensor]
    t4 = mix_bt(l4, p, tf, bg.t4)
    t11 = mix_bt(l11, p, tf, bg.t11)
    if t4 >= (ad if bg.day else an):
        return True
    dt = t4 - t11
    pre = t4 >= (pt_d if bg.day else pt_n) and dt >= (pd_d if bg.day else pd_n)
    ctx = (dt - (bg.t4 - bg.t11)) >= max(cmin, kdt * bg.sigma) and (t4 - bg.t4) >= k4 * bg.sigma
    return pre and ctx


def heat_floor_m2(sensor: str, view_deg: float | None = None, bg: Background | None = None,
                  tf: float = 800.0) -> float:
    """Smallest flaming area (m2) at temperature tf that the sensor's tests would flag."""
    bg = bg or Background()
    key = "VIIRS" if sensor.startswith("VIIRS") else sensor
    area = pixel_area_m2(sensor, view_deg)
    lo, hi = 0.0, 1.0
    if not _passes(key, hi, tf, bg):
        return float("inf")
    for _ in range(60):
        mid = (lo + hi) / 2
        if _passes(key, mid, tf, bg):
            hi = mid
        else:
            lo = mid
    return hi * area


# ------------------------------------------------------------------ reflective (Landsat-8 / Sentinel-2) tests
# solar irradiance at the band (W m^-2 um^-1): OLI B5 0.865, B6 1.61, B7 2.2; S2A B8A, B11, B12
ESUN = {"LANDSAT": (1044.0, 225.7, 81.1), "S2": (955.19, 245.59, 85.25)}
LAM = {"LANDSAT": (0.865, 1.61, 2.20), "S2": (0.865, 1.61, 2.19)}


def refl_fire_pixel(sensor: str, p: float, tf: float, rho_bg=(0.30, 0.25, 0.15), sza_deg: float = 40.0):
    e5, e6, e7 = ESUN[sensor]
    l5, l6, l7 = LAM[sensor]
    mu = math.cos(math.radians(sza_deg))
    out = []
    for rb, e, lam in zip(rho_bg, (e5, e6, e7), (l5, l6, l7)):
        out.append((1 - p) * rb + p * math.pi * planck(lam, tf) / (e * mu))
    return out


def reflective_passes(r5: float, r6: float, r7: float, ctx_r75: float = 0.5, ctx_r7: float = 0.15,
                      sd_r75: float = 0.05, sd_r7: float = 0.02) -> bool:
    """Schroeder et al. 2016 Landsat-8 tests (unambiguous or candidate + contextual)."""
    r75 = r7 / max(r5, 1e-6)
    if r75 > 2.5 and (r7 - r5) > 0.3 and r7 > 0.5:
        return True
    if r6 > 0.8 and r7 < 0.1:
        return True
    cand = r75 > 1.8 and (r7 - r5) > 0.17 and r7 / max(r6, 1e-6) > 1.6
    ctx = r75 > ctx_r75 + max(3 * sd_r75, 0.8) and r7 > ctx_r7 + max(3 * sd_r7, 0.08)
    return cand and ctx


def reflective_floor_m2(sensor: str, tf: float = 800.0, rho_bg=(0.30, 0.25, 0.15)) -> float:
    area = pixel_area_m2(sensor)
    if not reflective_passes(*refl_fire_pixel(sensor, 1.0, tf, rho_bg)):
        return float("inf")
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if reflective_passes(*refl_fire_pixel(sensor, mid, tf, rho_bg), ctx_r75=rho_bg[2] / rho_bg[0],
                             ctx_r7=rho_bg[2]):
            hi = mid
        else:
            lo = mid
    return hi * area


# ------------------------------------------------------------------ scar floor
def scar_floor_m2(threshold: float, pixel_m: float, n_min: int = 4, dnbr_ref: float = 0.25) -> float:
    """Protocol section 7: (sqrt(N_min)+1)^2 * p^2 * f_min, f_min = T / dNBR_ref; infinite if f_min > 1."""
    f = threshold / dnbr_ref
    if f > 1:
        return float("inf")
    return (math.sqrt(n_min) + 1) ** 2 * pixel_m ** 2 * f


def floor_table(day: bool = True) -> list[dict]:
    """The published floor table: heat sensors at nadir and edge of scan, day and night, plus scar looks."""
    rows = []
    for s in ["MODIS", "VIIRS", "AVHRR", "GOES"]:
        for dd in ([True, False] if day is None else [day]):
            bg = Background(305.0, 300.0, 2.0, True) if dd else Background(285.0, 285.0, 2.0, False)
            for v in [0.0, None]:
                vv = 30.0 if (s == "GOES" and v == 0.0) else v
                rows.append({"sensor": s, "day": dd, "view_deg": "edge" if v is None else vv,
                             "pixel_m2": round(pixel_area_m2(s, vv)), "floor_m2": round(heat_floor_m2(s, vv, bg), 1)})
    for s in ["LANDSAT", "S2"]:
        rows.append({"sensor": s + "_hotspot", "day": True, "view_deg": 0.0, "pixel_m2": pixel_area_m2(s),
                     "floor_m2": round(reflective_floor_m2(s), 2)})
    for s, p in [("S2_scar", 20.0), ("LANDSAT_scar", 30.0)]:
        for t in [0.10, 0.15, 0.20]:
            rows.append({"sensor": s, "day": True, "view_deg": 0.0, "pixel_m2": p * p, "threshold": t,
                         "floor_m2": round(scar_floor_m2(t, p), 1)})
    return rows

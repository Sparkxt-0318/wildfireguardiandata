"""Rule-based fuel-map checker. Deterministic; no model of any kind; never reads field plots.

check(layers, cfg) -> Result with verdict / rule bit-set / suggested class rasters (an overlay: inputs untouched).
Rule ids and thresholds are those of protocol/FUEL_PROTOCOL.md (+ amendment A1); thresholds live in config/<region>.json.
"""
from __future__ import annotations
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from .layers import Layers

# verdict codes
NODATA, CONSISTENT, STALE, CONTRADICTED, UNKNOWN = 0, 1, 2, 3, 4
VERDICT_NAMES = {0: "nodata", 1: "consistent", 2: "stale", 3: "contradicted", 4: "unknown"}
# rule bits
RULE_BITS = {"R1.1": 0, "R1.2": 1, "R1.3": 2, "R1.4": 3, "R1.5": 4, "R1.6": 5, "R1.7": 6, "R1.9": 7,
             "S1": 8, "S2": 9, "R3a": 10, "R3b": 11, "U0": 12}
BIT_RULES = {v: k for k, v in RULE_BITS.items()}
CONTRADICTION_RULES = ("R1.1", "R1.2", "R1.3", "R1.4", "R1.5", "R1.6", "R1.7", "R1.9", "R3a", "R3b")
GROUP_CODES = {"NB": 1, "GR": 2, "GS": 3, "SH": 4, "TU": 5, "TL": 6, "SB": 7}
GROUP_NAMES = {v: k for k, v in GROUP_CODES.items()}


@dataclass
class Result:
    verdict: np.ndarray    # uint8
    rules: np.ndarray      # uint32 bit-set
    suggest: np.ndarray    # int16 suggested class, 0 none
    sgroup: np.ndarray     # uint8 suggested group code, 0 none
    S: np.ndarray          # int8 tree-evidence score
    n: np.ndarray          # uint8 number of tree-evidence layers available
    group: np.ndarray      # uint8 group of the map class


def group_lut(cfg):
    lut = np.zeros(1024, np.uint8)
    for g, codes in cfg["groups"].items():
        for c in codes:
            lut[c] = GROUP_CODES[g]
    return lut


def tree_evidence(L: Layers, cfg):
    ind, iv = cfg["indicators"], cfg["nlcd"]
    v_lc = (L.lc > 0) & (L.lc <= 95)
    i_lc = np.where(np.isin(L.lc, iv["forest"]), 1, -1)
    v_tcc = L.tcc <= 100
    i_tcc = np.where(L.tcc >= ind["tcc_tree"], 1, np.where(L.tcc <= ind["tcc_none"], -1, 0))
    v_chm = L.chm_max != 255
    i_chm = np.where((L.chm_cov >= ind["chm_cov_tree"]) & (L.chm_max >= ind["chm_max_tree"]), 1,
                     np.where(L.chm_max < ind["chm_max_none"], -1, 0))
    wt = L.wc[10]
    v_wc = wt != 255
    i_wc = np.where(wt >= ind["wc_tree"], 1, np.where(wt <= ind["wc_none"], -1, 0))
    inds = {"nlcd": (i_lc, v_lc), "tcc": (i_tcc, v_tcc), "chm": (i_chm, v_chm), "wc": (i_wc, v_wc)}
    S = sum(np.where(v, i, 0) for i, v in inds.values()).astype(np.int8)
    n = sum(v.astype(np.uint8) for _, v in inds.values()).astype(np.uint8)
    return S, n, inds


def check(L: Layers, cfg: dict, arrival=None) -> Result:
    R = cfg["rules"]
    lut = group_lut(cfg)
    cls = L.fbfm.astype(np.int32)
    in_range = (cls >= 0) & (cls < 1024)
    grp = np.where(in_range, lut[np.clip(cls, 0, 1023)], 0).astype(np.uint8)
    valid = grp > 0
    S, n, inds = tree_evidence(L, cfg)
    nl = cfg["nlcd"]
    lc = L.lc
    wc = {k: v.astype(np.int16) for k, v in L.wc.items()}
    wcv = L.wc[10] != 255
    tcc = np.where(L.tcc <= 100, L.tcc, 255).astype(np.int16)
    chm_ok = L.chm_max != 255
    burnable = (grp >= 2)
    timber = np.isin(grp, [5, 6, 7])
    nontimber = np.isin(grp, [2, 3, 4])
    rules = np.zeros(L.fbfm.shape, np.uint32)

    def fire(name, mask):
        nonlocal rules
        mask = mask & valid
        rules |= (mask.astype(np.uint32) << np.uint32(RULE_BITS[name]))
        return mask

    # --- family 1
    r = R["R1_1"]
    f11 = fire("R1.1", np.isin(grp, [5, 6]) & (n >= r["min_n"]) & (S <= r["max_S"]))
    r = R["R1_2"]
    all_tree = (n == 4) & (S == 4)
    f12 = fire("R1.2", nontimber & all_tree & (tcc >= r["tcc_min"]) & chm_ok & (L.chm_max >= r["chm_max_min"]))
    f13 = fire("R1.3", burnable & np.isin(lc, nl["water"]) & wcv & (wc[80] >= R["R1_3"]["wc_water"]))
    f14 = fire("R1.4", burnable & np.isin(lc, nl["snow"]) & wcv & (wc[70] >= R["R1_4"]["wc_snow"]))
    f15 = fire("R1.5", burnable & np.isin(lc, nl["dev_high"]) & wcv & (wc[50] >= R["R1_5"]["wc_built"]))
    r = R["R1_6"]
    f16 = fire("R1.6", burnable & ~np.isin(cls, r["allowed"]) & np.isin(lc, nl["barren"]) & wcv & (wc[60] >= r["wc_bare"])
               & (tcc <= r["tcc_max"]) & chm_ok & (L.chm_max < r["chm_max_lt"]))
    r = R["R1_7"]
    nat = wc[10] + wc[20] + wc[30] + wc[100]
    f17 = fire("R1.7", np.isin(cls, [91, 93, 99]) & np.isin(lc, nl["natural_veg"]) & wcv & (nat >= r["wc_natural"])
               & (wc[50] <= r["wc_built_max"]) & (wc[40] <= r["wc_crop_max"]))
    r = R["R1_9"]
    f19a = (grp == 2) & (lc == 52) & wcv & (wc[20] >= r["wc_lifeform"]) & (tcc < r["tcc_lt"])
    f19b = (grp == 4) & (lc == 71) & wcv & (wc[30] >= r["wc_lifeform"]) & (tcc < r["tcc_lt"])
    f19 = fire("R1.9", f19a | f19b)
    # --- family 2 (A1): perimeter-year and Hansen loss since the map year
    s1 = fire("S1", L.post_fire_year > 0)
    my = L.map_year
    s2 = fire("S2", (L.loss_year > my) & (L.tc2000 >= R["S2"]["tc2000_min"]) & ~s1)
    # --- family 3
    f3a = fire("R3a", np.isin(cls, [98, 99]) & L.pre_burn)
    f3b = np.zeros_like(f3a)
    if arrival is not None:
        f3b = fire("R3b", arrival)
    u0 = ~valid
    rules |= (u0.astype(np.uint32) << np.uint32(RULE_BITS["U0"]))

    contra = f11 | f12 | f13 | f14 | f15 | f16 | f17 | f19 | f3a | f3b
    stale = s1 | s2

    # --- consistent support (protocol 3.5, step 3)
    c = R["consistent"]
    enough = n >= c["min_n"]
    sup_timber = timber & (S >= c["timber_S_min"])
    sup_non = nontimber & (S <= c["nontimber_S_max"])
    veg_share = wc[10] + wc[20] + wc[30] + wc[100]
    sup_nb = (
        ((cls == 98) & ((np.isin(lc, nl["water"])) | (wcv & (wc[80] >= c["nb_water_wc"])))) |
        ((cls == 92) & ((lc == 12) | (wcv & (wc[70] >= c["nb_water_wc"])))) |
        ((cls == 91) & (np.isin(lc, nl["dev_any"]) | (wcv & (wc[50] >= c["nb_built_wc"])))) |
        ((cls == 93) & (np.isin(lc, nl["crop"]) | (wcv & (wc[40] >= c["nb_crop_wc"])))) |
        ((cls == 99) & ((lc == 31) | (wcv & (wc[60] >= c["nb_bare_wc"])) |
                        (wcv & (veg_share <= 30) & (tcc <= 5) & chm_ok & (L.chm_max < 2))))
    )
    supported = enough & (sup_timber | sup_non | sup_nb)

    verdict = np.full(L.fbfm.shape, UNKNOWN, np.uint8)
    verdict[supported] = CONSISTENT
    verdict[contra] = CONTRADICTED
    verdict[stale] = STALE
    verdict[u0] = UNKNOWN  # U0: nodata or unmapped class is 'unknown' (protocol 3)
    # --- suggestions
    sgroup = np.zeros(L.fbfm.shape, np.uint8)
    shrub_ok = (lc == 52) & wcv & (wc[20] >= 50)
    grass_ok = (lc == 71) & wcv & (wc[30] >= 50)
    sgroup[f11 & shrub_ok] = GROUP_CODES["SH"]
    sgroup[f11 & grass_ok] = GROUP_CODES["GR"]
    sgroup[f17 & shrub_ok] = GROUP_CODES["SH"]
    sgroup[f17 & grass_ok] = GROUP_CODES["GR"]
    sgroup[f19a] = GROUP_CODES["SH"]
    sgroup[f19b] = GROUP_CODES["GR"]
    suggest = np.zeros(L.fbfm.shape, np.int16)
    suggest[f13] = 98
    suggest[f14] = 92
    suggest[f15] = 91
    suggest[f16] = 99
    suggest = _donor_classes(suggest, sgroup, cls, verdict, cfg)
    return Result(verdict, rules, suggest, sgroup, S, n, grp)


def _donor_classes(suggest, sgroup, cls, verdict, cfg):
    """Most frequent class of the suggested group among 'consistent' cells in an 11x11 window, if >= 5 donors."""
    sg = cfg["rules"]["suggest"]
    win, mind = sg["window"], sg["min_donors"]
    for gname in ("SH", "GR"):
        gc = GROUP_CODES[gname]
        need = sgroup == gc
        if not need.any():
            continue
        counts = []
        codes = cfg["groups"][gname]
        for code in codes:
            donor = ((verdict == CONSISTENT) & (cls == code)).astype(np.float32)
            counts.append(ndimage.uniform_filter(donor, size=win, mode="constant") * win * win)
        cnt = np.stack(counts)
        tot = cnt.sum(axis=0)
        best = np.array(codes, dtype=np.int16)[cnt.argmax(axis=0)]
        ok = need & (tot >= mind - 0.5)
        suggest[ok] = best[ok]
    return suggest

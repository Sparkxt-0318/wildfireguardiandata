"""Tool 1, values: detect and fix bad VALUES in fire-record tables, as patches (nothing is overwritten).

Entry point::

    patches, flags = clean_values(df, table, cfg, id_col="rid", grid=None)

``table`` is one of ``ics_sitreps``, ``fpafod``, ``ics_incidents``, ``generic``. ``cfg`` is the region
configuration (``firewitness.core.load_region``): placeholders, area units, plausible ranges all come from it
(optional overrides live under ``cfg["values"]``, see ``DEFAULTS``). ``df`` is read as strings (``dtype=str``)
or typed; a patch's ``old`` is always the cell exactly as it is in ``df`` so ``apply_patches(strict=True)``
works.  Every rule is deterministic, every patch carries evidence and a confidence, and a cell receives at most
one patch.  When the evidence is insufficient nothing is patched and the cell is returned in ``flags``
(columns ``record_id, field, value, reason, detail``).

Rules (rule name -> what it does, tolerances)
--------------------------------------------
``val:placeholder``
    Numeric sentinels become ``core.missing()``.  Negative sentinels at or below -999 are always blanked (no
    fire quantity is -9999).  Other configured sentinels (99999, 999999, 9999, 99, -99 ...) are blanked only
    when the column itself shows it: the value occurs >= 3 times and >= 5x more often than any other value
    within +-5 percent of it, in a column with > 20 distinct values (a real 0 or 99 never meets this); or when
    the value is an isolated spike inside one incident's report sequence.  Text placeholders (N/A, NULL,
    UNKNOWN, ?, - ...) are blanked unless they make up more than half of the column (then it is a category).
    A cell that is already empty is left alone.
``val:hidden_chars`` / ``val:mojibake``
    Text cells: NBSP and other unicode spaces become a space, zero-width characters, BOM and control
    characters are removed, leading/trailing whitespace is stripped; cp1252/utf-8 confusion (``Â `` ``â€™``
    ``Ã©``) is decoded back.  The new text is the old text with only those characters changed.
``val:unit_slip``
    A value off by a unit factor (acres/hectare 2.471, km2 247.1, sq mile 640, 1000x) from the same record's
    other sources (``FINAL_ACRES`` vs ``FOD_FINAL_ACRES``; ``FIRE_SIZE`` vs ``FIRE_SIZE_CLASS`` and any
    ``ICS_FINAL_ACRES``/``MTBS_ACRES`` style column) or from the neighbours in the incident's report
    sequence.  The ratio must be within +-1 percent of exactly one factor against an independent source
    (+-3 percent against a trend) and the corrected value must land in the neighbours' trend (+-3 percent) or
    in the stated size class.  The corrected value is rounded no further than the original's own rounding
    allows, so a planted slip is undone exactly.
``val:sequence_glitch``
    Impossible sequences within one incident (ordered by report date; a gap over 120 days starts a new
    sequence): area, percent contained, cumulative cost fall.  Only the clear single-report glitch is
    patched: value below (or above) both neighbours that are themselves in order, neighbours within 30
    percent of each other, and exactly one factor (10, 100, 1000, unit factors; each way) puts the value inside
    the neighbours' range +-3 percent.  Otherwise the cell is flagged (``*_isolated_glitch``,
    ``area_shrinks`` ...).  An isolated spike equal to a configured sentinel is blanked instead.
``val:weather_unit_slip``
    Temperature (F column) reported in C and relative humidity reported as a fraction,
    judged against the report's neighbours, and against ``grid(lat, lon, date)`` when given.  Temperatures
    are compared on the Kelvin scale with 3 percent tolerance (about 9 K); RH within +-10 points.  Range
    checks (RH in [0, 100], temperature range, wind vs gust, negative wind) only flag.

``grid`` (optional) is a callable ``grid(lat, lon, date) -> {"temp_f": float, "rh": float}`` (``None`` or NaN
values are ignored); the caller supplies it, this module never downloads weather.  It is called once per
report with a temperature or RH, so pass a cached/sampled implementation for big tables.

Everything is vectorised with numpy/pandas; there is no per-row python loop over the table except in the
patch objects themselves (and the optional grid).
"""
from __future__ import annotations

import re
from typing import Callable

import numpy as np
import pandas as pd

from firewitness.core import Patch, missing

__all__ = ["clean_values", "DEFAULTS", "TABLES"]

DEFAULTS = {
    "slip_tol": 0.03,            # relative tolerance for neighbour/trend evidence
    "cross_tol": 0.01,           # relative tolerance for independent-source ratio evidence
    "max_neighbour_ratio": 1.3,  # neighbours of a glitch must be within this ratio of each other
    "shrink_tol": {"area": 0.01, "cost": 0.10, "ppl_days": 0.10, "pct": 0.0},  # fall counted as shrinking
    "glitch_ratio": 2.0,         # an isolated value is a glitch when below prev/2 or above 2*next
    "pct_fall_points": 10.0,     # contained percent falling by this many points is flagged
    "break_days": 120,           # gap that starts a new report sequence of the same id
    "min_level": {"area": 10.0, "cost": 1000.0, "pct": 10.0, "ppl_days": 100.0},
    "temp_f_range": [-40.0, 135.0],
    "rh_range": [0.0, 100.0],
    "wind_max_mph": 150.0,
    "rh_window_points": 10.0,
    "context_ratio": 5.0,        # sentinel must out-number its neighbours this much
    "fire_size_max_acres": 2.0e6,
    # NWCG fire size classes (upper bound inclusive for A, exclusive otherwise)
    "size_classes": [["A", 0.25], ["B", 10.0], ["C", 100.0], ["D", 300.0], ["E", 1000.0], ["F", 5000.0], ["G", None]],
}

# strong tokens are placeholders anywhere; the others (NONE, UNKNOWN, UNK, NA, ...) are legitimate answers in
# narrative and low-cardinality category columns and are blanked only in name/identifier-like columns (by column name)
_STRONG_TEXT = {"N/A", "NULL", "NAN", "?", "-", "--", "TBD", "TBA"}
_NAMELIKE_COL = re.compile(r"(NAME|(^|_)ID|IDENTIFIER|NUMBER|CODE|(^|_)NUM)($|_)", re.I)
_LONG_TEXT_LEN = 60       # median length at which a column is treated as narrative text

# column aliases per role, first present wins (case-insensitive); area/uom/pct/uom are paired by index
TABLES = {
    "ics_sitreps": {
        "group": ["INCIDENT_ID", "INC_IDENTIFIER", "INCIDENT_NUMBER"],
        "date": ["REPORT_TO_DATE", "REPORT_DATE", "CREATED_DATE"],
        "hour": ["HOUR"],
        "area": [("ACRES", None), ("CURR_INCIDENT_AREA", "CURR_INC_AREA_UOM"),
                 ("CURR_INCIDENT_AREA", "CURR_INC_AREA_UOM_IDENTIFIER"), ("AREA", "AREA_MEASUREMENT")],
        "pct": [("PCT_CONTAINED_COMPLETED", "PCT_CONT_COMPL_UOM_ABBREV"), ("PCT_CONTAINED_COMPLETED", None),
                ("P_CONTAIN", None)],
        "cost": ["EST_IM_COST_TO_DATE", "COSTS_TO_DATE"],
        "ppl_days": ["PERSONNEL_DAYS", "TOTAL_PERSONNEL_DAYS", "CUM_PERSONNEL_DAYS"],
        "temp": ["C_TEMP", "TEMP_F", "TEMP"],
        "rh": ["C_RH", "RH"],
        "wind": ["C_WIND_SPEED", "WIND_SPEED"],
        "gust": ["C_WIND_GUST", "WIND_GUST", "C_GUST", "GUSTS"],
        "lat": ["POO_LATITUDE", "LATITUDE", "FOD_POO_LATITUDE"],
        "lon": ["POO_LONGITUDE", "LONGITUDE", "FOD_POO_LONGITUDE"],
    },
    "fpafod": {
        "size": ["FIRE_SIZE"], "size_class": ["FIRE_SIZE_CLASS"],
        "refs": ["ICS_FINAL_ACRES", "EVENT_FINAL_ACRES", "MTBS_ACRES", "REF_ACRES"],
        "disc": ["DISCOVERY_DATE"], "cont": ["CONT_DATE"],
    },
    "ics_incidents": {
        "size": ["FINAL_ACRES"], "refs": ["FOD_FINAL_ACRES"], "corroborate": ["FIRED_ACRES"],
        "disc": ["DISCOVERY_DATE"], "cont": ["FINAL_REPORT_DATE"],
        "peak": ["WF_PEAK_PERSONNEL"], "sum": ["TOTAL_PERSONNEL_SUM"],
    },
    "generic": {},
}

# hidden-character machinery (code points given as numbers so that invisible characters survive any editor)
_ZW_CP = [0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x2060, 0xFEFF, 0x00AD, 0x2028, 0x2029,
          0x202A, 0x202B, 0x202C, 0x202D, 0x202E]
_SPACE_CP = [0x00A0, 0x1680, *range(0x2000, 0x200B), 0x202F, 0x205F, 0x3000]
_ODD_TABLE = {c: " " for c in _SPACE_CP}
_ZW_TABLE = {c: None for c in _ZW_CP}
_CTRL_RE = re.compile(r"[\x00-\x08\x0e-\x1b\x7f]")      # removed
_CTRL_SEP_RE = re.compile(r"[\x0b\x0c\x1c-\x1f]")        # separators -> a space
_MOJI_TAIL = r"[\u0080-\u00bf\u0152\u0153\u0160\u0161\u0178\u017d\u017e\u0192\u02c6\u02dc\u2013-\u203a\u20ac\u2122]"
_MOJI_SEQ = re.compile(r"[\u00c2-\u00f4]" + _MOJI_TAIL + "{1,3}")
_DETECT_RE = (  # RE2 syntax (pyarrow string kernels): \x{HEX}
    r"^\s|\s$|[" + "".join("\\x{%X}" % c for c in _SPACE_CP + _ZW_CP) + r"\x{0}-\x{8}\x{B}\x{C}\x{E}-\x{1F}\x{7F}-\x{9F}]|"
    r"[\x{C2}-\x{F4}][\x{80}-\x{BF}\x{152}\x{153}\x{160}\x{161}\x{178}\x{17D}\x{17E}\x{192}\x{2C6}\x{2DC}"
    r"\x{2013}-\x{203A}\x{20AC}\x{2122}]")
_DETECT_PY = re.sub(r"\\x\{([0-9A-F]+)\}", lambda m: "\\U%08X" % int(m.group(1), 16), _DETECT_RE)
_OK_DECODED = set(map(chr, [0xA0, 0x2013, 0x2014, 0x2018, 0x2019, 0x201A, 0x201C, 0x201D, 0x201E, 0x2022, 0x2026,
                            0xB0, 0xA9, 0xAE, 0xB1, 0xB7, 0xBC, 0xBD, 0xBE, 0x20AC, 0x2122, 0x20]))


def _fix_seq(m) -> str:
    s = m.group()
    for enc in ("cp1252", "latin-1"):
        try:
            t = s.encode(enc).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if t and all((c.isalpha() and ord(c) <= 0x17F) or c in _OK_DECODED for c in t):
            return t
    return s


def _demoji(s: str) -> str:
    """Decode cp1252/latin-1 mojibake of utf-8 text (sequence by sequence); sequences that decode to junk stay."""
    return _MOJI_SEQ.sub(_fix_seq, s)


def _clean_text(s: str) -> tuple[str, list[str]]:
    """Return (cleaned text, list of fixes applied)."""
    fixes = []
    t = _demoji(s)
    if t != s:
        fixes.append("mojibake")
    u = t.translate(_ODD_TABLE)
    if u != t:
        fixes.append("odd_space")
    v = u.translate(_ZW_TABLE)
    if v != u:
        fixes.append("zero_width")
    w = _CTRL_SEP_RE.sub(" ", _CTRL_RE.sub("", v))
    if w != v:
        fixes.append("control")
    # C1 controls left over: decode through cp1252 where defined (they are cp1252 bytes read as latin-1)
    if any("\x80" <= ch <= "\x9f" for ch in w):
        w2 = "".join(_c1(ch) for ch in w)
        if w2 != w:
            fixes.append("c1_control")
        w = w2
    x = w.strip()
    if x != w:
        fixes.append("strip")
    return x, fixes


def _c1(ch: str) -> str:
    if "\x80" <= ch <= "\x9f":
        try:
            return bytes([ord(ch)]).decode("cp1252")
        except UnicodeDecodeError:
            return ""
    return ch


# small helpers --------------------------------------------------------------------------------------------
def _decimals(sv) -> int:
    if isinstance(sv, str):
        m = re.fullmatch(r"\s*[-+]?\d*\.(\d+)\s*", sv)
        return len(m.group(1)) if m else 0
    return 0


def _round_like(y: float, x_dec: int, k: float) -> tuple[float, int]:
    """Round the corrected value no further than the original's own rounding allows (undoes a planted slip)."""
    bound = max(0.5 * 10.0 ** (-x_dec) * abs(k), 1e-4 * abs(y), 1e-12)
    for d in range(0, 7):
        r = round(y, d)
        if abs(r - y) <= bound:
            return r, d
    return round(y, 6), 6


def _py(v):
    return v.item() if isinstance(v, np.generic) else v


def _find(df: pd.DataFrame, names) -> str | None:
    low = {str(c).lower(): c for c in df.columns}
    for n in names:
        if str(n).lower() in low:
            return low[str(n).lower()]
    return None


def _is_numeric_dtype(s: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)


def _to_num(s: pd.Series) -> np.ndarray:
    if _is_numeric_dtype(s):
        return s.to_numpy(dtype=float, na_value=np.nan)
    st = s.astype("string").str.strip()
    return pd.to_numeric(st, errors="coerce").to_numpy(dtype=float, na_value=np.nan)


def _to_dates(s: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    st = s.astype("string")
    d = pd.to_datetime(st.str.slice(0, 10), format="%Y-%m-%d", errors="coerce")
    bad = d.isna() & st.notna() & (st.str.strip() != "")
    if bad.any():
        d.loc[bad] = pd.to_datetime(st[bad], errors="coerce", format="mixed")
    return d


class _Ctx:
    """State of one clean_values call."""

    def __init__(self, df, table, cfg, id_col, grid):
        if table not in TABLES:
            raise ValueError(f"unknown table {table!r}; expected one of {sorted(TABLES)}")
        self.df, self.table, self.cfg, self.grid = df, table, cfg, grid
        self.p = {**DEFAULTS, **cfg.get("values", {})}
        self.id_col = id_col if id_col in df.columns else None
        self.rid = (df[id_col].astype(str) if self.id_col else df.index.to_series().astype(str)).to_numpy()
        self.patches: list[Patch] = []
        self.touched: set[tuple[int, str]] = set()
        self._fl = {"record_id": [], "field": [], "value": [], "reason": [], "detail": []}
        self._cache: dict[str, np.ndarray] = {}
        self._dec: dict[str, int] = {}
        self.blank: dict[str, np.ndarray] = {}      # cells already patched/blanked, per column
        au = cfg.get("area_units", {})
        self.acres_per_ha = float(au.get("acres_per_hectare", 2.47105))
        self.acres_per_km2 = float(au.get("acres_per_km2", 247.105))
        self.acres_per_sqmi = float(au.get("acres_per_sq_mile", 640.0))
        self.num_ph = [float(v) for v in cfg.get("placeholders_numeric", [])]
        self.text_ph = {str(v).strip().upper() for v in cfg.get("placeholders_text", []) if str(v).strip()}
        self.skip_cols = {self.id_col} if self.id_col else set()

    # ---- emit ----
    def patch(self, pos, col, new, rule, evidence, conf) -> bool:
        key = (int(pos), col)
        if key in self.touched:
            return False
        old = _py(self.df[col].iat[int(pos)])
        if isinstance(new, dict) and isinstance(old, float) and np.isnan(old):
            return False
        try:
            if old == new:
                return False
        except Exception:
            pass
        self.patches.append(Patch(self.rid[int(pos)], str(col), old, new, rule, evidence, round(float(conf), 3)))
        self.touched.add(key)
        if col in self.blank:
            self.blank[col][int(pos)] = True
        return True

    def flag(self, pos, col, reason, detail=""):
        pos = np.atleast_1d(np.asarray(pos, dtype=np.int64))
        if not len(pos):
            return
        vals = self.df[col].to_numpy(dtype=object)[pos]
        self._fl["record_id"].extend(self.rid[pos].tolist())
        self._fl["field"].extend([str(col)] * len(pos))
        self._fl["value"].extend([_py(v) for v in vals])
        self._fl["reason"].extend([reason] * len(pos))
        d = detail if isinstance(detail, (list, np.ndarray)) else [detail] * len(pos)
        self._fl["detail"].extend(list(d))

    def flags_df(self):
        out = pd.DataFrame(self._fl, columns=["record_id", "field", "value", "reason", "detail"])
        out["value"] = out["value"].astype(object)
        return out

    # ---- column access ----
    def num(self, col) -> np.ndarray:
        """Numeric view of a column with already-patched cells set to NaN."""
        if col not in self._cache:
            self._cache[col] = _to_num(self.df[col])
            self.blank[col] = np.zeros(len(self.df), bool)
        out = self._cache[col].copy()
        out[self.blank[col]] = np.nan
        return out

    def area_factors(self, digits=False):
        f = [("hectare_vs_acre", self.acres_per_ha), ("km2_vs_acre", self.acres_per_km2),
             ("sqmile_vs_acre", self.acres_per_sqmi), ("thousand", 1000.0)]
        if digits:
            f += [("tenfold", 10.0), ("hundredfold", 100.0)]
        out = []
        for n, k in f:
            out += [(n, k), (n + "_inv", 1.0 / k)]
        return out

    # ---- run ----
    def run(self):
        self.step_placeholders()
        self.step_hidden()
        if self.table == "ics_sitreps":
            self.step_sitreps()
        elif self.table == "fpafod":
            self.step_fpafod()
        elif self.table == "ics_incidents":
            self.step_incidents()

    # ------------------------------------------------------------------------------------------- 1. placeholders
    def step_placeholders(self):
        n = len(self.df)
        for col in self.df.columns:
            if col in self.skip_cols:
                continue
            s = self.df[col]
            if _is_numeric_dtype(s):
                x = s.to_numpy(dtype=float, na_value=np.nan)
                self._sentinels(col, x, np.ones(n, bool))
                continue
            valid = s.notna().to_numpy()
            if not valid.any():
                continue
            st = s.astype("string")
            up = st.str.strip().str.upper()
            ph = up.isin(list(self.text_ph)).fillna(False).to_numpy(dtype=bool) if self.text_ph else np.zeros(n, bool)
            nonblank = (valid & (st.str.strip() != "").fillna(False).to_numpy(dtype=bool))
            nvalid = int(nonblank.sum())
            if ph.any():
                strong = up.isin(list(_STRONG_TEXT)).fillna(False).to_numpy(dtype=bool)
                if not self._namelike(col, st, nonblank & ~ph):
                    ph_use = ph & strong
                else:
                    ph_use = ph
                if ph_use.sum() <= 0.5 * max(nvalid, 1):
                    for pos in np.flatnonzero(ph_use):
                        tok = str(up.iat[pos])
                        self.patch(pos, col, missing(), "val:placeholder",
                                   {"kind": "text", "token": tok,
                                    "column_fraction": round(float(ph_use.sum()) / max(nvalid, 1), 4)},
                                   0.9 if tok in _STRONG_TEXT else 0.75)
            x = pd.to_numeric(st.str.strip(), errors="coerce").to_numpy(dtype=float, na_value=np.nan)
            cand = valid & ~ph
            denom = int((cand & (st.str.strip() != "").fillna(False).to_numpy(dtype=bool)).sum())
            if denom and np.isfinite(x[cand]).sum() >= 0.5 * denom:
                self._sentinels(col, x, cand)

    def _namelike(self, col, st, mask) -> bool:
        """True for name/identifier columns (by column name), where NONE/UNKNOWN/UNK/NA mean "no value"."""
        return bool(_NAMELIKE_COL.search(str(col)))

    def _longtext(self, st) -> bool:
        v = st.dropna().iloc[:5000]
        return len(v) > 0 and float(v.str.len().median()) >= _LONG_TEXT_LEN

    def _sentinels(self, col, x, cand):
        ok = cand & np.isfinite(x)
        if not ok.any():
            return
        vals = x[ok]
        uniq, cnt = np.unique(vals, return_counts=True)
        for v in self.num_ph:
            if v == 0:
                continue
            i = np.searchsorted(uniq, v)
            nv = int(cnt[i]) if i < len(uniq) and uniq[i] == v else 0
            if nv == 0:
                continue
            rows = np.flatnonzero(ok & (x == v))
            if v <= -999:
                for pos in rows:
                    self.patch(pos, col, missing(), "val:placeholder",
                               {"kind": "negative_sentinel", "value": v, "count_in_column": nv}, 0.95)
                continue
            near = (np.abs(uniq - v) <= 0.05 * abs(v)) & (uniq != v)
            other = int(cnt[near].max()) if near.any() else 0
            if nv >= 3 and len(uniq) > 20 and nv >= self.p["context_ratio"] * max(other, 1):
                for pos in rows:
                    self.patch(pos, col, missing(), "val:placeholder",
                               {"kind": "context_sentinel", "value": v, "count_in_column": nv,
                                "max_neighbour_count": other}, 0.8)
            elif abs(v) >= 9999 and re.fullmatch(r"-?9+", str(int(v))) and not _NAMELIKE_COL.search(str(col)):
                self.flag(rows, col, "possible_sentinel", f"value {v:g} occurs {nv}x")

    # ------------------------------------------------------------------------------------------- 2. hidden chars
    def step_hidden(self):
        for col in self.df.columns:
            if col in self.skip_cols:
                continue
            s = self.df[col]
            if _is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s):
                continue
            st = s.astype("string")
            try:
                m = st.str.contains(_DETECT_RE, regex=True).fillna(False).to_numpy(dtype=bool)
            except Exception:     # string storage without pyarrow: python re syntax
                m = st.str.contains(_DETECT_PY, regex=True).fillna(False).to_numpy(dtype=bool)
            longtext = bool(m.any()) and self._longtext(st)
            for pos in np.flatnonzero(m):
                old = s.iat[pos]
                new, fixes = _clean_text(str(old))
                if new == old or (longtext and fixes == ["strip"]):
                    continue    # ordinary edge whitespace in narrative text is formatting, not a hidden character
                if new == "":
                    new = missing()
                rule = "val:mojibake" if "mojibake" in fixes else "val:hidden_chars"
                self.patch(pos, col, new, rule, {"fixes": fixes}, 0.97 if rule == "val:hidden_chars" else 0.9)

    # ------------------------------------------------------------------------------------------- 3-5. sitreps
    def step_sitreps(self):
        r = TABLES["ics_sitreps"]
        df = self.df
        gcol, dcol = _find(df, r["group"]), _find(df, r["date"])
        if gcol is None or dcol is None:
            return
        n = len(df)
        date = _to_dates(df[dcol])
        gid = pd.factorize(df[gcol].astype("string"))[0]
        hcol = _find(df, r["hour"])
        hour = pd.to_numeric(df[hcol], errors="coerce").fillna(0).to_numpy() if hcol else np.zeros(n)
        pos = np.arange(n)
        dn = date.to_numpy("datetime64[ns]")
        dnum = np.where(date.isna().to_numpy(), np.iinfo(np.int64).max, dn.astype("int64"))
        order = np.lexsort((pos, hour, dnum, gid))
        okrow = (gid[order] >= 0) & ~date.isna().to_numpy()[order]
        order = order[okrow]
        gs = gid[order]
        days = dn.astype("datetime64[D]").astype("int64")[order]
        newg = np.r_[True, (gs[1:] != gs[:-1]) | ((days[1:] - days[:-1]) > self.p["break_days"])]
        self.order, self.grp = order, np.cumsum(newg)
        self.step_monotone()
        self.step_weather()

    def _seq_neighbours(self, x_by_row):
        """For the valid rows in sequence order return (rows, prev, next, grp, has_prev, has_next)."""
        v = x_by_row[self.order]
        ok = np.isfinite(v)
        rows, g, x = self.order[ok], self.grp[ok], v[ok]
        hp = np.r_[False, g[1:] == g[:-1]]
        hn = np.r_[g[1:] == g[:-1], False]
        p = np.r_[np.nan, x[:-1]]
        nx = np.r_[x[1:], np.nan]
        return rows, x, np.where(hp, p, np.nan), np.where(hn, nx, np.nan), g

    def step_monotone(self):
        r = TABLES["ics_sitreps"]
        df = self.df
        # --- area (normalised to acres through its unit column) ---
        for acol, ucol in r["area"]:
            ac = _find(df, [acol])
            if ac is None:
                continue
            uc = _find(df, [ucol]) if ucol else None
            x = self.num(ac)
            fac = np.ones(len(df))
            if uc is not None:
                u = df[uc].astype("string").str.strip().str.upper().fillna("")
                fac = np.where(u.str.contains("MILE").to_numpy(), self.acres_per_sqmi, fac)
                fac = np.where(u.str.startswith("HECT").to_numpy(), self.acres_per_ha, fac)
                fac = np.where(u.isin(["SQ KM", "KM2", "SQUARE KILOMETERS"]).to_numpy(), self.acres_per_km2, fac)
            self._monotone(ac, x * fac, fac, "area", self.area_factors(digits=True), None)
            break
        # --- percent contained ---
        for pcol, ucol in r["pct"]:
            pc = _find(df, [pcol])
            if pc is None:
                continue
            x = self.num(pc)
            if ucol and _find(df, [ucol]):
                u = df[_find(df, [ucol])].astype("string").str.strip().str.upper().fillna("")
                x = np.where(u.isin(["", "PCT", "PERCENT", "%"]).to_numpy(), x, np.nan)
            bad = np.isfinite(x) & ((x < 0) | (x > 100))
            if bad.any():
                self.flag(np.flatnonzero(bad), pc, "pct_out_of_range", "percent contained outside [0, 100]")
            x = np.where(bad, np.nan, x)
            pf = [(nm, k) for nm, k in [("tenfold", 10.0), ("tenfold_inv", 0.1), ("hundredfold", 100.0),
                                         ("hundredfold_inv", 0.01)]]
            self._monotone(pc, x, np.ones(len(df)), "pct", pf, (0.0, 100.0))
            break
        # --- cumulative cost / personnel-days ---
        for role, key in (("cost", "cost"), ("ppl_days", "ppl_days")):
            c = _find(df, r[role])
            if c is None:
                continue
            ff = self.area_factors(digits=True)
            ff = [(nm, k) for nm, k in ff if nm.startswith(("thousand", "tenfold", "hundredfold"))]
            self._monotone(c, self.num(c), np.ones(len(df)), key, ff, None)

    def _monotone(self, col, xn, native_fac, name, factors, bounds):
        """Isolated-glitch detection + repair on a non-decreasing per-incident series.

        xn: values in the reference unit (acres...), native_fac converts native -> reference unit.
        """
        tol, shrink, gr = self.p["slip_tol"], self.p["shrink_tol"][name], self.p["glitch_ratio"]
        lvl = self.p["min_level"].get(name, 0.0)
        rows, x, p, nx, g = self._seq_neighbours(xn)
        if not len(rows):
            return
        hp, hn = np.isfinite(p), np.isfinite(nx)
        both = hp & hn
        p2 = np.r_[np.nan, np.nan, x[:-2]]
        n2 = np.r_[x[2:], np.nan, np.nan]
        p2 = np.where(np.r_[False, False, g[2:] == g[:-2]], p2, np.nan)
        n2 = np.where(np.r_[g[2:] == g[:-2], False, False], n2, np.nan)
        with np.errstate(invalid="ignore"):
            in_order = both & (p <= nx * (1 + 1e-9))
            low = in_order & (x < p / gr) & (x < nx)
            high = in_order & (x > nx * gr) & (x > p)
            close = (nx <= p * self.p["max_neighbour_ratio"]) & (np.maximum(p, nx) >= lvl)
            # the neighbours must belong to a monotone run themselves, and the odd value must not recur two
            # reports away (alternating values are a real pattern, not a typo)
            run_ok = (~np.isfinite(p2) | (p2 <= p * (1 + 1e-9))) & (~np.isfinite(n2) | (n2 >= nx * (1 - 1e-9)))
            recurs = (np.abs(p2 - x) <= tol * x) | (np.abs(n2 - x) <= tol * x)
            close &= run_ok & ~recurs
            # ordinary shrinkage (not an isolated glitch, not the report after a spike)
            prev_spike = np.r_[False, high[:-1]] & np.r_[False, g[1:] == g[:-1]]
            shrinks = hp & (x < p * (1 - shrink)) & ~low & ~prev_spike & (np.maximum(p, x) >= lvl)
            if name == "pct":
                shrinks &= (p - x) >= self.p["pct_fall_points"]
        reason_shrink = {"area": "area_shrinks", "pct": "pct_falls", "cost": "cost_falls",
                         "ppl_days": "personnel_days_fall"}[name]
        lo_b = bounds[0] if bounds else -np.inf
        hi_b = bounds[1] if bounds else np.inf
        patched_rows = np.zeros(len(rows), bool)
        for i in np.flatnonzero((low | high) & close):
            pos = int(rows[i])
            xi, pi, ni = x[i], p[i], nx[i]
            # sentinel spike -> blank
            if high[i] and any(xi == v for v in self.num_ph if abs(v) >= 999):
                if self.patch(pos, col, missing(), "val:placeholder",
                              {"kind": "isolated_spike_sentinel", "prev": pi, "next": ni, "value": xi}, 0.8):
                    patched_rows[i] = True
                continue
            fits = []
            for nm, k in factors:
                y = xi * k
                if lo_b <= y <= hi_b and pi * (1 - tol) <= y <= ni * (1 + tol) and abs(k - 1) > 1e-9:
                    fits.append((nm, k, y))
            if len(fits) != 1:
                continue
            nm, k, y = fits[0]
            nat = float(self.df[col].iat[pos]) if not isinstance(self.df[col].iat[pos], str) else float(
                str(self.df[col].iat[pos]).strip())
            yn, d = _round_like(nat * k, _decimals(self.df[col].iat[pos]), k)
            new = self._format_like(col, self.df[col].iat[pos], yn, d)
            unit = not nm.startswith(("tenfold", "hundredfold"))
            rule = "val:unit_slip" if unit else "val:sequence_glitch"
            ev = {"factor": nm, "ratio": round(float(k), 6), "prev": pi, "next": ni, "kind": "sequence"}
            if self.patch(pos, col, new, rule, ev, (0.9 if unit else 0.8) * (1.0 if both[i] else 0.8)):
                patched_rows[i] = True
        # flags
        unexplained = (low | high) & ~patched_rows
        unexplained &= np.maximum(p, x) >= lvl
        self.flag(rows[unexplained], col, f"{name}_isolated_glitch",
                  [f"prev={a:g} value={b:g} next={c:g}" for a, b, c in zip(p[unexplained], x[unexplained], nx[unexplained])])
        sh = shrinks & ~patched_rows
        self.flag(rows[sh], col, reason_shrink, [f"prev={a:g} value={b:g}" for a, b in zip(p[sh], x[sh])])

    def _col_decimals(self, col) -> int:
        """Most common number of decimals written in a string column (how its numbers are formatted)."""
        if col not in self._dec:
            v = self.df[col]
            v = v[v.notna()].iloc[:5000]
            counts = pd.Series([_decimals(x) for x in v if isinstance(x, str)])
            self._dec[col] = int(counts.mode().iloc[0]) if len(counts) else 0
        return self._dec[col]

    def _format_like(self, col, old, y, d):
        """Format a corrected number the way the column writes numbers (string columns) or as a number."""
        if isinstance(old, (int, np.integer)) and float(y).is_integer():
            return int(y)
        if isinstance(old, (float, np.floating)):
            return float(y)
        return f"{y:.{max(self._col_decimals(col), d)}f}"

    # ---- weather ----
    def step_weather(self):
        r = TABLES["ics_sitreps"]
        df = self.df
        tc, rc = _find(df, r["temp"]), _find(df, r["rh"])
        wc, gc = _find(df, r["wind"]), _find(df, r["gust"])
        tol, win = self.p["slip_tol"], self.p["rh_window_points"]
        k = lambda f: (f - 32.0) / 1.8 + 273.15
        lat = _find(df, r["lat"]) ; lon = _find(df, r["lon"]); dcol = _find(df, r["date"])
        if tc is not None:
            t = self.num(tc)
            lo, hi = self.p["temp_f_range"]
            bad = np.isfinite(t) & ((t < lo) | (t > hi))
            self.flag(np.flatnonzero(bad), tc, "temp_out_of_range", f"outside [{lo:g}, {hi:g}] F")
            rows, x, p, nx, g = self._seq_neighbours(t)
            ref_lo, ref_hi = np.fmin(p, nx), np.fmax(p, nx)
            has = np.isfinite(p) & np.isfinite(nx) & (np.abs(p - nx) <= 20.0)   # neighbours must agree (F)
            wlo, whi = k(ref_lo) * (1 - tol), k(ref_hi) * (1 + tol)
            with np.errstate(invalid="ignore"):
                orig_fits = (k(x) >= wlo) & (k(x) <= whi)
                cand = {"c_reported_as_f": x * 1.8 + 32.0}
                fit = {nm: has & ~orig_fits & (y >= lo) & (y <= hi) & (k(y) >= wlo) & (k(y) <= whi)
                       for nm, y in cand.items()}
            for nm, y in cand.items():
                other = [fit[o] for o in fit if o != nm]
                sel = fit[nm] & ~np.any(other, axis=0)
                for i in np.flatnonzero(sel):
                    pos = int(rows[i])
                    new = self._format_like(tc, df[tc].iat[pos], round(float(y[i])), 0)
                    self.patch(pos, tc, new, "val:weather_unit_slip",
                               {"kind": nm, "prev": p[i], "next": nx[i], "tol_kelvin_pct": tol * 100}, 0.75)
            if self.grid is not None and lat and lon and dcol:
                self._grid_check(tc, rc, lat, lon, dcol)
        if rc is not None:
            rh = self.num(rc)
            lo, hi = self.p["rh_range"]
            bad = np.isfinite(rh) & ((rh < lo) | (rh > hi))
            self.flag(np.flatnonzero(bad), rc, "rh_out_of_range", f"outside [{lo:g}, {hi:g}] percent")
            rows, x, p, nx, g = self._seq_neighbours(np.where(bad, np.nan, rh))
            has = np.isfinite(p) & np.isfinite(nx)
            wl, wh = np.fmin(p, nx) - win, np.fmax(p, nx) + win
            with np.errstate(invalid="ignore"):
                sel = has & (x > 0) & (x <= 1.0) & (np.fmin(p, nx) >= 5) & ((x * 100 >= wl) & (x * 100 <= wh))
            for i in np.flatnonzero(sel):
                pos = int(rows[i])
                new = self._format_like(rc, df[rc].iat[pos], round(float(x[i]) * 100, 4), 0)
                self.patch(pos, rc, new, "val:weather_unit_slip",
                           {"kind": "rh_fraction_as_percent", "prev": p[i], "next": nx[i], "window_points": win}, 0.7)
        if wc is not None:
            w = self.num(wc)
            neg = np.isfinite(w) & (w < 0)
            self.flag(np.flatnonzero(neg), wc, "wind_negative", "")
            big = np.isfinite(w) & (w > self.p["wind_max_mph"])
            self.flag(np.flatnonzero(big), wc, "wind_implausible", f"> {self.p['wind_max_mph']:g} mph")
            if gc is not None:
                gu = self.num(gc)
                m = np.isfinite(w) & np.isfinite(gu) & (gu < w)
                self.flag(np.flatnonzero(m), gc, "gust_below_wind", "gust lower than sustained wind")

    def _grid_check(self, tc, rc, lat, lon, dcol):
        df, tol, win = self.df, self.p["slip_tol"], self.p["rh_window_points"]
        k = lambda f: (f - 32.0) / 1.8 + 273.15
        la, lo = self.num(lat), self.num(lon)
        if np.isfinite(lo).any() and self.cfg.get("longitude_sign_convention") == "west_negative":
            lo = np.where(lo > 0, -lo, lo)
        dts = _to_dates(df[dcol])
        t = self.num(tc)
        rh = self.num(rc) if rc is not None else np.full(len(df), np.nan)
        rows = np.flatnonzero((np.isfinite(t) | np.isfinite(rh)) & np.isfinite(la) & np.isfinite(lo) & dts.notna().to_numpy())
        for pos in rows:
            try:
                gr = self.grid(float(la[pos]), float(lo[pos]), dts.iat[pos].date()) or {}
            except Exception:
                continue
            gt, gh = gr.get("temp_f"), gr.get("rh")
            if np.isfinite(t[pos]) and gt is not None and np.isfinite(gt):
                x, ok = t[pos], abs(k(t[pos]) - k(gt)) <= tol * k(gt)
                if not ok:
                    for nm, y in (("c_reported_as_f", x * 1.8 + 32.0),):
                        if abs(k(y) - k(gt)) <= tol * k(gt):
                            new = self._format_like(tc, df[tc].iat[pos], round(float(y)), 0)
                            if self.patch(pos, tc, new, "val:weather_unit_slip",
                                          {"kind": nm, "grid_temp_f": float(gt), "source": "grid"}, 0.8):
                                break
                    else:
                        if abs(k(x) - k(gt)) > 2 * tol * k(gt):
                            self.flag(pos, tc, "temp_vs_grid_unexplained", f"grid {gt:.1f} F")
            if rc is not None and np.isfinite(rh[pos]) and gh is not None and np.isfinite(gh):
                x = rh[pos]
                if abs(x - gh) > win and 0 < x <= 1.0 and abs(x * 100 - gh) <= win:
                    new = self._format_like(rc, df[rc].iat[pos], round(float(x) * 100, 4), 0)
                    self.patch(pos, rc, new, "val:weather_unit_slip",
                               {"kind": "rh_fraction_as_percent", "grid_rh": float(gh), "source": "grid"}, 0.75)

    # ------------------------------------------------------------------------------------------- FPA FOD
    def _class_of(self, y):
        """NWCG size class letter of acreage ``y`` (A <= 0.25 < B < 10 <= C < 100 <= D < 300 <= E < 1000 <= F < 5000 <= G)."""
        y = np.asarray(y, dtype=float)
        out = np.full(y.shape, "", dtype=object)
        prev = None
        for i, (c, b) in enumerate(self.p["size_classes"]):
            if i == 0:
                sel = y <= b
            elif b is None:
                sel = y >= prev
            elif i == 1:
                sel = (y > prev) & (y < b)
            else:
                sel = (y >= prev) & (y < b)
            out[sel & np.isfinite(y)] = c
            prev = b
        return out

    def step_fpafod(self):
        self._size_checks("fpafod", has_class=True)
        r = TABLES["fpafod"]
        dc, cc = _find(self.df, r["disc"]), _find(self.df, r["cont"])
        if dc and cc:
            d, c = _to_dates(self.df[dc]), _to_dates(self.df[cc])
            bad = (c < d).fillna(False).to_numpy(dtype=bool)
            self.flag(np.flatnonzero(bad), cc, "cont_before_discovery", "")

    def step_incidents(self):
        self._size_checks("ics_incidents", has_class=False)
        r = TABLES["ics_incidents"]
        pk, sm = _find(self.df, r["peak"]), _find(self.df, r["sum"])
        if pk and sm:
            a, b = self.num(pk), self.num(sm)
            m = np.isfinite(a) & np.isfinite(b) & (a > b)
            self.flag(np.flatnonzero(m), pk, "peak_exceeds_sum", "peak personnel above total personnel sum")
        dc, cc = _find(self.df, r["disc"]), _find(self.df, r["cont"])
        if dc and cc:
            d, c = _to_dates(self.df[dc]), _to_dates(self.df[cc])
            self.flag(np.flatnonzero((c < d).fillna(False).to_numpy(dtype=bool)), cc, "report_before_discovery", "")

    def _size_checks(self, table, has_class):
        r = TABLES[table]
        df = self.df
        sc = _find(df, r["size"])
        if sc is None:
            return
        x = self.num(sc)
        neg = np.isfinite(x) & (x <= 0) if table == "fpafod" else np.isfinite(x) & (x < 0)
        self.flag(np.flatnonzero(neg), sc, "nonpositive_size", "")
        huge = np.isfinite(x) & (x > self.p["fire_size_max_acres"])
        self.flag(np.flatnonzero(huge), sc, "implausible_size", f"> {self.p['fire_size_max_acres']:g} acres")
        refs = [self.num(c) for c in [_find(df, [n]) for n in r["refs"]] if c]
        clsc = _find(df, r["size_class"]) if has_class and "size_class" in r else None
        cls = (df[clsc].astype("string").str.strip().str.upper().fillna("").to_numpy(dtype=object)
               if clsc else None)
        facs = self.area_factors(digits=False)
        tol = self.p["cross_tol"]
        pos_ok = np.isfinite(x) & (x > 0)
        nk = len(facs)
        hits = np.zeros((len(x), nk), bool)
        near = np.zeros(len(x), bool)
        nref = np.zeros(len(x), int)
        for ref in refs:
            ok = pos_ok & np.isfinite(ref) & (ref > 0)
            q = np.where(ok, x / np.where(ok, ref, 1), np.nan)
            nref += ok
            with np.errstate(invalid="ignore"):
                near |= ok & (q >= 0.75) & (q <= 1.25)
                for j, (_, k) in enumerate(facs):
                    hits[:, j] |= ok & (np.abs(q * k - 1) <= tol)   # x * k lands on the other source
        cand = np.zeros(len(x), bool)
        yfix = np.full(len(x), np.nan)
        kfix = np.zeros(len(x))
        nm_fix = np.empty(len(x), dtype=object)
        support = np.zeros(len(x), int)
        # a single other source is not enough where there is no size class: a second, looser source must agree
        # (within 1.5x) with the corrected value, otherwise the cell is only flagged
        corro = [self.num(c) for c in [_find(df, [n]) for n in r.get("corroborate", [])] if c]
        # (a) independent-source evidence
        sel = pos_ok & ~near & (hits.sum(1) == 1)
        for j, (nm, k) in enumerate(facs):
            m = sel & hits[:, j]
            y = x * k
            if cls is not None:
                have = np.isin(cls, [c for c, _ in self.p["size_classes"]])
                m &= ~have | (self._class_of(y) == cls)
            if cls is None and "corroborate" in r:
                agree = np.zeros(len(x), bool)
                for c in corro:
                    with np.errstate(invalid="ignore", divide="ignore"):
                        agree |= np.isfinite(c) & (c > 0) & (np.maximum(y / c, c / y) <= 1.5)
                weak = m & ~agree
                self.flag(np.flatnonzero(weak), sc, "unit_slip_candidate",
                          [f"{nm} x{k:.5g} would match the other source; no corroboration" for _ in range(int(weak.sum()))])
                m &= agree
            cand |= m
            yfix = np.where(m, y, yfix); kfix = np.where(m, k, kfix); nm_fix[m] = nm
            support = np.where(m, 1 + (have.astype(int) if cls is not None else 0) + (1 if (cls is None and "corroborate" in r) else 0), support)
        # (b) class-only evidence (FPA FOD): size is outside its own class and exactly one factor repairs it
        if cls is not None:
            have = np.isin(cls, [c for c, _ in self.p["size_classes"]])
            mism = pos_ok & have & (self._class_of(x) != cls)
            rest = mism & ~cand & ~near
            fixes = [(nm, k, self._class_of(x * k) == cls) for nm, k in facs]
            cnt = sum(f.astype(int) for _, _, f in fixes)
            only = rest & (cnt == 1)
            for nm, k, f in fixes:
                m = only & f
                cand |= m
                yfix = np.where(m, x * k, yfix); kfix = np.where(m, k, kfix); nm_fix[m] = nm
                support = np.where(m, 1, support)
            left = mism & ~cand
            self.flag(np.flatnonzero(left), sc, "size_class_mismatch",
                      [f"size {a:g} vs class {b}" for a, b in zip(x[left], cls[left])])
        sel_rows = np.flatnonzero(cand)
        for pos in sel_rows:
            old = self.df[sc].iat[int(pos)]
            yn, d = _round_like(float(yfix[pos]), _decimals(old), float(kfix[pos]))
            new = self._format_like(sc, old, yn, d)
            src = "class" if nref[pos] == 0 else "reference"
            if cls is not None and nref[pos] and support[pos] > 1:
                src += " + class"
            ev = {"factor": nm_fix[pos], "ratio": round(float(kfix[pos]), 6), "sources": src, "tol": tol}
            conf = 0.95 if support[pos] > 1 else (0.8 if nref[pos] else 0.75)
            self.patch(pos, sc, new, "val:unit_slip", ev, conf)


def clean_values(df: pd.DataFrame, table: str, cfg: dict, id_col: str = "rid",
                 grid: Callable | None = None) -> tuple[list[Patch], pd.DataFrame]:
    """Detect and fix bad values. Returns ``(patches, flags)``; see the module docstring for the rules.

    ``table`` is one of ``'ics_sitreps'``, ``'fpafod'``, ``'ics_incidents'``, ``'generic'``.
    ``grid`` (optional) is ``grid(lat, lon, date) -> {"temp_f": ..., "rh": ...}`` for the gridded-weather check.
    The input frame is never modified.
    """
    ctx = _Ctx(df, table, cfg, id_col, grid)
    ctx.run()
    return ctx.patches, ctx.flags_df()

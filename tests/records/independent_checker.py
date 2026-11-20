#!/usr/bin/env python3
"""Independent checker for record-level patch files (FPA FOD data cleaning).

Standalone: stdlib + numpy + pandas + sqlite3 (+ pyshp/shapely for the county
checks).  It knows only the patch file format and the input GeoPackage; it never
imports or reads the tool that produced the patches.

Usage:
  python independent_checker.py --patches P.jsonl --gpkg FPA_FOD.gpkg \
      [--years 2008,2009] [--full] [--counties cb_2020_us_county_500k.zip] \
      [--report report.json]

Exit code 0 only if checks 1,2,3,5,6 have zero violations.
"""
import argparse
import collections
import datetime as dt
import io
import json
import math
import os
import re
import sqlite3
import sys
import unicodedata
import zipfile

import numpy as np
import pandas as pd

KNOWN_PREFIXES = ("val:", "loc:", "time:", "dup:")
KNOWN_RULES = {
    "val:placeholder", "val:hidden_chars", "val:mojibake", "val:unit_slip",
    "val:sequence_glitch", "val:weather_unit_slip",
    "loc:sign_flip_lon", "loc:sign_flip_lat", "loc:sign_flip_both",
    "loc:swap_axes", "loc:swap_axes_neg", "loc:dm_dd", "loc:dm_swap",
    "time:day_month", "time:tz_shift", "dup:fs_link",
}
COSMETIC_RULES = {"val:hidden_chars", "val:mojibake"}
SEVEN_KEYS = ("record_id", "field", "old", "new", "rule", "evidence", "confidence")
HARD_CHECKS = ("1_schema", "2_strict_old", "3_cells_ids", "5_alteration_budget",
               "6_reversibility")

NEEDED_COLS = ["FOD_ID", "FIRE_YEAR", "LATITUDE", "LONGITUDE", "DISCOVERY_DATE",
               "SOURCE_SYSTEM", "FIPS_CODE", "STATE"]

STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
    "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15",
    "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
    "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
    "WV": "54", "WI": "55", "WY": "56", "AS": "60", "GU": "66", "MP": "69",
    "PR": "72", "VI": "78",
}

PLACEHOLDER_TOKENS = {
    "N/A", "NA", "N.A.", "NULL", "NONE", "UNKNOWN", "UNK", "?", "??", "???", "-", "--",
    "---", ".", "TBD", "TBA", "NAN", "NOT AVAILABLE", "NOT APPLICABLE", "MISSING",
    "UNNAMED", "NO NAME", "NONAME", "BLANK", "#N/A", "NIL", "UNSPECIFIED",
    "NOT SPECIFIED", "UNDEFINED", "NOT REPORTED", "NO DATA",
}
PLACEHOLDER_NUMS = {9999.0, 99999.0, 999999.0}

FACTORS = [2.47105, 1 / 2.47105, 247.105, 640.0, 1000.0, 1 / 1000.0, 10.0, 100.0, 0.1, 0.01]
FACTOR_TOL = 0.03


# --------------------------------------------------------------------------- utils
class Check:
    """Counts violations and keeps up to 5 examples per sub-type."""

    def __init__(self, name):
        self.name = name
        self.counts = collections.Counter()
        self.examples = collections.defaultdict(list)
        self.info = {}

    def add(self, sub, patch=None, detail=None, n=1):
        self.counts[sub] += n
        if len(self.examples[sub]) < 5:
            ex = {}
            if patch is not None:
                ex["patch"] = jsonable(patch)
            if detail is not None:
                ex["detail"] = jsonable(detail)
            self.examples[sub].append(ex)

    @property
    def total(self):
        return int(sum(self.counts.values()))

    def to_json(self):
        return {
            "violations": self.total,
            "by_type": dict(self.counts),
            "examples": {k: v for k, v in self.examples.items()},
            "info": jsonable(self.info),
        }


def jsonable(o):
    try:
        json.dumps(o)
        return o
    except TypeError:
        if isinstance(o, dict):
            return {str(k): jsonable(v) for k, v in o.items()}
        if isinstance(o, (list, tuple, set)):
            return [jsonable(v) for v in o]
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        return str(o)


def is_missing(x):
    return isinstance(x, dict) and x.get("__missing__") is True and len(x) == 1


def to_cell(x):
    """Cell-space string of a patch old/new value."""
    if is_missing(x):
        return ""
    if x is None:
        return "\x00None"  # cannot equal any real cell
    if isinstance(x, str):
        return x
    if isinstance(x, (dict, list)):
        return "\x00" + json.dumps(x, sort_keys=True)
    return str(x)


def parse_float(s):
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


_DT = re.compile(
    r"^\s*(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?\s*"
    r"(Z|[+-]\d{2}:?\d{2})?\s*$")


def parse_date(s):
    if not isinstance(s, str):
        return None
    m = _DT.match(s)
    if m:
        try:
            return dt.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                               int(m.group(4) or 0), int(m.group(5) or 0), int(m.group(6) or 0))
        except ValueError:
            return None
    for fmt in ("%m/%d/%Y", "%m/%d/%Y %H:%M", "%Y%m%d", "%d-%b-%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def _removable(ch):
    if ch.isspace():
        return True
    return unicodedata.category(ch)[0] in ("Z", "C") or ch in " ​‌‍⁠﻿­�"


def strip_hidden(s):
    return "".join(ch for ch in s if not _removable(ch))


def repair_mojibake(s):
    """cp1252/latin-1 -> utf-8 round trip repair; returns s unchanged if impossible."""
    try:
        raw = bytearray()
        for ch in s:
            try:
                raw += ch.encode("cp1252")
            except UnicodeEncodeError:
                if ord(ch) < 256:
                    raw.append(ord(ch))
                else:
                    return s
        return bytes(raw).decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


# --------------------------------------------------------------------------- loading
def read_patches(path):
    header, rows, bad = None, [], []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if not line.strip():
                bad.append((i + 1, "blank line"))
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                bad.append((i + 1, "invalid json: %s" % e))
                continue
            if i == 0:
                header = obj
            else:
                rows.append((i + 1, obj))
    return header, rows, bad


def load_table(gpkg, cols, ids=None, years=None):
    """DataFrame (object/str, index=record_id) of selected columns.

    Values are str(sqlite value), NULL -> ''.  Rows selected: FOD_ID in ids OR
    FIRE_YEAR in years (all rows if both None).  Never reads Shape."""
    con = sqlite3.connect("file:%s?mode=ro" % gpkg, uri=True)
    try:
        avail = [r[1] for r in con.execute("PRAGMA table_info(Fires)")]
        cols = [c for c in dict.fromkeys(cols) if c in avail and c != "Shape"]
        sel = ", ".join('f."%s"' % c for c in cols)
        where, params = [], []
        if ids is not None:
            con.execute("CREATE TEMP TABLE ids(i INTEGER PRIMARY KEY)")
            con.executemany("INSERT OR IGNORE INTO ids VALUES (?)", ((int(i),) for i in ids))
            where.append("f.FOD_ID IN (SELECT i FROM ids)")
        if years is not None:
            where.append("f.FIRE_YEAR IN (%s)" % ",".join("?" * len(years)))
            params += list(years)
        sql = "SELECT %s FROM Fires f" % sel
        if where:
            sql += " WHERE " + " OR ".join(where)
        cur = con.execute(sql, params)
        data = [[] for _ in cols]
        while True:
            chunk = cur.fetchmany(200000)
            if not chunk:
                break
            for j, colvals in enumerate(zip(*chunk)):
                data[j].extend("" if v is None else str(v) for v in colvals)
        df = pd.DataFrame({c: pd.Series(d, dtype=object) for c, d in zip(cols, data)})
        df.index = pd.Index(["fod:" + s for s in df["FOD_ID"]], dtype=object)
        return df, avail
    finally:
        con.close()


def count_rows(gpkg, years):
    con = sqlite3.connect("file:%s?mode=ro" % gpkg, uri=True)
    try:
        if years:
            return con.execute("SELECT COUNT(*) FROM Fires WHERE FIRE_YEAR IN (%s)" %
                               ",".join("?" * len(years)), list(years)).fetchone()[0]
        return con.execute("SELECT COUNT(*) FROM Fires").fetchone()[0]
    finally:
        con.close()


def load_counties(zpath, needed):
    """needed: set of (statefp, countyfp) -> {key: shapely geometry}"""
    import shapefile  # pyshp
    from shapely.geometry import shape
    out = {}
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()

        def get(ext):
            return io.BytesIO(z.read([n for n in names if n.lower().endswith(ext)][0]))
        r = shapefile.Reader(shp=get(".shp"), shx=get(".shx"), dbf=get(".dbf"))
        fields = [f[0] for f in r.fields[1:]]
        i_s, i_c = fields.index("STATEFP"), fields.index("COUNTYFP")
        for sr in r.iterShapeRecords():
            key = (str(sr.record[i_s]), str(sr.record[i_c]))
            if key in needed:
                out[key] = shape(sr.shape.__geo_interface__)
    return out


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patches", required=True)
    ap.add_argument("--gpkg", required=True)
    ap.add_argument("--years", default=None, help="comma list of FIRE_YEARs to restrict to")
    ap.add_argument("--full", action="store_true",
                    help="load the whole (year-filtered) table for checks 5/6 instead of only patched rows")
    ap.add_argument("--counties", default=None, help="census county zip")
    ap.add_argument("--report", default=None)
    args = ap.parse_args()
    years = [int(y) for y in args.years.split(",")] if args.years else None
    if args.counties is None:
        cand = "/home/user/wildfire 3 (1)/firewitness_raw/census/cb_2020_us_county_500k.zip"
        if os.path.exists(cand):
            args.counties = cand

    header, raw, bad_lines = read_patches(args.patches)
    names = ("1_schema", "2_strict_old", "3_cells_ids", "4_value_sanity",
             "5_alteration_budget", "6_reversibility", "7_confidence")
    checks = {k: Check(k) for k in names}
    c1, c2, c3, c4, c5, c6, c7 = (checks[k] for k in names)

    # ---- check 1: header + per-patch schema
    if not (isinstance(header, dict) and header.get("_header") is True):
        c1.add("header_missing_or_malformed", detail=str(header)[:200])
        header = header if isinstance(header, dict) else {}
    else:
        n_hdr = header.get("n")
        if not isinstance(n_hdr, int) or isinstance(n_hdr, bool):
            c1.add("header_n_not_int", detail=n_hdr)
        elif n_hdr != len(raw):
            c1.add("header_n_mismatch", detail={"header_n": n_hdr, "patch_lines": len(raw)})
        if not isinstance(header.get("tool"), str):
            c1.add("header_tool_not_str")
        if not (header.get("input_sha256") is None or isinstance(header.get("input_sha256"), str)):
            c1.add("header_sha_bad_type")
        if not isinstance(header.get("chain"), str):
            c1.add("header_chain_not_str")
        if not isinstance(header.get("meta"), dict):
            c1.add("header_meta_not_dict")
    for ln, why in bad_lines:
        c1.add("bad_line", detail={"line": ln, "why": why})

    patches = []
    for ln, p in raw:
        if not isinstance(p, dict):
            c1.add("patch_not_object", detail={"line": ln})
            continue
        ok = True
        missing_keys = [k for k in SEVEN_KEYS if k not in p]
        if missing_keys:
            c1.add("missing_keys", p, missing_keys)
            ok = False
        extra = [k for k in p if k not in SEVEN_KEYS]
        if extra:
            c1.add("unexpected_keys", p, extra)
        rid = p.get("record_id")
        if not isinstance(rid, str) or not rid:
            c1.add("record_id_empty_or_not_str", p)
            ok = False
        fld = p.get("field")
        if not isinstance(fld, str) or not fld:
            c1.add("field_empty_or_not_str", p)
            ok = False
        rule = p.get("rule")
        if not isinstance(rule, str) or not rule:
            c1.add("rule_empty_or_not_str", p)
            ok = False
        elif not rule.startswith(KNOWN_PREFIXES):
            c1.add("rule_unknown_prefix", p)
        conf = p.get("confidence")
        if (isinstance(conf, bool) or not isinstance(conf, (int, float)) or
                (isinstance(conf, float) and math.isnan(conf)) or not (0.0 <= conf <= 1.0)):
            c1.add("confidence_bad", p)
        ev = p.get("evidence", None)
        if ev is None or (isinstance(ev, (dict, list, str)) and len(ev) == 0):
            c1.add("evidence_null_or_empty", p)
        for k in ("old", "new"):
            if k in p:
                v = p[k]
                if v is None or isinstance(v, (list, bool)) or (isinstance(v, dict) and not is_missing(v)):
                    c1.add("old_new_bad_type", p, {k: v})
                    ok = False
        if ok:
            patches.append(p)

    # ---- load input rows
    all_ids = set()
    for p in patches:
        rid = p["record_id"]
        if rid.startswith("fod:") and rid[4:].isdigit():
            all_ids.add(int(rid[4:]))
        nw = p["new"]
        if p["field"] == "dup_of" and isinstance(nw, str) and nw.startswith("fod:") and nw[4:].isdigit():
            all_ids.add(int(nw[4:]))
    touched_fields = sorted({p["field"] for p in patches})
    if args.full:
        table, avail = load_table(args.gpkg, NEEDED_COLS + touched_fields,
                                  ids=all_ids if years else None, years=years)
    else:
        table, avail = load_table(args.gpkg, NEEDED_COLS + touched_fields, ids=all_ids)
    avail_set = set(avail)
    n_table = len(table)
    pos_of = {rid: i for i, rid in enumerate(table.index)}
    if len(pos_of) != n_table:
        c3.add("input_record_id_not_unique", detail={"rows": n_table, "unique": len(pos_of)})
    colarr = {c: table[c].to_numpy(dtype=object) for c in table.columns}
    year_arr = colarr.get("FIRE_YEAR")

    n_all_patches = len(patches)
    if years is not None:  # unknown record ids are kept so they get reported
        yset = {str(y) for y in years}
        patches = [p for p in patches
                   if pos_of.get(p["record_id"]) is None or year_arr[pos_of[p["record_id"]]] in yset]

    # ---- checks 2 & 3
    dup_marked = {p["record_id"] for p in patches if p["field"] == "dup_of"}
    seen_cells = collections.Counter()
    for p in patches:
        rid, fld = p["record_id"], p["field"]
        seen_cells[(rid, fld)] += 1
        if seen_cells[(rid, fld)] >= 2:
            c3.add("duplicate_cell_patch", p)
        i = pos_of.get(rid)
        if i is None:
            c3.add("unknown_record_id", p)
            continue
        cell = colarr[fld][i] if fld in colarr else ""
        old, new = p["old"], p["new"]
        if fld != "dup_of" and (fld not in avail_set or fld == "Shape"):
            c3.add("unknown_field", p)
        if fld == "dup_of":
            if not is_missing(old):
                c2.add("dup_old_not_missing", p)
        elif to_cell(old) != cell:
            c2.add("old_differs_from_input", p, {"input_cell": cell})
        elif not (isinstance(old, str) or is_missing(old)):
            c2.add("old_not_string_but_equal", p, {"input_cell": cell})
        if to_cell(old) == to_cell(new):
            c3.add("no_op", p)
        if p["rule"].startswith("dup:") != (fld == "dup_of"):
            c4.add("rule_field_mismatch", p)
        if fld == "dup_of":
            if not isinstance(new, str) or new not in pos_of:
                c3.add("dup_target_unknown", p)
            elif new == rid:
                c3.add("dup_target_is_self", p)
            elif new in dup_marked:
                c3.add("dup_target_itself_marked_duplicate", p)

    # ---- checks 5 & 6: vectorised apply, then inverse
    per_field = collections.defaultdict(lambda: ([], [], []))
    for p in patches:
        i = pos_of.get(p["record_id"])
        if i is None:
            continue
        a, b, c = per_field[p["field"]]
        a.append(i)
        b.append(to_cell(p["new"]))
        c.append(to_cell(p["old"]))
    patched_cols = {}
    patched_cells, altered_cells = set(), set()
    for f, (pos, news, olds) in per_field.items():
        base = colarr[f] if f in colarr else np.full(n_table, "", dtype=object)
        pos = np.asarray(pos, dtype=np.int64)
        news_a = np.empty(len(news), dtype=object)
        news_a[:] = news
        olds_a = np.empty(len(olds), dtype=object)
        olds_a[:] = olds
        patched_cells.update((int(i), f) for i in pos)
        # forward: patch order, last patch per cell wins
        keep = ~pd.Series(pos).duplicated(keep="last").to_numpy()
        col = base.copy()
        col[pos[keep]] = news_a[keep]
        patched_cols[f] = col
        altered_cells.update((int(i), f) for i in np.nonzero(col != base)[0])
        # inverse: reverse order, set to old, last in reversed order wins
        pr, orr = pos[::-1], olds_a[::-1]
        keep_i = ~pd.Series(pr).duplicated(keep="last").to_numpy()
        col2 = col.copy()
        col2[pr[keep_i]] = orr[keep_i]
        bad = np.nonzero(col2 != base)[0]
        if len(bad):
            c6.add("cell_not_restored", None,
                   {"record_id": table.index[bad[0]], "field": f, "input": base[bad[0]],
                    "after_inverse": col2[bad[0]]}, n=len(bad))
            for j in bad[1:5]:
                c6.examples["cell_not_restored"].append(
                    {"detail": {"record_id": table.index[j], "field": f, "input": base[j],
                                "after_inverse": col2[j]}})
            del c6.examples["cell_not_restored"][5:]
    for (i, f) in sorted(patched_cells - altered_cells):
        c5.add("patched_cell_not_altered", None,
               {"record_id": table.index[i], "field": f, "input_cell": colarr[f][i] if f in colarr else ""})
    for (i, f) in sorted(altered_cells - patched_cells):
        c5.add("altered_cell_without_patch", None, {"record_id": table.index[i], "field": f})
    c5.info.update({
        "patched_cells": len(patched_cells), "altered_cells": len(altered_cells),
        "mode": "full (year-filtered table)" if args.full else "subset (rows named by patches + dup targets)",
        "rows_loaded": n_table,
        "note": ("apply is this checker's own last-write-wins application; a violation means a patch is "
                 "a no-op, repeats a cell or reverts another patch"),
    })
    c6.info["cells_checked"] = len(patched_cells)

    n_universe = count_rows(args.gpkg, years)
    rec_value, rec_cos = set(), set()
    for p in patches:
        (rec_cos if p["rule"] in COSMETIC_RULES else rec_value).add(p["record_id"])
    c5.info["shares"] = {
        "universe_rows": n_universe,
        "records_value_level": len(rec_value), "share_value_level": len(rec_value) / max(n_universe, 1),
        "records_cosmetic": len(rec_cos), "share_cosmetic": len(rec_cos) / max(n_universe, 1),
        "records_any": len(rec_value | rec_cos), "share_any": len(rec_value | rec_cos) / max(n_universe, 1),
        "records_both": len(rec_value & rec_cos),
    }

    # ---- check 4: value sanity
    loc_by_record = collections.defaultdict(list)
    dup_rows = []
    placeholder_tokens_seen = collections.Counter()
    for p in patches:
        rule, fld, old, new, rid = p["rule"], p["field"], p["old"], p["new"], p["record_id"]
        if rid not in pos_of:
            continue
        if rule.startswith(KNOWN_PREFIXES) and rule not in KNOWN_RULES:
            c4.add("unknown_rule_name", p)
        news = to_cell(new)
        if rule == "val:placeholder":
            ok_tok = False
            if isinstance(old, (str, int, float)) and not is_missing(old):
                tok = str(old).strip().upper()
                placeholder_tokens_seen[str(old)] += 1
                if tok in PLACEHOLDER_TOKENS:
                    ok_tok = True
                else:
                    v = parse_float(tok)
                    ok_tok = v is not None and (v <= -99 or v in PLACEHOLDER_NUMS)
            if not ok_tok:
                c4.add("placeholder_old_not_sentinel", p)
            if not is_missing(new):
                c4.add("placeholder_new_not_missing", p)
        elif rule in COSMETIC_RULES:
            if not isinstance(old, str):
                c4.add("cosmetic_old_not_string", p)
                continue
            n_old, n_new = strip_hidden(old), strip_hidden(news)
            good = n_old == n_new
            if not good and rule == "val:mojibake":
                good = strip_hidden(repair_mojibake(old)) == n_new
            if not good:
                c4.add("%s_changes_content" % rule.split(":")[1], p, {"old_norm": n_old, "new_norm": n_new})
        elif rule in ("val:unit_slip", "val:sequence_glitch", "val:weather_unit_slip"):
            ov, nv = parse_float(to_cell(old)), parse_float(news)
            if ov is None or nv is None:
                c4.add("non_numeric", p)
            elif ov == 0:
                c4.add("ratio_not_a_known_factor", p, {"reason": "old is zero"})
            else:
                r = nv / ov
                if not any(abs(r / f - 1.0) <= FACTOR_TOL for f in FACTORS):
                    c4.add("ratio_not_a_known_factor", p, {"ratio": r})
        elif rule.startswith("loc:"):
            loc_by_record[rid].append(p)
        elif rule.startswith("time:"):
            if parse_date(news) is None:
                c4.add("new_date_unparseable", p)
        elif rule == "dup:fs_link":
            if fld == "dup_of" and isinstance(new, str) and new in pos_of and new != rid:
                dup_rows.append((p, pos_of[rid], pos_of[new]))
    c4.info["placeholder_old_tokens"] = dict(placeholder_tokens_seen.most_common(30))

    c4.info["loc_records"] = len(loc_by_record)
    if loc_by_record:
        pl = patched_cols.get("LATITUDE", colarr["LATITUDE"])
        pg = patched_cols.get("LONGITUDE", colarr["LONGITUDE"])
        need, recs, skipped = set(), [], 0
        for rid, plist in loc_by_record.items():
            i, first = pos_of[rid], plist[0]
            for q in plist:
                if q["field"] not in ("LATITUDE", "LONGITUDE"):
                    c4.add("loc_field_not_coordinate", q)
            plat, plon = parse_float(pl[i]), parse_float(pg[i])
            if plat is None or plon is None:
                c4.add("loc_new_coords_unparseable", first, {"lat": pl[i], "lon": pg[i]})
                continue
            if not (17 <= plat <= 72):
                c4.add("loc_lat_out_of_bounds", first, {"lat": plat, "lon": plon})
            if not (-180 <= plon <= -64):
                c4.add("loc_lon_out_of_bounds", first, {"lat": plat, "lon": plon})
            st = colarr["STATE"][i].strip().upper()
            fp = colarr["FIPS_CODE"][i].strip()
            if st in STATE_FIPS and fp.isdigit():
                key = (STATE_FIPS[st], fp.zfill(3))
                need.add(key)
                recs.append((rid, plat, plon, key, first))
            else:
                skipped += 1
        c4.info["loc_no_state_or_fips_skipped"] = skipped
        if recs:
            if not args.counties or not os.path.exists(args.counties):
                c4.add("county_polygons_unavailable", None, args.counties)
            else:
                import shapely
                from shapely import affinity
                from shapely.geometry import Point
                geoms = load_counties(args.counties, need)
                by_key = collections.defaultdict(list)
                for r in recs:
                    by_key[r[3]].append(r)
                n_checked = n_no_poly = 0
                for key, rs in by_key.items():
                    g = geoms.get(key)
                    if g is None:
                        n_no_poly += len(rs)
                        continue
                    inside = shapely.contains_xy(g, np.array([r[2] for r in rs]), np.array([r[1] for r in rs]))
                    for r, ins in zip(rs, inside):
                        n_checked += 1
                        if ins:
                            continue
                        pt = Point(r[2], r[1])
                        d_deg = g.distance(pt)
                        if d_deg <= 0.12:  # near the border: local equirectangular distance
                            cs = math.cos(math.radians(r[1]))
                            dist_km = (affinity.scale(g, xfact=cs, yfact=1.0, origin=(0, 0))
                                       .distance(affinity.scale(pt, xfact=cs, yfact=1.0, origin=(0, 0))) * 111.195)
                            if dist_km <= 3.0:
                                continue
                        else:
                            dist_km = d_deg * 111.195 * math.cos(math.radians(r[1]))
                        i = pos_of[r[0]]
                        olat, olon = parse_float(colarr["LATITUDE"][i]), parse_float(colarr["LONGITUDE"][i])
                        old_in = (bool(shapely.contains_xy(g, olon, olat))
                                  if olat is not None and olon is not None else None)
                        c4.add("loc_new_point_outside_named_county", r[4],
                               {"record": r[0], "county_key": list(key), "new_lat": r[1], "new_lon": r[2],
                                "approx_dist_km": round(float(dist_km), 2), "old_point_inside_county": old_in})
                c4.info["loc_county_checked"] = n_checked
                c4.info["loc_county_not_in_polygons"] = n_no_poly

    c4.info["dup_patches"] = len(dup_rows)
    if dup_rows:
        a = np.array([d[1] for d in dup_rows])
        b = np.array([d[2] for d in dup_rows])
        lat = pd.to_numeric(pd.Series(colarr["LATITUDE"]), errors="coerce").to_numpy(dtype=float)
        lon = pd.to_numeric(pd.Series(colarr["LONGITUDE"]), errors="coerce").to_numpy(dtype=float)
        dates = pd.to_datetime(pd.Series(colarr["DISCOVERY_DATE"]), errors="coerce", utc=True, format="ISO8601")
        dates = dates.dt.tz_localize(None)
        ts = dates.to_numpy().astype("datetime64[s]").astype("int64").astype(float)
        ts[dates.isna().to_numpy()] = np.nan
        dist = haversine_km(lat[a], lon[a], lat[b], lon[b])
        ddays = np.abs(ts[a] - ts[b]) / 86400.0
        ss = colarr["SOURCE_SYSTEM"]
        for k, (p, ia, ib) in enumerate(dup_rows):
            if np.isnan(dist[k]):
                c4.add("dup_coords_unparseable", p)
            elif dist[k] > 10.0:
                c4.add("dup_distance_gt_10km", p, {"km": round(float(dist[k]), 3)})
            if np.isnan(ddays[k]):
                c4.add("dup_date_unparseable", p)
            elif ddays[k] > 10.0:
                c4.add("dup_dates_gt_10_days", p, {"days": float(ddays[k])})
            if ss[ia] == ss[ib]:
                c4.add("dup_same_source_system", p, {"source_system": ss[ia]})
        c4.info["dup_max_km"] = float(np.nanmax(dist))
        c4.info["dup_max_days"] = float(np.nanmax(ddays))

    # ---- check 7: confidence
    byrule = collections.defaultdict(list)
    for p in patches:
        byrule[p["rule"]].append(p["confidence"])
        if p["confidence"] < 0.5:
            c7.add("confidence_lt_0.5", p)
    dist_out = {}
    for rule, v in sorted(byrule.items()):
        arr = np.asarray(v, dtype=float)
        dist_out[rule] = {
            "n": int(arr.size), "min": float(arr.min()), "p05": float(np.quantile(arr, 0.05)),
            "median": float(np.median(arr)), "mean": float(arr.mean()),
            "p95": float(np.quantile(arr, 0.95)), "max": float(arr.max()),
            "n_lt_0.5": int((arr < 0.5).sum()),
        }
    c7.info["by_rule"] = dist_out
    comp = collections.Counter((p["rule"], p["field"]) for p in patches)
    c3.info["rule_field_counts"] = {"%s|%s" % k: v for k, v in sorted(comp.items())}
    c3.info["patches_checked"] = len(patches)

    # ---- report
    report = {
        "patch_file": args.patches, "gpkg": args.gpkg, "years": years, "full": bool(args.full),
        "header": jsonable(header), "n_patches_in_file": n_all_patches,
        "n_patches_checked": len(patches), "rows_loaded": n_table,
        "checks": {k: v.to_json() for k, v in checks.items()},
    }
    hard = {k: checks[k].total for k in HARD_CHECKS}
    report["hard_violations"] = hard
    report["pass"] = all(v == 0 for v in hard.values())
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1, ensure_ascii=True)

    print("patch file : %s" % args.patches)
    print("patches    : %d in file, %d checked (years=%s, mode=%s, rows loaded=%d)" %
          (n_all_patches, len(patches), years, "full" if args.full else "subset", n_table))
    print("%-22s %10s  %s" % ("check", "violations", "breakdown"))
    for k, ck in checks.items():
        bd = "n<0.5" if k == "7_confidence" else ", ".join("%s=%d" % kv for kv in sorted(ck.counts.items()))
        print("%-22s %10d  %s%s" % (k, ck.total, bd[:160], "  [hard]" if k in HARD_CHECKS else ""))
    sh = c5.info["shares"]
    print("share of records touched: value-level %.4f (%d), cosmetic %.4f (%d), any %.4f, both %d (universe %d)" %
          (sh["share_value_level"], sh["records_value_level"], sh["share_cosmetic"], sh["records_cosmetic"],
           sh["share_any"], sh["records_both"], sh["universe_rows"]))
    print("confidence by rule:")
    for rule, d in dist_out.items():
        print("  %-20s n=%-6d min=%.3f med=%.3f mean=%.3f max=%.3f  <0.5: %d" %
              (rule, d["n"], d["min"], d["median"], d["mean"], d["max"], d["n_lt_0.5"]))
    print("RESULT: %s" % ("PASS" if report["pass"] else "FAIL"))
    if args.report:
        print("report: %s" % args.report)
    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()

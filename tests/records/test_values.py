"""Tests for firewitness.records.values: plant synthetic errors in a clean table, recover them exactly."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from firewitness.core import Patch, apply_patches, load_region, missing, revert_patches
from firewitness.records.values import clean_values

CFG = load_region("/home/user/wildfireguardiandata/firewitness/records", "us")


def _fmt(v, dec=1):
    return f"{v:.{dec}f}"


def make_sitreps(n_inc=25, n_rep=12, seed=0, as_str=True) -> pd.DataFrame:
    """Clean synthetic ICS-209 sitreps: monotone area, cost, containment; smooth weather."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_inc):
        area = float(rng.integers(200, 3000))
        cost = float(rng.integers(50, 400)) * 1000
        pct = 0.0
        t0 = int(rng.integers(70, 90))
        for j in range(n_rep):
            area = round(area * float(rng.uniform(1.0, 1.12)), 0)
            cost = round(cost * float(rng.uniform(1.02, 1.1)), 0)
            pct = min(100.0, pct + float(rng.integers(0, 12)))
            rows.append({
                "rid": f"s{i}_{j}",
                "INCIDENT_ID": f"2010_X{i}_FIRE{i}",
                "REPORT_TO_DATE": (pd.Timestamp("2010-07-01") + pd.Timedelta(days=j)).strftime("%Y-%m-%d"),
                "ACRES": area, "EST_IM_COST_TO_DATE": cost, "PCT_CONTAINED_COMPLETED": pct,
                "C_TEMP": float(t0 + rng.integers(-3, 4)), "C_RH": float(rng.integers(18, 40)),
                "C_WIND_SPEED": float(rng.integers(3, 12)), "INCIDENT_NAME": f"FIRE {i}",
                "REMARKS": "line one of a normal remark",
            })
    df = pd.DataFrame(rows)
    if as_str:
        for c in ["ACRES", "EST_IM_COST_TO_DATE", "PCT_CONTAINED_COMPLETED", "C_TEMP", "C_RH", "C_WIND_SPEED"]:
            df[c] = df[c].map(lambda v: _fmt(v, 1))
    return df


def by_field(patches, rid, field):
    return [p for p in patches if p.record_id == rid and p.field == field]


def test_clean_table_yields_no_patches():
    for as_str in (True, False):
        df = make_sitreps(as_str=as_str)
        patches, flags = clean_values(df, "ics_sitreps", CFG)
        assert patches == []
        assert list(flags.columns) == ["record_id", "field", "value", "reason", "detail"]


def test_legit_zero_and_99_are_not_sentinels():
    df = make_sitreps()
    df.loc[df.index[::7], "PCT_CONTAINED_COMPLETED"] = "100.0"
    df.loc[df.index[[5, 50, 120]], "PCT_CONTAINED_COMPLETED"] = "99.0"
    df.loc[df.index[3], "C_WIND_SPEED"] = "0.0"
    df.loc[df.index[4], "PCT_CONTAINED_COMPLETED"] = "0.0"
    patches, _ = clean_values(df, "ics_sitreps", CFG)
    assert [p for p in patches if p.rule == "val:placeholder"] == []


@pytest.mark.parametrize("as_str", [True, False])
@pytest.mark.parametrize("factor,name", [(2.471, "acre_ha"), (1 / 2.471, "ha_acre"), (1000.0, "x1000"), (0.001, "x0.001")])
def test_area_unit_slip_recovered_exactly(as_str, factor, name):
    clean = make_sitreps(as_str=as_str)
    df = clean.copy()
    idx = [5, 40, 77, 130, 200, 255]
    for i in idx:
        v = float(clean["ACRES"].iloc[i])
        dec = 4 if factor < 0.01 else 1
        slipped = round(v * factor, dec)
        df.loc[df.index[i], "ACRES"] = _fmt(slipped, dec) if as_str else slipped
    patches, flags = clean_values(df, "ics_sitreps", CFG)
    got = {p.record_id: p for p in patches if p.field == "ACRES"}
    for i in idx:
        rid = clean["rid"].iloc[i]
        assert rid in got, (name, i)
        p = got[rid]
        assert p.rule == "val:unit_slip" and p.new == clean["ACRES"].iloc[i]
        assert p.old == df["ACRES"].iloc[i] and 0 <= p.confidence <= 1 and p.evidence
    # applying every patch restores the clean table exactly
    recs = df.set_index("rid").to_dict("index")
    out = apply_patches(recs, patches, strict=True)
    for rid, rec in out.items():
        assert rec["ACRES"] == clean.set_index("rid").at[rid, "ACRES"]
    assert len(patches) == len(idx)


def test_cost_thousand_slip_and_digit_glitch():
    clean = make_sitreps()
    df = clean.copy()
    df.loc[df.index[20], "EST_IM_COST_TO_DATE"] = _fmt(float(clean["EST_IM_COST_TO_DATE"].iloc[20]) / 1000, 3)
    df.loc[df.index[50], "EST_IM_COST_TO_DATE"] = _fmt(float(clean["EST_IM_COST_TO_DATE"].iloc[50]) * 10, 1)
    patches, _ = clean_values(df, "ics_sitreps", CFG)
    assert len(patches) == 2
    p20 = by_field(patches, clean["rid"].iloc[20], "EST_IM_COST_TO_DATE")[0]
    p50 = by_field(patches, clean["rid"].iloc[50], "EST_IM_COST_TO_DATE")[0]
    assert float(p20.new) == pytest.approx(float(clean["EST_IM_COST_TO_DATE"].iloc[20]), rel=1e-9)
    assert p20.rule == "val:unit_slip" and p50.rule == "val:sequence_glitch"
    assert float(p50.new) == float(clean["EST_IM_COST_TO_DATE"].iloc[50])


def test_spec_example_1000_1100_110_1300():
    df = pd.DataFrame({"rid": list("abcd"), "INCIDENT_ID": ["I"] * 4,
                       "REPORT_TO_DATE": ["2010-07-01", "2010-07-02", "2010-07-03", "2010-07-04"],
                       "ACRES": ["1000", "1100", "110", "1300"]})
    patches, flags = clean_values(df, "ics_sitreps", CFG)
    assert len(patches) == 1 and patches[0].record_id == "c" and patches[0].new == "1100"
    assert patches[0].rule == "val:sequence_glitch"


def test_real_shrink_and_unexplained_glitch_are_flagged_not_patched():
    df = pd.DataFrame({"rid": list("abcde"), "INCIDENT_ID": ["I"] * 5,
                       "REPORT_TO_DATE": [f"2010-07-0{i}" for i in range(1, 6)],
                       "ACRES": ["1000", "1100", "1150", "1130", "1300"]})
    patches, flags = clean_values(df, "ics_sitreps", CFG)
    assert patches == []
    assert "area_shrinks" in set(flags.reason) and list(flags[flags.reason == "area_shrinks"].record_id) == ["d"]
    df["ACRES"] = ["1000", "1100", "400", "1200", "1300"]          # no factor explains 400
    patches, flags = clean_values(df, "ics_sitreps", CFG)
    assert patches == [] and "area_isolated_glitch" in set(flags.reason)
    df["ACRES"] = ["1000", "10000", "1010", "10000", "1020"]       # alternating: not a typo pattern
    patches, _ = clean_values(df, "ics_sitreps", CFG)
    assert patches == []


def test_sequence_breaks_across_incident_and_gap():
    df = pd.DataFrame({"rid": list("abcd"), "INCIDENT_ID": ["I", "I", "J", "J"],
                       "REPORT_TO_DATE": ["2010-07-01", "2010-07-02", "2010-07-03", "2010-07-04"],
                       "ACRES": ["5000", "5100", "100", "110"]})   # new incident restarts small: fine
    patches, flags = clean_values(df, "ics_sitreps", CFG)
    assert patches == [] and len(flags) == 0


def test_numeric_sentinels_and_text_placeholders_blanked():
    clean = make_sitreps()
    df = clean.copy()
    df.loc[df.index[10], "EST_IM_COST_TO_DATE"] = "-999.0"
    df.loc[df.index[11], "ACRES"] = "-9999.0"
    df.loc[df.index[12], "INCIDENT_NAME"] = "N/A"
    df.loc[df.index[13], "REMARKS"] = "?"
    patches, _ = clean_values(df, "ics_sitreps", CFG)
    assert len(patches) == 4 and all(p.rule == "val:placeholder" and p.new == missing() for p in patches)
    assert {(p.record_id, p.field) for p in patches} == {
        (clean["rid"].iloc[10], "EST_IM_COST_TO_DATE"), (clean["rid"].iloc[11], "ACRES"),
        (clean["rid"].iloc[12], "INCIDENT_NAME"), (clean["rid"].iloc[13], "REMARKS")}
    assert all(p.evidence and 0 <= p.confidence <= 1 for p in patches)


def test_context_sentinel_99999_blanked_only_when_column_shows_it():
    df = make_sitreps(n_inc=40)
    rows = df.index[::37][:8]
    df.loc[rows, "EST_IM_COST_TO_DATE"] = "99999.0"
    patches, _ = clean_values(df, "ics_sitreps", CFG)
    ph = [p for p in patches if p.rule == "val:placeholder" and p.field == "EST_IM_COST_TO_DATE"]
    assert len(ph) == len(rows) and all(p.old == "99999.0" for p in ph)
    # a single 99999 in a column is not a sentinel by context alone
    df2 = make_sitreps(n_inc=40)
    df2.loc[df2.index[100], "C_WIND_SPEED"] = "99999.0"
    patches, flags = clean_values(df2, "ics_sitreps", CFG)
    assert not [p for p in patches if p.field == "C_WIND_SPEED" and p.rule == "val:placeholder"]
    assert "possible_sentinel" in set(flags.reason)


def test_isolated_spike_sentinel_in_sequence():
    df = pd.DataFrame({"rid": list("abcd"), "INCIDENT_ID": ["I"] * 4,
                       "REPORT_TO_DATE": [f"2010-07-0{i}" for i in range(1, 5)],
                       "ACRES": ["1000", "1100", "99999", "1200"]})
    patches, _ = clean_values(df, "ics_sitreps", CFG)
    assert len(patches) == 1 and patches[0].rule == "val:placeholder" and patches[0].new == missing()


def test_hidden_characters_and_mojibake():
    u = chr
    dirty = {
        "a": "ELK" + u(0xA0) + "CREEK",                       # NBSP
        "b": u(0xFEFF) + "PINE",                              # BOM
        "c": "ZERO" + u(0x200B) + "WIDTH",                    # zero-width space
        "d": "TAB" + u(7) + "BELL",                           # control character
        "e": "  padded  ",                                    # edge whitespace
        "f": "caf" + u(0xC3) + u(0xA9) + " fire",             # utf-8 read as latin-1
        "g": "it" + u(0xE2) + u(0x20AC) + u(0x2122) + "s" + u(0xC2) + u(0xA0) + "fire",   # cp1252 mojibake
    }
    clean = {"a": "ELK CREEK", "b": "PINE", "c": "ZEROWIDTH", "d": "TABBELL", "e": "padded",
             "f": "caf" + u(0xE9) + " fire", "g": "it" + u(0x2019) + "s fire"}
    df = pd.DataFrame({"rid": list(dirty), "NAME": list(dirty.values()), "OK": ["fine"] * 7})
    patches, flags = clean_values(df, "generic", CFG)
    new = {p.record_id: p.new for p in patches}
    assert new == clean
    assert all(p.field == "NAME" and p.rule in ("val:hidden_chars", "val:mojibake") for p in patches)
    assert len(patches) == 7
    # junk that does not decode to text is left alone
    junk = pd.DataFrame({"rid": ["x"], "NAME": ["didn" + u(0xC2) + u(0xBF) + "t"]})
    assert clean_values(junk, "generic", CFG)[0] == []
    # patches apply strictly and revert exactly
    recs = df.set_index("rid").to_dict("index")
    out = apply_patches(recs, patches)
    assert revert_patches(out, patches) == recs


def test_text_placeholders_respect_column_context():
    names = [f"FIRE {i}" for i in range(80)]
    df = pd.DataFrame({"rid": range(86), "FIRE_NAME": names + ["UNKNOWN", "N/A", "unk", "-", "None", "NA"],
                       "CAUSE": ["Lightning"] * 80 + ["UNKNOWN"] * 6})
    patches, _ = clean_values(df, "generic", CFG)
    # CAUSE: UNKNOWN is an ordinary category and must stay; FIRE_NAME placeholders are blanked
    assert {p.field for p in patches} == {"FIRE_NAME"} and len(patches) == 6


def test_weather_unit_slip_neighbours_and_ranges():
    df = pd.DataFrame({"rid": list("abcde"), "INCIDENT_ID": ["I"] * 5,
                       "REPORT_TO_DATE": [f"2010-07-0{i}" for i in range(1, 6)],
                       "C_TEMP": ["85", "88", "30", "86", "84"],           # 30 is Celsius (86 F)
                       "C_RH": ["20", "25", "0.22", "18", "130"],          # fraction; and an impossible 130
                       "C_WIND_SPEED": ["5", "6", "7", "8", "-4"]})
    patches, flags = clean_values(df, "ics_sitreps", CFG)
    got = {(p.record_id, p.field): p for p in patches}
    assert got[("c", "C_TEMP")].new == "86" and got[("c", "C_TEMP")].rule == "val:weather_unit_slip"
    assert got[("c", "C_RH")].new == "22"
    assert set(flags.reason) >= {"rh_out_of_range", "wind_negative"}
    assert ("e", "C_RH") not in got


def test_gust_below_wind_flagged():
    df = pd.DataFrame({"rid": list("ab"), "INCIDENT_ID": ["I"] * 2, "REPORT_TO_DATE": ["2010-07-01", "2010-07-02"],
                       "C_WIND_SPEED": ["10", "10"], "C_WIND_GUST": ["20", "5"]})
    patches, flags = clean_values(df, "ics_sitreps", CFG)
    assert patches == [] and list(flags.record_id) == ["b"] and flags.reason.iloc[0] == "gust_below_wind"


def test_grid_weather_check():
    df = pd.DataFrame({"rid": list("ab"), "INCIDENT_ID": ["I", "J"], "REPORT_TO_DATE": ["2010-07-01", "2010-07-01"],
                       "POO_LATITUDE": ["40.0", "40.0"], "POO_LONGITUDE": ["-120.0", "-120.0"],
                       "C_TEMP": ["29", "84"], "C_RH": ["0.3", "30"]})
    calls = []

    def grid(lat, lon, date):
        calls.append((lat, lon, str(date)))
        return {"temp_f": 85.0, "rh": 30.0}

    p0, _ = clean_values(df, "ics_sitreps", CFG)                    # no neighbours, no grid: nothing
    assert p0 == [] and calls == []
    patches, _ = clean_values(df, "ics_sitreps", CFG, grid=grid)
    got = {(p.record_id, p.field): p.new for p in patches}
    assert got == {("a", "C_TEMP"): "84", ("a", "C_RH"): "30"}
    assert calls and calls[0][2] == "2010-07-01"


def test_fpafod_class_slip_and_clean():
    n = 300
    rng = np.random.default_rng(1)
    size = np.round(rng.lognormal(0.5, 1.8, n), 2).clip(0.01, 4000)
    def cls(v):
        return "A" if v <= 0.25 else "B" if v < 10 else "C" if v < 100 else "D" if v < 300 else "E" if v < 1000 else "F" if v < 5000 else "G"
    df = pd.DataFrame({"rid": [str(i) for i in range(n)], "FIRE_SIZE": size, "FIRE_SIZE_CLASS": [cls(v) for v in size],
                       "FIRE_NAME": [f"F{i}" for i in range(n)],
                       "DISCOVERY_DATE": ["2010-07-01T00:00:00.0Z"] * n, "CONT_DATE": ["2010-07-02T00:00:00.0Z"] * n})
    patches, flags = clean_values(df, "fpafod", CFG)
    assert patches == [] and len(flags) == 0
    bad = df.copy()
    i = int(np.flatnonzero((size > 20) & (size < 80))[0])     # class C: x1000 -> F, x2.47 stays C? pick factor 1000
    bad.loc[i, "FIRE_SIZE"] = round(size[i] * 1000, 2)
    patches, _ = clean_values(bad, "fpafod", CFG)
    assert len(patches) == 1 and patches[0].record_id == str(i) and patches[0].new == pytest.approx(size[i], rel=1e-6)
    assert patches[0].rule == "val:unit_slip"
    # a size outside its class with no factor that repairs it is flagged only
    bad2 = df.copy()
    bad2.loc[i, "FIRE_SIZE"] = size[i] * 7.3
    patches, flags = clean_values(bad2, "fpafod", CFG)
    assert patches == [] and "size_class_mismatch" in set(flags.reason)


def test_fpafod_boundaries_and_dates():
    df = pd.DataFrame({"rid": list("abcdefg"), "FIRE_SIZE": [0.25, 9.9, 10.0, 99.9, 100.0, 5000.0, 4999.9],
                       "FIRE_SIZE_CLASS": list("ABCCDGF"),
                       "DISCOVERY_DATE": ["2010-07-05T00:00:00.0Z"] * 7, "CONT_DATE": ["2010-07-01T00:00:00.0Z"] * 7})
    patches, flags = clean_values(df, "fpafod", CFG)
    assert patches == []
    assert (flags.reason == "cont_before_discovery").sum() == 7 and "size_class_mismatch" not in set(flags.reason)


def test_incidents_unit_slip_needs_two_sources():
    df = pd.DataFrame({"rid": list("abc"), "FINAL_ACRES": ["2471.0", "2471.0", "500.0"],
                       "FOD_FINAL_ACRES": ["1000.0", "1000.0", "480.0"], "FIRED_ACRES": ["1200.0", "", ""]})
    patches, flags = clean_values(df, "ics_incidents", CFG)
    assert len(patches) == 1 and patches[0].record_id == "a" and patches[0].new == "1000.0"
    assert patches[0].rule == "val:unit_slip"
    assert list(flags[flags.reason == "unit_slip_candidate"].record_id) == ["b"]


def test_inputs_never_mutated_and_patches_valid():
    df = make_sitreps()
    df.loc[df.index[3], "REMARKS"] = " padded "
    df.loc[df.index[8], "EST_IM_COST_TO_DATE"] = "-9999.0"
    before = df.copy(deep=True)
    patches, _ = clean_values(df, "ics_sitreps", CFG)
    pd.testing.assert_frame_equal(df, before)
    for p in patches:
        assert isinstance(p, Patch)
        p.validate()
        assert p.rule.startswith("val:")


def test_unknown_table_rejected():
    with pytest.raises(ValueError):
        clean_values(pd.DataFrame({"rid": ["a"]}), "nope", CFG)


def test_raw_area_unit_column_normalises_square_miles():
    # AREA in sq miles for one report: 1.5 sq mi = 960 acres. The series is in acres otherwise.
    df = pd.DataFrame({"rid": list("abcd"), "INCIDENT_NUMBER": ["I"] * 4,
                       "REPORT_DATE": [f"2010-07-0{i} 00:00:00" for i in range(1, 5)],
                       "AREA": ["900", "1.5", "980", "1000"], "AREA_MEASUREMENT": ["ACRES", "SQ MILES", "ACRES", "ACRES"]})
    patches, flags = clean_values(df, "ics_sitreps", CFG)
    assert patches == [] and len(flags) == 0


def test_performance_vectorised():
    import time
    parts = []
    for s in range(4):
        d = make_sitreps(n_inc=100, n_rep=30, seed=s)
        d["INCIDENT_ID"] = d["INCIDENT_ID"] + f"_{s}"
        parts.append(d)
    df = pd.concat(parts, ignore_index=True)
    df["rid"] = [f"r{i}" for i in range(len(df))]
    t = time.time()
    patches, _ = clean_values(df, "ics_sitreps", CFG)
    assert time.time() - t < 30 and patches == []


def test_fpafod_reference_column_without_class():
    df = pd.DataFrame({"rid": list("abc"), "FIRE_SIZE": [2471.0, 520.0, 12.0], "ICS_FINAL_ACRES": [1000.0, 500.0, np.nan]})
    patches, _ = clean_values(df, "fpafod", CFG)
    assert len(patches) == 1 and patches[0].record_id == "a" and patches[0].new == pytest.approx(1000.0)

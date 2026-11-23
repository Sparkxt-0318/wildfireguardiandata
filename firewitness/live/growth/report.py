"""Numbers, table, figure and results text from the released growth files only (protocol/GROWTH_PROTOCOL.md §8-§9).

Shipped in the release as growth_report.py next to growth_stats.py; `growth_recompute.py` calls compute() and
render() and compares with the released GROWTH_RESULTS.md byte for byte.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from . import stats as st
except ImportError:  # running from the release folder
    import growth_stats as st

FILES = {"fires": "growth_fires.csv", "runs": "growth_runs.csv", "series": "growth_series_fire.parquet",
         "placebo": "growth_series_placebo.parquet", "cfg": "growth_us.json", "thr": "growth_thresholds_us.json",
         "prov": "growth_provenance.json", "set_a": "growth_fires_set_a.csv", "set_b": "growth_fires_set_b.csv"}


def load(rel: Path) -> dict:
    rel = Path(rel)
    d = {"fires": pd.read_csv(rel / FILES["fires"], dtype={"perm_id": str, "fdc_first": str}, keep_default_na=True),
         "runs": pd.read_csv(rel / FILES["runs"]),
         "series": pd.read_parquet(rel / FILES["series"]), "placebo": pd.read_parquet(rel / FILES["placebo"]),
         "cfg": json.loads((rel / FILES["cfg"]).read_text())}
    d["fires"]["perm_id"] = d["fires"]["perm_id"].fillna("")
    t = json.loads((rel / FILES["thr"]).read_text()) if (rel / FILES["thr"]).is_file() else None
    d["thr_frozen"] = t.get("thresholds", t) if t else None
    d["prov"] = json.loads((rel / FILES["prov"]).read_text()) if (rel / FILES["prov"]).is_file() else {}
    d["set_a"] = pd.read_csv(rel / FILES["set_a"], dtype=str, keep_default_na=False) if (rel / FILES["set_a"]).is_file() else None
    return d


def thresholds_from(d) -> dict:
    split = d["fires"].drop_duplicates("fire_id").set_index("fire_id").split
    pa = st.placebo_attrs(d["placebo"], d["cfg"])
    pa["split"] = pa.fire_id.map(split)
    use = pa[pa.split.isin(["A", "dev"])]
    return st.thresholds(use, d["cfg"]), pa


def thresholds_from_release(rel) -> dict:
    return thresholds_from(load(rel))[0]


def _same_thr(a, b, tol=1e-9) -> bool:
    if a is None or b is None:
        return False
    for s in a:
        for k in a[s]:
            x, y = a[s][k]["thr"], b.get(s, {}).get(k, {}).get("thr", float("nan"))
            both_nan = x != x and y != y
            if not (both_nan or x == y or abs(x - y) <= tol * max(1.0, abs(x))) or a[s][k]["n"] != b[s][k]["n"]:
                return False
    return True


def onset_repro(d) -> dict:
    """Set A: the trace-back re-run on the new extraction against the released fire label (same onset or both none)."""
    if d["set_a"] is None:
        return {}
    runs = d["runs"].set_index("fire_id")
    k = n = 0
    same_none = same_on = 0
    for _, r in d["set_a"].iterrows():
        if r.fire_id not in runs.index or runs.loc[r.fire_id, "status"] != "ok":
            continue
        lab = json.loads(runs.loc[r.fire_id, "label_recomputed"]) or {}
        new = lab.get("onset_utc")
        old = r.frozen_onset or None
        n += 1
        if old is None and new is None:
            k += 1; same_none += 1
        elif old and new and abs(pd.Timestamp(old).timestamp() - pd.Timestamp(new).timestamp()) <= 300:
            k += 1; same_on += 1
    return {"n": n, "same": k, "same_no_onset": same_none, "same_onset_within_5min": same_on,
            "n_frozen_onsets": int((d["set_a"].frozen_onset != "").sum())}


def compute(rel) -> dict:
    d = load(rel)
    cfg = d["cfg"]
    fires = d["fires"]
    thr_new, pa = thresholds_from(d)
    thr = d["thr_frozen"] or thr_new
    tab = st.build_table(fires, d["series"], thr, cfg)
    num = {"thresholds_recomputed_match_frozen": _same_thr(thr_new, d["thr_frozen"]),
           "thresholds": thr, "headline": st.headline_counts(tab, fires.drop_duplicates("fire_id")),
           "n_fire_satellites": int(len(tab)), "n_fires": int(fires.fire_id.nunique()),
           "n_placebo_anchors": {s: int((pa.split == s).sum()) for s in ("A", "dev", "sealed")},
           "onset_repro_set_a": onset_repro(d), "t0_kind": {}}
    for part in ("A", "dev", "sealed"):
        f1 = fires.drop_duplicates("fire_id")
        f1 = f1[(f1.set == "A") if part == "A" else (f1.split == part)]
        num["t0_kind"][part] = {k: int(v) for k, v in f1.t0_kind.value_counts().sort_index().items()}
    parts = {"sealed": fires.split == "sealed", "dev": fires.split == "dev", "A": fires.set == "A"}
    num["gates"] = {}
    for part, m in parts.items():
        fs = fires[m]
        if not len(fs):
            continue
        ts = tab[tab.fire_id.isin(set(fs.fire_id))]
        g = {"G2": st.g2(fs, d["series"], cfg), "G3": st.g3(ts, cfg), "G4": st.g4(ts, fs, cfg)}
        g["G2"].pop("_rows", None)
        pas = pa[pa.split == part]
        if len(pas):
            g["G1"] = st.g1(pas, thr, cfg)
        g["afternoon"] = afternoon(ts)
        g["measured_slopes"] = measured_summary(ts, cfg)
        num["gates"][part] = g
    curve_part = "sealed" if (fires.split == "sealed").any() else "dev"
    cv = st.curves(tab[tab.fire_id.isin(set(fires[fires.split == curve_part].fire_id))], d["series"], cfg)
    return {"numbers": _clean(num), "table": tab, "curves": cv, "curve_part": curve_part, "prov": d["prov"],
            "cfg": cfg}


def afternoon(ts: pd.DataFrame) -> dict:
    """slope_3h of the selected satellite by local solar hour of t0 (10-18 h vs the rest): medians with n."""
    s = ts[ts.selected & (ts.slope_3h_state != "unknown")]
    day = s[(s.local_solar_hour_t0 >= 10) & (s.local_solar_hour_t0 < 18)]
    rest = s[~s.index.isin(day.index)]
    out = {}
    for name, x in (("t0_10_18h", day), ("t0_other", rest)):
        v = x.slope_3h.to_numpy(float)
        meas = int((x.slope_3h_state == "measured").sum())
        out[name] = {"n": int(len(v)), "median_slope_3h": float(np.median(v)) if len(v) else float("nan"),
                     "measured": meas}
    return out


def measured_summary(ts: pd.DataFrame, cfg) -> dict:
    s = ts[ts.selected & (ts.slope_3h_state == "measured")]
    v = s.slope_3h.to_numpy(float)
    dt = s.doubling_time_h.to_numpy(float)
    dt = dt[np.isfinite(dt) & (s.logslope_3h_state.to_numpy() == "measured")]
    rng = np.random.default_rng(cfg["gates"]["boot_seed"])
    def bmed(x):
        if not len(x):
            return [float("nan")] * 3
        m = np.median(x[rng.integers(0, len(x), (cfg["gates"]["boot_B"], len(x)))], 1)
        return [float(np.median(x)), *st.ci(m)]
    return {"n": int(len(v)), "n_rising": int((v > 0).sum()), "median_slope_3h": bmed(v),
            "n_doubling": int(len(dt)), "median_doubling_time_h": bmed(dt)}


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        x = float(o)
        return None if not math.isfinite(x) else round(x, 6)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


# ---------------------------------------------------------------- outputs
TABLE_COLS = None


def write_outputs(res: dict, out: Path):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    tab = res["table"]
    tab.to_csv(out / "early_growth_v0.1.csv", index=False, float_format="%.6g")
    tab.to_parquet(out / "early_growth_v0.1.parquet", index=False)
    (out / "growth_numbers.json").write_text(json.dumps(res["numbers"], indent=1, sort_keys=True) + "\n")
    res["curves"].to_csv(out / "growth_curves.csv", index=False, float_format="%.6g")


def figure(cv: pd.DataFrame, path: Path, part: str = "sealed"):
    """Slide figure: median fire power and the middle half (quartiles) for fires that ended large vs stayed small.
    Colours: categorical slots 1-2 of the reference palette (#2a78d6, #eb6834), checked for colour-blind separation;
    identity is also carried by line style (solid / dashed) and direct labels."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = {"large": "#2a78d6", "small": "#eb6834"}
    ls = {"large": "-", "small": (0, (6, 3))}
    lab = {"large": "ended large (≥ 1,000 acres)", "small": "stayed small (< 1,000 acres)"}
    plt.rcParams.update({"font.size": 20, "font.family": "DejaVu Sans"})
    fig, ax = plt.subplots(figsize=(13.33, 7.5), dpi=150)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    for g in ("large", "small"):
        c = cv[cv.group == g].sort_values("tau_min")
        if not len(c):
            continue
        x = c.tau_min.to_numpy() / 60.0
        n = int(c.n.max())
        ax.fill_between(x, np.maximum(c.q25, 0.5), np.maximum(c.q75, 0.5), color=col[g], alpha=0.16, lw=0)
        y = np.maximum(c["median"].to_numpy(), 0.5)
        ax.plot(x, y, color=col[g], ls=ls[g], lw=3.5, label=f"{lab[g]}, n = {n} fires")
        ax.annotate(f"{g}\n{y[-1]:.0f} MW", (x[-1], y[-1]), xytext=(10, 0), textcoords="offset points",
                    va="center", fontsize=18, color="#222222")
    ax.set_yscale("log")
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
    ax.yaxis.set_major_locator(FixedLocator([1, 3, 10, 30, 100, 300, 1000, 3000, 10000]))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_xlim(0, 6)
    ax.set_xticks(range(7))
    ax.set_xlabel("hours after the start time t0")
    ax.set_ylabel("fire radiative power (MW, log scale)")
    ax.grid(True, which="major", color="#dddddd", lw=1)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#888888")
    ax.legend(loc="upper left", frameon=False, fontsize=18)
    who = "sealed new fires" if part == "sealed" else "dev fires (draft)"
    ax.set_title(f"Fire power in the first 6 hours, {who}: median and middle half", fontsize=22, loc="left")
    fig.text(0.01, 0.01, "GOES 5-minute frames, 2 km pixels; cloudy frames left out, never filled. Past fires: an "
             "association, not a forecast.", fontsize=14, color="#444444")
    fig.tight_layout(rect=(0, 0.04, 0.95, 1))
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


# ---------------------------------------------------------------- results text
def f_pct(s):
    return f"{100 * s:.1f} %"


def f_ci(lo, hi, nd=2, pct=False):
    if lo is None or hi is None:
        return "–"
    return f"{100 * lo:.1f}–{100 * hi:.1f} %" if pct else f"{lo:.{nd}f} to {hi:.{nd}f}"


def f_num(x, nd=2):
    return "–" if x is None else f"{x:.{nd}f}"


def _sh(x):
    """share triple [p, lo, hi] -> 'p % (lo–hi %)'."""
    if not x or x[0] is None:
        return "–"
    return f"{100 * x[0]:.1f} % ({100 * x[1]:.1f}–{100 * x[2]:.1f} %)"


def _v(x, nd=2):
    return "–" if x is None else f"{x:.{nd}f}"


def _iv(c, nd=2):
    return "–" if not c or c[0] is None else f"{c[0]:.{nd}f} to {c[1]:.{nd}f}"


def _verdict(p):
    return "not enough data" if p is None else ("PASS" if p else "FAIL")


PRIOR_ART = (
    "Fire radiative power measured every 15 minutes from geostationary orbit has been used to follow individual fires "
    "and their daily cycle since SEVIRI (Roberts and Wooster 2008, IEEE TGRS; Roberts et al. 2009, Biogeosciences), "
    "and GOES-16 ABI fire-power retrievals at 5–15 minutes were evaluated over the Americas by Xu et al. (2021, "
    "Science of Remote Sensing). Wiggins et al. (2020, GRL) used GOES-16 fire-power time series of single fires to "
    "explain changes in their smoke, and Benali et al. (2023, ESSD) paired fire growth rates of 80 large Portuguese "
    "fires with SEVIRI fire power. Luo et al. (2026, Science Advances) analysed hourly geostationary observations of "
    "about 9,000 North American fires and report that about 60 % reached peak intensity within 24 hours of detection; "
    "the attribute here is a per-fire, placebo-calibrated slope of the first six hours, not a new kind of measurement.")


def render(n: dict, prov: dict) -> str:
    """GROWTH_RESULTS.md from the numbers (and provenance: commits, opening time). Deterministic."""
    G = n["gates"]
    S = G.get("sealed", {})
    H = n["headline"]
    L = []
    w = L.append
    hs = H.get("sealed", {})
    g1, g2, g3, g4 = S.get("G1", {}), S.get("G2", {}), S.get("G3", {}), S.get("G4", {})
    w("# GROWTH_RESULTS — early growth rate of fire power in the first hours (track growth)")
    w("")
    if hs and hs["fires_tried"] and g4:
        w(f"**Headline: on the {hs['fires_tried']} sealed new fires, {hs['measured_3h']} have a measured 3-hour growth "
          f"rate ({_sh(hs['share_3h'])}); {hs['flat_3h']} are flat (not distinguishable from the placebo) and "
          f"{hs['unknown_3h']} unknown (too few clear frames). Gates: G1 placebo {_verdict(g1.get('pass'))}, "
          f"G2 agreement with the operational product {g2.get('verdict', '–')} (Spearman {_v(g2.get('spearman'))}), "
          f"G3 two satellites {g3.get('verdict', '–')}, G4: the 3-hour growth rate separates fires that ended large "
          f"{'better' if g4.get('better_than_power_t0') else 'not better'} than fire power at t0 and "
          f"{'better' if g4.get('better_than_fdc_first_power') else 'not better'} than the operational product's first "
          f"power (AUC {_v(g4.get('auc_growth_3h', {}).get('value'))} vs {_v(g4.get('auc_power_t0', {}).get('value'))} "
          f"and {_v(g4.get('auc_fdc_first_power', {}).get('value'))}). This is an association on past fires, not a "
          f"forecast.**")
        w("")
    w(f"Protocol: `protocol/GROWTH_PROTOCOL.md` (committed alone with the fire lists at {prov.get('protocol_commit', '–')}"
      f"; amendments inside). Fires: Set A = the 370 fires of the earlier live lists (used before, descriptive only); "
      f"Set B = 310 new WFIGS fires 2023-01-10 to 2025-12-31, 155 dev and 155 sealed. {n['n_fire_satellites']} "
      f"fire-satellite series (GOES-16/17/18/19). Thresholds frozen at {prov.get('thresholds_commit', '–')} "
      f"(`firewitness/live/config/growth_thresholds_us.json`, SHA-256 {prov.get('thresholds_sha256', '–')[:12]}…) "
      f"from {n['n_placebo_anchors']['A'] + n['n_placebo_anchors']['dev']:,} placebo anchors of Set A and dev; "
      f"recomputed from the released placebo series: {'identical' if n['thresholds_recomputed_match_frozen'] else ('DIFFERENT' if prov.get('thresholds_sha256') else 'not yet frozen')}. "
      f"{prov.get('opening', 'Sealed half: not opened.')}")
    w("")
    w("Every number below is recomputed from the release files alone by `growth_recompute.py` (release growth-v0.1). "
      "Intervals: Wilson 95 % for shares; bootstrap by fire (2,000, seed 0) for correlations, AUCs and medians.")
    w("")
    w("## Headline numbers")
    w("")
    w("| quantity | n | value | 95 % interval | source file | what it does not show |")
    w("|---|---|---|---|---|---|")
    src_t = "`early_growth_v0.1.csv` (from `growth_series_fire.parquet`)"
    for part, label in (("sealed", "sealed new fires"), ("dev", "dev new fires (descriptive)"), ("A", "Set A (used before; descriptive)")):
        h = H.get(part)
        if not h or not h["fires_tried"]:
            continue
        w(f"| fires with a measured 3 h growth rate, {label} | {h['fires_tried']} tried | {h['measured_3h']} "
          f"({h['flat_3h']} flat, {h['unknown_3h']} unknown) | {_iv([h['share_3h'][1] * 100, h['share_3h'][2] * 100], 1)} % | {src_t} | "
          f"a measured slope says the power changed more than at 99 % of fire-free anchors, not why or how fast the "
          f"fire spread on the ground |")
    if g1:
        worst = max(g1["by_attribute"].items(), key=lambda kv: kv[1]["share"][0])
        w(f"| G1: placebo anchors called measured, sealed (worst of 7 slope attributes: {worst[0]}) | "
          f"{worst[1]['n_anchors']:,} anchors | {worst[1]['called_measured']} ({100 * worst[1]['share'][0]:.2f} %) | "
          f"{100 * worst[1]['share'][1]:.2f}–{100 * worst[1]['share'][2]:.2f} % | `growth_series_placebo.parquet` | "
          f"placebo anchors are fire-free only by the records; unrecorded heat sources count against the method |")
    if g2:
        w(f"| G2: rank agreement of our 3 h slope with the operational product's, sealed | {g2['n_fire_satellites']} "
          f"fire-satellites ({g2['n_fires']} fires) | Spearman {_v(g2['spearman'])} | {_iv(g2['ci'])} | "
          f"`growth_series_fire.parquet` (P, fdc_P) | only frames where the product reports power, so fires it misses "
          f"early are not in this check |")
    if g3:
        w(f"| G3: two satellites, rank of slope_3h, sealed | {g3['n_fires_both_known']} fires | Spearman "
          f"{_v(g3['spearman'])}; same sign {g3['sign_agree']} of {g3['n_fires_both_measured']} measured on both | "
          f"{_iv(g3['ci'])}; sign {_sh(g3['sign_share'])} | `early_growth_v0.1.csv` | the two views share the "
          f"ground truth but not the pixels; it is not a check against an independent measurement of the fire |")
    if g4:
        for k, lab in (("auc_growth_3h", "AUC, 3 h growth rate"), ("auc_power_t0", "AUC, fire power at t0"),
                       ("auc_fdc_first_power", "AUC, operational product's first power"),
                       ("diff_vs_power_t0", "AUC difference, growth − power at t0"),
                       ("diff_vs_fdc_first_power", "AUC difference, growth − product's first power")):
            w(f"| G4: {lab}, sealed (large = ≥ 1,000 acres) | {g4['n_fires']} fires ({g4['n_large']} large, "
              f"{g4['n_small']} small) | {_v(g4[k]['value'])} | {_iv(g4[k]['ci'])} | `early_growth_v0.1.csv`, "
              f"`growth_fires.csv` (acres) | an association on past fires, not a forecast: final size also depends on "
              f"weather, fuel and suppression after the first hours |")
    ms = S.get("measured_slopes")
    if ms and ms["n"]:
        w(f"| median 3 h slope of sealed fires with a measured rate | {ms['n']} fires ({ms['n_rising']} rising) | "
          f"{_v(ms['median_slope_3h'][0], 1)} MW/h | {_iv(ms['median_slope_3h'][1:], 1)} MW/h | `early_growth_v0.1.csv` | "
          f"fire power, not area: our estimate runs about 1.5× the product (v0.2 S1), and 2 km pixels mix fire and "
          f"background |")
    if ms and ms["n_doubling"]:
        w(f"| median doubling time, sealed fires with measured slope_3h and logslope_3h, rising | {ms['n_doubling']} fires | "
          f"{_v(ms['median_doubling_time_h'][0], 2)} h | {_iv(ms['median_doubling_time_h'][1:], 2)} h | "
          f"`early_growth_v0.1.csv` | the log fit adds 1 MW to every frame; a slow start under a noise floor looks slower |")
    orp = n.get("onset_repro_set_a", {})
    if orp:
        w(f"| Set A: frozen trace-back re-run on the new extraction gives the released label | {orp['n']} fires | "
          f"{orp['same']} same ({orp['same_no_onset']} no onset, {orp['same_onset_within_5min']} onset within 5 min) | – | "
          f"`growth_runs.csv`, `growth_fires_set_a.csv` | t0 of Set A is the released label either way; this checks "
          f"that the re-read satellite data reproduce the frozen method |")
    w("")
    w("## Gates (sealed half, opened once)")
    w("")
    if g1:
        w(f"**G1 placebo — {_verdict(g1['pass'])}.** Share of sealed placebo anchors called measured with the frozen "
          f"thresholds (limit 2 %):")
        w("")
        w("| attribute | anchors | called measured | share (95 % CI) | by satellite (called / anchors) |")
        w("|---|---|---|---|---|")
        for k, v in g1["by_attribute"].items():
            bs = ", ".join(f"{s} {a}/{b}" for s, (a, b) in sorted(v["by_sat"].items()))
            w(f"| {k} | {v['n_anchors']:,} | {v['called_measured']} | {_sh(v['share'])} | {bs} |")
        w("")
    if g2:
        w(f"**G2 agreement with the operational product — {g2['verdict']}.** Spearman {_v(g2['spearman'])} "
          f"({_iv(g2['ci'])}) over {g2['n_fire_satellites']} fire-satellites ({g2['n_fires']} fires) with at least 6 common "
          f"frames in the first 3 h (median {_v(g2['median_common_frames'], 0)}); target 0.6.")
        w("")
    if g3:
        w(f"**G3 two satellites — {g3['verdict']}.** {g3['n_fires_both_known']} sealed fires have a usable 3 h window on "
          f"both satellites: Spearman {_v(g3['spearman'])} ({_iv(g3['ci'])}); of {g3['n_fires_both_measured']} measured "
          f"on both, {g3['sign_agree']} agree in sign ({_sh(g3['sign_share'])}). Targets: ρ ≥ 0.6, sign ≥ 80 %, n ≥ 10.")
        w("")
    if g4:
        w(f"**G4 is it informative.** {g4['n_fires']} of {g4['n_sealed_fires']} sealed fires have a usable slope_3h and a "
          f"known power at t0 ({g4['n_large']} ended ≥ 1,000 acres, {g4['n_small']} stayed below). AUC: growth "
          f"{_v(g4['auc_growth_3h']['value'])} ({_iv(g4['auc_growth_3h']['ci'])}), power at t0 "
          f"{_v(g4['auc_power_t0']['value'])} ({_iv(g4['auc_power_t0']['ci'])}), product's first power "
          f"{_v(g4['auc_fdc_first_power']['value'])} ({_iv(g4['auc_fdc_first_power']['ci'])}). Differences: growth − "
          f"power at t0 {_v(g4['diff_vs_power_t0']['value'])} ({_iv(g4['diff_vs_power_t0']['ci'])}); growth − product "
          f"{_v(g4['diff_vs_fdc_first_power']['value'])} ({_iv(g4['diff_vs_fdc_first_power']['ci'])}). Growth separates "
          f"{'better' if g4['better_than_power_t0'] else 'not better'} than power at t0 and "
          f"{'better' if g4['better_than_fdc_first_power'] else 'not better'} than the product's first power (better = "
          f"interval of the difference above 0). Association on past fires, not a forecast.")
        w("")
    af = S.get("afternoon")
    if af:
        a1, a2 = af["t0_10_18h"], af["t0_other"]
        w(f"**Time of day (descriptive).** Sealed fires with a usable 3 h window starting 10–18 h local solar time: n = "
          f"{a1['n']}, median slope_3h {_v(a1['median_slope_3h'], 1)} MW/h, {a1['measured']} measured; starting at other "
          f"hours: n = {a2['n']}, median {_v(a2['median_slope_3h'], 1)} MW/h, {a2['measured']} measured. The column "
          f"`local_solar_hour_t0` is in the table so that a reader can separate the afternoon cycle from the fire.")
        w("")
    w("## Descriptive: dev and Set A")
    w("")
    w("Same computation, same thresholds. Set A fires were used before; dev fires were used to check the pipeline. "
      "Nothing was tuned on either.")
    w("")
    w("| part | G1 worst share | G2 Spearman (n) | G3 Spearman (n) | G4 AUC growth / t0 / product (n) |")
    w("|---|---|---|---|---|")
    for part in ("dev", "A"):
        x = G.get(part)
        if not x:
            continue
        a = x.get("G1")
        worst = max(a["by_attribute"].values(), key=lambda v: v["share"][0])["share"] if a else None
        w(f"| {part} | {_sh(worst) if worst else '–'} | {_v(x['G2']['spearman'])} ({x['G2']['n_fire_satellites']}) | "
          f"{_v(x['G3']['spearman'])} ({x['G3']['n_fires_both_known']}) | {_v(x['G4']['auc_growth_3h']['value'])} / "
          f"{_v(x['G4']['auc_power_t0']['value'])} / {_v(x['G4']['auc_fdc_first_power']['value'])} ({x['G4']['n_fires']}) |")
    w("")
    w("Start time t0 by kind (fires): " + "; ".join(
        f"{p}: " + ", ".join(f"{k} {v}" for k, v in n["t0_kind"][p].items()) for p in ("sealed", "dev", "A") if n["t0_kind"].get(p)))
    w("")
    w("## Prior art")
    w("")
    w(PRIOR_ART)
    w("")
    w("## What the attribute cannot tell you")
    w("")
    w("- 2 km pixels: P is the radiance excess of whole pixels over a modelled background; a fire under ~30 MW is near "
      "the noise, and a slope says nothing about where in the pixel the fire grows.")
    w("- Cloud: cloudy frames are missing, never zero; a fire under cloud for its first hours is `unknown`, with the "
      "clear-frame count. Thick smoke flagged as cold cloud is lost the same way.")
    w("- The afternoon cycle: fires that start in the morning rise with the heating of the day. `local_solar_hour_t0` "
      "is given so that this can be separated; the slope itself does not remove it.")
    w("- No claim about ignition: t0 is when GOES could first tell the fire from its background (or the first "
      "detection), not when it started.")
    w("- Large fires that spread beyond the 7 × 7 region (about 14–20 km) or into their own background annulus lose "
      "power to the background; their late slopes are underestimates.")
    w("- GOES-19 (GOES-East from 2025-04-07) uses the onset threshold calibrated on GOES-16; its growth thresholds come "
      "from its own dev placebo anchors.")
    w("")
    w("Files (release growth-v0.1, checksums in `SHA256SUMS.txt`): `early_growth_v0.1.csv` / `.parquet`, "
      "`growth_series_fire.parquet`, `growth_series_placebo.parquet`, `growth_fires.csv`, `growth_runs.csv`, "
      "`growth_fires_set_a.csv`, `growth_fires_set_b.csv`, `growth_thresholds_us.json`, `growth_us.json`, "
      "`growth_numbers.json`, `growth_provenance.json`, `growth_stats.py`, `growth_report.py`, `growth_recompute.py`, "
      "`DATA_CARD.md`, `growth_curves_sealed.png`, `growth_curves.csv`.")
    return "\n".join(L) + "\n"


def open_sealed(a):
    """Protocol §7: once. Needs the thresholds file committed and the sealed artifact folder."""
    import subprocess
    import time
    thr_file = Path(__file__).resolve().parent.parent / "config" / "growth_thresholds_us.json"
    if not a.open_sealed:
        print("refusing: pass --i-am-opening-the-sealed-half (the sealed half is opened once)")
        return 2
    rel_thr = subprocess.run(["git", "ls-files", "--error-unmatch", str(thr_file)], capture_output=True).returncode
    dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(thr_file)]).returncode
    if rel_thr or dirty:
        print("refusing: the thresholds file must be committed and unchanged")
        return 2
    marker = Path("results/growth/SEALED_OPENED.md")
    if marker.is_file():
        print(f"refusing: the sealed half was already opened ({marker.read_text().strip()})")
        return 2
    if not a.sealed_dir:
        print("refusing: --sealed-dir (the downloaded growth-sealed artifact) is needed")
        return 2
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    from .common import sha256_file
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(f"Sealed half opened once at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} from commit "
                      f"{head}; thresholds file SHA-256 {sha256_file(thr_file)}; sealed folder {a.sealed_dir}.\n")
    print(marker.read_text())
    return 0


def recompute_main(rel: Path, out: Path) -> int:
    import subprocess
    import sys
    return subprocess.call([sys.executable, str(Path(rel) / "growth_recompute.py"), "--dir", str(rel), "--out", str(out)])

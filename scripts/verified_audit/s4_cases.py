"""Verified-tier audit, step 4: the case list (rebuilt verified placebos + seeded record sample) and one blind
composite image per case (rubric sections 2-3).

Usage: s4_cases.py list | render [threads]
Outputs (under $FIREWITNESS_RAW/audit_cases/): cases_key.csv (unblinding key; not shown to raters),
cases_public.csv (case id + evidence text only), case_###.png.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import numpy as np
import pandas as pd

from firewitness.caught.fetch import RAW_ROOT

OUT = RAW_ROOT / "audit_cases"
SEED = "verified-audit-v1:"
ALLOC = {"A": 1, "B": 28, "C": 40, "D": 12, "E": 9, "F": 6, "G": 4}
REL = "release/caught-v0.1/caught_labels_v0.1_{y}.parquet"
WC = {10: "tree cover", 20: "shrubland", 30: "grassland", 40: "cropland", 50: "built-up", 60: "bare/sparse",
      70: "snow/ice", 80: "water", 90: "herbaceous wetland", 95: "mangrove", 100: "moss/lichen", 0: "no data"}


def h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def released():
    d = pd.concat([pd.read_parquet(REL.format(y=y)) for y in (2018, 2019, 2020)], ignore_index=True)
    return d


def record_sample(rel: pd.DataFrame) -> pd.DataFrame:
    v = rel[rel.tier == "verified"].copy()
    v["key"] = [h(SEED + r) for r in v.rid]
    parts = []
    for k, n in ALLOC.items():
        parts.append(v[v.FIRE_SIZE_CLASS == k].sort_values("key").head(n))
    return pd.concat(parts, ignore_index=True)


def stage_list(arms=("R", "P")):
    from shapely import wkb
    OUT.mkdir(parents=True, exist_ok=True)
    rel = released()
    rs = record_sample(rel)
    rs_rows = pd.DataFrame({
        "rid": rs.rid, "arm": "R", "LATITUDE": rs.LATITUDE, "LONGITUDE": rs.LONGITUDE, "r_m": rs.r_m, "t0": rs.t0,
        "t1": rs.t1, "FIRE_SIZE_CLASS": rs.FIRE_SIZE_CLASS, "FIRE_YEAR": rs.FIRE_YEAR, "STATE": rs.STATE,
        "std_label": rs.std_label, "witnesses": rs.witnesses, "pairs": rs.pairs, "evidence": rs.evidence,
        "scar_sensor": rs.scar_sensor, "scar_pre": rs.scar_pre, "scar_post": rs.scar_post,
        "label_wkt": [wkb.loads(g).wkt if g is not None else None for g in rs.geometry], "own_fod": rs.FOD_ID,
        "of_rid": None})
    if "P" in arms:
        lab = pd.read_parquet(RAW_ROOT / "derived_caught" / "audit_S3_placebo_labels.parquet")
    else:
        lab = pd.DataFrame(columns=["rid", "tier", "LATITUDE", "LONGITUDE", "r_m", "t0", "t1", "FIRE_SIZE_CLASS",
                                    "FIRE_YEAR", "STATE", "std_label", "witnesses", "pairs", "evidence", "scar_sensor",
                                    "scar_pre", "scar_post", "geometry_wkt", "of_rid"])
    pv = lab[lab.tier == "verified"]
    p_rows = pd.DataFrame({
        "rid": pv.rid, "arm": "P", "LATITUDE": pv.LATITUDE, "LONGITUDE": pv.LONGITUDE, "r_m": pv.r_m, "t0": pv.t0,
        "t1": pv.t1, "FIRE_SIZE_CLASS": pv.FIRE_SIZE_CLASS, "FIRE_YEAR": pv.FIRE_YEAR, "STATE": pv.STATE,
        "std_label": pv.std_label, "witnesses": pv.witnesses, "pairs": pv.pairs, "evidence": pv.evidence,
        "scar_sensor": pv.scar_sensor, "scar_pre": pv.scar_pre, "scar_post": pv.scar_post,
        "label_wkt": pv.geometry_wkt, "own_fod": None, "of_rid": pv.of_rid})
    cases = pd.concat([x for x in (p_rows, rs_rows) if len(x) and x.arm.iloc[0] in arms], ignore_index=True)
    # blind id: sha256-derived, independent of which other cases exist (so the arms can be listed separately)
    cases["case"] = ["case_" + h(SEED + "case:" + r)[:6] for r in cases.rid]
    assert cases.case.is_unique
    kp = OUT / "cases_key.csv"
    if kp.exists():
        old = pd.read_csv(kp)
        cases = pd.concat([old[~old.arm.isin(arms)], cases], ignore_index=True)
    cases.sort_values("case").to_csv(kp, index=False)
    print(cases.groupby("arm").size().to_dict(), "R by class", rs.FIRE_SIZE_CLASS.value_counts().to_dict(),
          "R without standard label", int((~rs.std_label).sum()), flush=True)


# ------------------------------------------------------------------ evidence text
class Ev:
    def __init__(self):
        import geopandas as gpd
        from firewitness.caught.geo import PointIndex
        f = pd.read_parquet(RAW_ROOT / "derived_caught" / "firms_2018_2020.parquet")
        f["date"] = pd.to_datetime(f["date"]).dt.date
        self.firms = f.reset_index(drop=True)
        self.fidx = PointIndex(f.lat, f.lon, f.half_m, f.date, f.date)
        hm = pd.read_parquet(RAW_ROOT / "derived_caught" / "hms_fire_2018_2020.parquet")
        hm = hm[hm.witness.isin(["GOES", "AVHRR", "HMS_ANALYST"])].reset_index(drop=True)
        self.hms = hm
        self.hidx = PointIndex(hm.lat, hm.lon, hm.half_m, hm.date, hm.date)
        rel = pd.read_parquet(REL.format(y=2018), columns=["FOD_ID", "LATITUDE", "LONGITUDE", "t0", "t1",
                                                              "FIRE_SIZE", "FIRE_SIZE_CLASS"])
        rel = pd.concat([rel] + [pd.read_parquet(REL.format(y=y), columns=rel.columns.tolist()) for y in (2019, 2020)],
                        ignore_index=True)
        rel["d"] = pd.to_datetime(rel.t0).dt.date + timedelta(days=1)
        self.fod = rel
        self.fodidx = PointIndex(rel.LATITUDE, rel.LONGITUDE, np.zeros(len(rel)), rel.d, rel.d)
        self.per = gpd.read_parquet(RAW_ROOT / "derived_caught" / "perimeters_2018_2020.parquet")
        self.mtbs = gpd.read_parquet(RAW_ROOT / "derived_caught" / "mtbs_perims.parquet")

    def text(self, c) -> tuple[str, dict]:
        from shapely.geometry import Point
        from firewitness.caught.geo import haversine_m
        from firewitness.caught.landcover import lc_class
        t0, t1 = pd.Timestamp(c.t0).date(), pd.Timestamp(c.t1).date()
        lat, lon, r = float(c.LATITUDE), float(c.LONGITUDE), float(c.r_m)
        L = [f"{c.case}   window {t0} to {t1} ({(t1 - t0).days} d)   disc radius {r:,.0f} m",
             f"WorldCover at centre: {WC.get(lc_class(lat, lon), '?')}",
             f"witness set that made this case verified: {c.witnesses}", ""]
        facts = {}
        ix = self.fidx.query(lat, lon, r, t0, t1)
        L.append(f"FIRMS MODIS/VIIRS in disc and window: {len(ix)}")
        for i in ix[:8]:
            q = self.firms.iloc[int(i)]
            L.append(f"  {q.witness} {q.acq_dt:%Y-%m-%d %H:%M}Z conf {q.confidence} FRP {q.frp} type {q.get('type', '?')}")
        cx = self.fidx.query(lat, lon, 5000.0, t0 - timedelta(days=3), t1 + timedelta(days=3))
        L.append(f"FIRMS within 5 km, window +-3 d (context): {len(cx)}")
        near = self.fidx.query(lat, lon, 1000.0, date(t0.year - 1, 1, 1), date(t1.year + 1, 12, 31))
        q = self.firms.iloc[near]
        other = q[(q.date < t0) | (q.date > t1)]
        nd = other.date.nunique()
        types = sorted(set(self.firms.iloc[np.r_[ix, cx]]["type"].dropna().astype(int))) if "type" in self.firms else []
        L.append(f"FIRMS within 1 km of centre on other days (same/adjacent years): {nd} distinct days; "
                 f"FIRMS type values seen: {types or 'none'}")
        facts.update(firms_in=len(ix), firms_ctx=len(cx), static_days=int(nd), firms_types=types)
        hx = self.hidx.query(lat, lon, r, t0, t1)
        L.append(f"HMS GOES/AVHRR/analyst points in disc and window: {len(hx)}")
        for i in hx[:6]:
            q = self.hms.iloc[int(i)]
            L.append(f"  {q.witness} {q.date} {q.hhmm} {q.sat}")
        ev = json.loads(c.evidence) if isinstance(c.evidence, str) else []
        sm = [e for e in ev if e.get("witness") == "HMS_SMOKE"]
        L.append(f"HMS smoke attributed to the disc: {len(sm)}" + (f" ({sm[0]['d0']}, {sm[0].get('area_km2')} km2)" if sm else ""))
        hot = [e for e in ev if e.get("witness") in ("S2_AF", "LANDSAT_AF")]
        L.append(f"Sentinel-2/Landsat short-wave hot spots: {len(hot)}" + (f" ({', '.join(e['witness'] + ' ' + e['d0'] for e in hot[:3])})" if hot else ""))
        L.append("")
        fx = self.fodidx.query(lat, lon, 10_000.0, t0 - timedelta(days=30), t1 + timedelta(days=30))
        fq = self.fod.iloc[fx]
        if pd.notna(c.own_fod):
            fq = fq[fq.FOD_ID != int(c.own_fod)]
        L.append(f"FPA FOD records within 10 km, window +-30 d (case's own record excluded): {len(fq)}")
        for q in fq.head(5).itertuples():
            dkm = haversine_m(lat, lon, q.LATITUDE, q.LONGITUDE) / 1000
            L.append(f"  {q.d} class {q.FIRE_SIZE_CLASS} {q.FIRE_SIZE} ac at {dkm:.1f} km")
        facts["fod_10km"] = len(fq)
        from pyproj import Transformer
        from shapely.ops import transform
        from firewitness.caught.standard import local_crs
        tr = Transformer.from_crs("EPSG:4326", local_crs(lat, lon), always_xy=True).transform
        disc = Point(0, 0).buffer(r, 64)
        a, b = pd.Timestamp(t0 - timedelta(days=30)), pd.Timestamp(t1 + timedelta(days=30))
        cand = self.per.iloc[self.per.sindex.query(Point(lon, lat).buffer(r / 111_000 * 2 + 0.01))]
        hits = []
        for q in cand.itertuples():
            d0 = q.d0 if pd.notna(q.d0) else (q.d1 if pd.notna(q.d1) else pd.Timestamp(f"{int(q.year)}-01-01") if pd.notna(q.year) else None)
            d1 = q.d1 if pd.notna(q.d1) else (pd.Timestamp(f"{int(q.year)}-12-31") if pd.notna(q.year) else None)
            if d0 is None or d1 is None or d0 > b or d1 < a:
                continue
            if transform(tr, q.geometry).intersects(disc):
                hits.append(f"  {q.source} {q.kind} '{q.name}' {q.area_ac} ac dates {str(q.d0)[:10]} to {str(q.d1)[:10]}")
        mc = self.mtbs.iloc[self.mtbs.sindex.query(Point(lon, lat).buffer(r / 111_000 * 2 + 0.01))]
        for q in mc.itertuples():
            if a.date() - timedelta(days=1) <= q.ig_date <= b.date() and transform(tr, q.geometry).intersects(disc):
                hits.append(f"  MTBS {q.Incid_Type} '{q.Incid_Name}' ignition {q.ig_date}")
        L.append(f"Agency polygons meeting the disc, window +-30 d (NIFC history, WFIGS, FRAP, FRAP Rx, FACTS broadcast burns, MTBS): {len(hits)}")
        L += hits[:6]
        facts["agency_polys"] = len(hits)
        facts["agency_detail"] = " | ".join(x.strip() for x in hits)
        fa, st = facts_all(lat, lon, r, t0 - timedelta(days=30), t1 + timedelta(days=30), tr, disc)
        facts["facts_status"] = st
        facts["facts_all"] = " | ".join(fa)
        L.append(f"FACTS hazardous-fuel activities (all kinds) meeting the disc, completed in window +-30 d: "
                 + (f"{len(fa)}" if st == "ok" else "QUERY FAILED"))
        L += ["  " + x for x in fa[:4]]
        return "\n".join(L), facts


FACTS_URL = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_HazardousFuelsTreatments_01/MapServer/15/query"


def facts_all(lat, lon, r, a, b, tr, disc):
    """All FACTS hazardous-fuel activities whose polygon meets the disc and that were completed in [a, b]."""
    import requests
    from shapely.geometry import shape
    from shapely.ops import transform
    d = (r + 100) / 111_000.0
    dl = d / max(math.cos(math.radians(lat)), 0.05)
    q = {"where": f"date_completed >= DATE '{a}' AND date_completed <= DATE '{b}'",
         "geometry": f"{lon - dl},{lat - d},{lon + dl},{lat + d}", "geometryType": "esriGeometryEnvelope",
         "inSR": "4326", "spatialRel": "esriSpatialRelIntersects", "outSR": "4326", "f": "geojson",
         "outFields": "activity,date_completed,gis_acres,treatment_name", "returnGeometry": "true"}
    for k in range(3):
        try:
            js = requests.get(FACTS_URL, params=q, timeout=180).json()
            if "error" in js:
                raise RuntimeError(str(js["error"])[:200])
            out = []
            for f in js.get("features", []):
                try:
                    if not transform(tr, shape(f["geometry"])).intersects(disc):
                        continue
                except Exception:
                    pass
                p = f["properties"]
                dc = pd.to_datetime(p.get("date_completed"), unit="ms", errors="coerce")
                out.append(f"{p.get('activity')} completed {str(dc)[:10]} {p.get('gis_acres')} ac '{p.get('treatment_name')}'")
            return out, "ok"
        except Exception as e:
            err = e
    return [], f"failed {type(err).__name__}"


# ------------------------------------------------------------------ images
def _s2_pair(c, scar):
    """(pre_item, post_item, note) by the rubric's scene rule."""
    from firewitness.caught import scar as S
    lon, lat = float(c.LONGITUDE), float(c.LATITUDE)
    t0, t1 = pd.Timestamp(c.t0).date(), pd.Timestamp(c.t1).date()
    if isinstance(c.scar_sensor, str) and c.scar_sensor == "s2" and isinstance(c.scar_pre, str):
        dp, dq = date.fromisoformat(c.scar_pre[:10]), date.fromisoformat(c.scar_post[:10])
        pre = [i for i in S.search(S.S2.collection, lon, lat, dp, dp) if S.item_date(i) == dp]
        post = [i for i in S.search(S.S2.collection, lon, lat, dq, dq) if S.item_date(i) == dq]
        return pre, post, f"scar finder's own pair ({dp} / {dq})"
    pre = sorted(S.search(S.S2.collection, lon, lat, t0 - timedelta(days=60), t0 - timedelta(days=1)),
                 key=lambda i: S.item_date(i), reverse=True)
    post = sorted(S.search(S.S2.collection, lon, lat, t1 + timedelta(days=1), t1 + timedelta(days=45)),
                  key=lambda i: S.item_date(i))
    return pre, post, "rule 6.1 pair (no Sentinel-2 scar item)"


def _first_clear(items, grid, disc, run, need=0.8, tries=12):
    from firewitness.caught import scar as S
    for it in items[:tries]:
        if S.S2.cloud(it) > 90 or S.S2.epsg(it) != grid.epsg:
            continue
        cl = S.S2.clear(it, grid, run, None)
        valid = cl[disc]
        frac = float(valid.mean()) if valid.size else 0.0
        if frac >= need:
            return it, frac
    return None, None


def render_one(c, ev: Ev):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from pyproj import Transformer
    from shapely import wkt
    from firewitness.caught import scar as S
    run = "audit_cases"
    lon, lat, r = float(c.LONGITUDE), float(c.LATITUDE), float(c.r_m)
    text, facts = ev.text(c)
    pre_l, post_l, note = _s2_pair(c, None)
    allitems = pre_l + post_l
    if not allitems:
        return text, facts, "no Sentinel-2 items"
    epsg = S.S2.epsg(allitems[0])
    # use the CRS of the pre item if any, else the post item
    tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    x, y = tr.transform(lon, lat)
    half = min(max(500.0, 2.5 * r), 10_000.0)
    grid = S.Grid(epsg, x, y, half, 20.0)
    disc = grid.dist() <= r
    pre, fp = _first_clear([i for i in pre_l if S.S2.epsg(i) == epsg], grid, disc, run, 0.0 if "own pair" in note else 0.8)
    post, fq = _first_clear([i for i in post_l if S.S2.epsg(i) == epsg], grid, disc, run, 0.0 if "own pair" in note else 0.8)
    import textwrap
    fig = plt.figure(figsize=(21, 11.5), dpi=80)
    wrapped = "\n".join(textwrap.fill(l, 72, subsequent_indent="    ") if l else "" for l in text.split("\n"))
    fig.text(0.635, 0.98, wrapped, va="top", ha="left", family="monospace", fontsize=9.5, wrap=False)
    status = "ok"
    if pre is None or post is None:
        fig.text(0.02, 0.5, f"NO CLEAR SENTINEL-2 PAIR ({note}; pre {'found' if pre else 'none'}, post {'found' if post else 'none'})",
                 fontsize=16, color="red")
        status = "no clear pair"
    else:
        def bands(it):
            off = S.S2.offset(it)
            g10 = S.Grid(grid.epsg, grid.cx, grid.cy, (grid.n // 2) * grid.res, grid.res / 2)
            g10.n, g10.bounds = grid.n * 2, grid.bounds
            r20 = lambda a: (S.read_asset(it, a, grid, "average", run).astype("f4") - off) / 1e4
            r10 = lambda a: ((S.read_asset(it, a, g10, "average", run).astype("f4") - off) / 1e4).reshape(grid.n, 2, grid.n, 2).mean(axis=(1, 3))
            return {"B04": r10("B04"), "B03": r10("B03"), "B02": r10("B02"), "B8A": r20("B8A"), "B12": r20("B12")}
        A, B = bands(pre), bands(post)
        tc = lambda d: np.clip(np.dstack([d["B04"], d["B03"], d["B02"]]) / 0.25, 0, 1) ** 0.8
        sw = lambda d: np.clip(np.dstack([d["B12"] / 0.45, d["B8A"] / 0.5, d["B04"] / 0.25]), 0, 1)
        nbr = lambda d: (d["B8A"] - d["B12"]) / np.maximum(d["B8A"] + d["B12"], 1e-6)
        dn = nbr(A) - nbr(B)
        ext = [-grid.n * 10 / 1000, grid.n * 10 / 1000, -grid.n * 10 / 1000, grid.n * 10 / 1000]
        th = np.linspace(0, 2 * np.pi, 200)
        outline = None
        if isinstance(c.label_wkt, str):
            g = wkt.loads(c.label_wkt)
            tl = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
            outline = []
            for poly in getattr(g, "geoms", [g]):
                if hasattr(poly, "exterior"):
                    xs, ys = tl.transform(*poly.exterior.xy)
                    outline.append(((np.asarray(xs) - x) / 1000, (np.asarray(ys) - y) / 1000))
        panels = [(tc(A), f"PRE true colour {S.item_date(pre)} (disc clear {fp:.0%})"),
                  (tc(B), f"POST true colour {S.item_date(post)} (disc clear {fq:.0%})"),
                  (None, "dNBR (pre - post); cyan = label geometry"),
                  (sw(A), "PRE SWIR false colour (B12, B8A, B04)"),
                  (sw(B), "POST SWIR false colour (B12, B8A, B04)")]
        for k, (img, title) in enumerate(panels):
            ax = fig.add_axes([0.01 + (k % 3) * 0.205, 0.52 - (k // 3) * 0.47, 0.2, 0.42])
            if img is None:
                im = ax.imshow(dn, cmap="RdYlGn_r", vmin=-0.3, vmax=0.6, extent=ext)
                if outline:
                    for xs, ys in outline:
                        ax.plot(xs, ys, color="cyan", lw=1.2)
                fig.colorbar(im, ax=ax, fraction=0.04)
            else:
                ax.imshow(img, extent=ext)
            ax.plot(r / 1000 * np.cos(th), r / 1000 * np.sin(th), color="yellow", lw=1.3)
            ax.set_title(title, fontsize=9)
            ax.tick_params(labelsize=7)
            ax.set_xlabel("km", fontsize=7)
        fig.text(0.42, 0.03, f"scene rule: {note}\nyellow circle = search disc", fontsize=9)
        facts.update(pre_date=str(S.item_date(pre)), post_date=str(S.item_date(post)), pre_clear=fp, post_clear=fq)
    fig.savefig(OUT / f"{c.case}.png")
    plt.close(fig)
    facts["note"] = note
    return text, facts, status


def stage_render(threads):
    cases = pd.read_csv(OUT / "cases_key.csv")
    ev = Ev()
    done = set()
    pub_p = OUT / "cases_public.jsonl"
    if pub_p.exists():
        done = {json.loads(l)["case"] for l in open(pub_p)}

    def one(c):
        if c.case in done:
            return None
        try:
            text, facts, status = render_one(c, ev)
        except Exception as e:
            text, facts, status = "", {}, f"FAILED {type(e).__name__}: {e}"[:300]
            traceback.print_exc()
        return {"case": c.case, "status": status, "text": text, **{k: v for k, v in facts.items()}}

    with ThreadPoolExecutor(threads) as ex, open(pub_p, "a") as f:
        for res in ex.map(one, list(cases.itertuples())):
            if res:
                f.write(json.dumps(res, default=str) + "\n")
                f.flush()
                print(res["case"], res["status"], flush=True)


if __name__ == "__main__":
    st = sys.argv[1]
    if st == "list":
        stage_list(tuple(sys.argv[2]) if len(sys.argv) > 2 else ("R", "P"))
    else:
        stage_render(int(sys.argv[2]) if len(sys.argv) > 2 else 4)

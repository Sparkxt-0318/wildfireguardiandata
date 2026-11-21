"""Release v0.1: label set (geometry, time interval, tier, evidence, floor), data card, checksums; scar pairs."""
from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from firewitness.core.hashing import sha256_file

from .run import heat_floors, run_dir

COLUMNS = ["rid", "FOD_ID", "STATE", "FIRE_YEAR", "FIRE_SIZE", "FIRE_SIZE_CLASS", "LATITUDE", "LONGITUDE", "r_loc_m", "r_m",
           "t0", "t1", "t1_source", "tier", "reason", "pixel_label", "label_t0", "label_t1", "std_label",
           "std_witnesses", "witnesses", "kinds", "pairs", "evidence", "scar_status", "scar_sensor", "scar_pre",
           "scar_post", "scar_threshold", "scar_floor_m2", "scar_clear_frac", "scar_area_ha", "fire_m2_disc",
           "no_fire_m2_disc", "unknown_m2_disc", "searched", "split", "geometry_wkt"]


def load_labels(tag: str, slice_name: str) -> pd.DataFrame:
    return pd.read_parquet(run_dir(f"{slice_name}_{tag}") / "records" / "labels.parquet")


def export(tag: str, slices, out: str) -> Path:
    import geopandas as gpd
    from shapely import wkt

    outd = Path(out)
    outd.mkdir(parents=True, exist_ok=True)
    frames = []
    for s in slices:
        d = load_labels(tag, s)
        d["slice"] = s
        frames.append(d)
    lab = pd.concat(frames, ignore_index=True).drop_duplicates("rid", keep="last")
    lab["FOD_ID"] = lab.rid.str[3:].astype("int64")
    hf = heat_floors(0)
    lab["heat_floors_m2"] = json.dumps(hf)
    cols = [c for c in COLUMNS if c in lab] + ["heat_floors_m2", "slice"]
    lab = lab[cols].copy()
    for c in ("t0", "t1"):
        lab[c] = lab[c].astype(str)
    g = gpd.GeoDataFrame(lab.drop(columns=["geometry_wkt"]), geometry=lab.geometry_wkt.map(wkt.loads), crs="EPSG:4326")
    pq = outd / "caught_labels_v0.1.parquet"
    g.to_parquet(pq)
    gj = outd / "caught_labels_v0.1.geojsonl.gz"
    with gzip.open(gj, "wt") as f:
        for feat in json.loads(g.to_json(drop_id=True))["features"]:
            f.write(json.dumps(feat) + "\n")
    card = outd / "DATA_CARD.md"
    card.write_text(data_card(g, tag, slices))
    sums = outd / "SHA256SUMS"
    files = sorted(p for p in outd.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    sums.write_text("".join(f"{sha256_file(p)}  {p.relative_to(outd)}\n" for p in files))
    return outd


def data_card(g, tag, slices) -> str:
    vc = g.tier.value_counts().to_dict()
    nostd = g[~g.std_label.astype(bool)]
    return f"""# caught v0.1 label set: data card

Built {datetime.now(timezone.utc):%Y-%m-%d} from run tag `{tag}`, slices {', '.join(slices)}. Code: `firewitness caught`.

## What it is
One row per wildfire record in FPA FOD 7th edition (RDS-2013-0009.7) for the slices above: {len(g):,} records.
Every record is kept. Tier: verified {vc.get('verified', 0):,}; probable {vc.get('probable', 0):,};
record-only {vc.get('record-only', 0):,}. Records with no standard satellite label: {len(nostd):,}, of which
verified {int((nostd.tier == 'verified').sum()):,} and probable {int((nostd.tier == 'probable').sum()):,}.

## Fields
`geometry`: the pixel label (scar components and agreeing heat-pixel footprints, clipped to the search disc) for
verified and probable fires with a pixel label; otherwise the search disc (honest radius `r_m` = location
uncertainty `r_loc_m` + radius of the recorded area). `t0`, `t1`: the record's window; `label_t0`, `label_t1`: the
interval the agreeing evidence allows. `tier`, `reason` (record-only: below_floor, no_clear_look,
location_too_uncertain, clear_look_nothing_found). `evidence`: JSON list of every agreeing item (witness, kind,
dates, details). `pairs`: agreeing independent kinds. `std_label`, `std_witnesses`: standard products (MODIS,
VIIRS S-NPP, VIIRS NOAA-20 active fire; MCD64A1; MTBS) in the window. Three states in the searched disc:
`fire_m2_disc`, `no_fire_m2_disc` (verified no fire above `scar_floor_m2` between `scar_pre` and `scar_post`),
`unknown_m2_disc`. `heat_floors_m2`: edge-of-scan flaming-area floors per heat sensor, day and night.

## How it was made
protocol/CAUGHT_PROTOCOL.md (fixed before results). No trained model writes a label. No smoothing, dilation,
filling or interpolation. Inputs: see results/CAUGHT_RESULTS.md (hashes) and the raw index.

## What it does not show
- FireCCI51 was not checked (host unreachable from the build network); a fire labelled only by FireCCI51 counts
  here as "no standard label".
- "Verified no fire" holds only above the stated floor and only for the scar look's interval.
- A verified label says two independent kinds of evidence agree with the record in place and time; it does not
  prove the record's area, cause or exact start.
- Location uncertainty is inferred from coordinate precision; FPA FOD records placed at a survey-section centroid
  with many decimals get a radius that is too small.

## Licence and sources
FPA FOD (USDA Forest Service, public domain); FIRMS (NASA, open); MCD64A1 (NASA LP DAAC); MTBS (USGS/USFS); HMS
(NOAA); Sentinel-2 (Copernicus, free and open); Landsat (USGS, public domain); ESA WorldCover (CC BY 4.0); agency
perimeters (NIFC, CAL FIRE, public). Labels: MIT, like the code.
"""


def scar_pairs(lab: pd.DataFrame, out: str, n: int = 40, seed: int = 0) -> Path:
    """Before/after RGB chips for verified Sentinel-2 scars (for the video tool, track 52)."""
    import numpy as np
    from PIL import Image
    from .scar import find_scar

    outd = Path(out) / "scar_pairs"
    outd.mkdir(parents=True, exist_ok=True)
    pick = lab[(lab.tier == "verified") & (lab.scar_status == "scar") & (lab.scar_sensor == "s2")]
    pick = pick.sample(n=min(n, len(pick)), random_state=seed)
    done = []
    for r in pick.itertuples():
        res = find_scar(r.LONGITUDE, r.LATITUDE, r.r_m, pd.Timestamp(r.t0).date(), pd.Timestamp(r.t1).date(),
                        r.FIRE_SIZE * 0.40468564, sensors=("s2",), run="pairs")
        a = getattr(res, "_arrays", None)
        if a is None:
            continue
        d = outd / r.rid
        d.mkdir(exist_ok=True)

        def rgb(b):
            v = np.clip(b["vis"] * 3.5, 0, 1)
            x = np.dstack([np.clip(b["swir2"] * 2.5, 0, 1), np.clip(b["nir"] * 2.0, 0, 1), v])
            return Image.fromarray((np.nan_to_num(x) * 255).astype("uint8"))

        rgb(a["pre"]).save(d / "pre.png")
        rgb(a["post"]).save(d / "post.png")
        dn = np.clip((np.nan_to_num(a["dnbr"]) + 0.2) / 0.8, 0, 1)
        img = np.dstack([dn, dn, dn])
        img[a["accepted"]] = [1, 0.2, 0]
        Image.fromarray((img * 255).astype("uint8")).save(d / "dnbr.png")
        Image.fromarray((a["accepted"] * 255).astype("uint8")).save(d / "mask.png")
        from pyproj import Transformer
        gb = a["grid"].bounds
        tr = Transformer.from_crs(f"EPSG:{a['grid'].epsg}", "EPSG:4326", always_xy=True).transform
        corners = [tr(x, y) for x, y in [(gb[0], gb[1]), (gb[2], gb[3]), (gb[0], gb[3]), (gb[2], gb[1])]]
        acc = [c for c in res.components if c["status"] == "accepted"]
        meta = {"rid": r.rid, "fire_name": getattr(r, "FIRE_NAME", None), "lon": r.LONGITUDE, "lat": r.LATITUDE,
                "pre_date": res.pre_date, "bounds_wgs84_approx": [min(c[0] for c in corners), min(c[1] for c in corners),
                                                                  max(c[0] for c in corners), max(c[1] for c in corners)],
                "method": "firewitness caught scar finder (dNBR, protocol section 6), Sentinel-2 L2A 20 m",
                "score_median_dnbr": max([c["median_dnbr"] for c in acc], default=None),
                "post_date": res.post_date, "tier": r.tier, "bands": "R=B12 G=B8A B=mean(B02,B03,B04), 20 m",
                "grid_epsg": a["grid"].epsg, "grid_bounds": a["grid"].bounds, "inputs": res.inputs,
                "scar_geometry": res.to_dict()["geometry"]}
        (d / "meta.json").write_text(json.dumps(meta, default=str, indent=1))
        done.append(r.rid)
    (outd / "INDEX.json").write_text(json.dumps(done))
    return outd


def states_table(run: str, labels: pd.DataFrame | None = None) -> "gpd.GeoDataFrame":
    """Three states per searched record disc: fire, no_fire (with floor), unknown; record-only discs as unknown."""
    import geopandas as gpd
    from pyproj import Transformer
    from shapely import wkt
    from shapely.geometry import Point, shape
    from shapely.ops import transform

    from .standard import local_crs

    rd = run_dir(run)
    lab = labels if labels is not None else pd.read_parquet(rd / "labels.parquet")
    unk = {}
    ck = rd / "scar.jsonl"
    if ck.exists():
        for line in ck.read_text().splitlines():
            j = json.loads(line)
            st = j.get("states") or {}
            unk[j["rid"]] = shape(st["unknown"]) if st.get("unknown") else None
    rows = []
    for r in lab.itertuples():
        if pd.isna(r.LATITUDE):
            continue
        tr = Transformer.from_crs("EPSG:4326", local_crs(r.LATITUDE, r.LONGITUDE), always_xy=True).transform
        inv = Transformer.from_crs(local_crs(r.LATITUDE, r.LONGITUDE), "EPSG:4326", always_xy=True).transform
        disc = Point(0, 0).buffer(r.r_m, 64)
        looked = isinstance(r.scar_pre, str) and r.scar_status in ("scar", "no_scar_clear", "rejected")
        fire = transform(tr, wkt.loads(r.geometry_wkt)).intersection(disc) if (r.tier != "record-only" and r.pixel_label) else None
        u = transform(tr, unk[r.rid]).intersection(disc) if looked and unk.get(r.rid) is not None else None
        base = {"rid": r.rid, "tier": r.tier, "std_label": bool(r.std_label)}
        if fire is not None and not fire.is_empty:
            rows.append({**base, "state": "fire", "t0": r.label_t0, "t1": r.label_t1, "floor_m2": None,
                         "geometry": transform(inv, fire)})
        if looked:
            nf = disc.difference(fire) if fire is not None else disc
            if u is not None and not u.is_empty:
                nf = nf.difference(u)
                rows.append({**base, "state": "unknown", "t0": r.scar_pre, "t1": r.scar_post, "floor_m2": None,
                             "geometry": transform(inv, u)})
            if not nf.is_empty:
                rows.append({**base, "state": "no_fire", "t0": r.scar_pre, "t1": r.scar_post,
                             "floor_m2": r.scar_floor_m2, "geometry": transform(inv, nf)})
        else:
            rest = disc.difference(fire) if fire is not None and not fire.is_empty else disc
            rows.append({**base, "state": "unknown", "t0": str(r.t0), "t1": str(r.t1), "floor_m2": None,
                         "geometry": transform(inv, rest)})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

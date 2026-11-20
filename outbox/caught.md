# outbox: caught

Messages from track caught. Format: `## <UTC time> TO <track|orchestrator>: <subject>` then the body.

## 2026-11-20T17:40Z TO records: scar module interface (firewitness.caught.scar), for missing perimeters
Code lands on main via PR from track/caught (first PR within a few hours). Interface, fixed now so you can code against it:

```python
from firewitness.caught.scar import find_scar, make_perimeter, ScarResult
r = make_perimeter(lon, lat, start, end, area_ha, search_radius_m=None, sensors=("s2", "landsat"))
r = find_scar(lon, lat, radius_m, start, end, area_ha=None, sensors=("s2", "landsat"))
# start, end: datetime.date (fire window). make_perimeter widens the window to sqrt(area)*2 + radius and keeps
# every component connected (8-neighbour, no dilation/filling) to the one nearest the point.
r.status        # "scar" | "no_scar_clear" | "no_clear_look" | "below_floor" | "rejected"
r.geometry      # shapely (Multi)Polygon, EPSG:4326, or None
r.area_ha, r.sensor ("s2"|"landsat"), r.pre_date, r.post_date, r.threshold (dNBR), r.floor_m2
r.clear_fraction (of the search disc), r.reject_reason, r.inputs  # [(item id, asset, sha256 of the window)]
r.to_dict()     # JSON-ready
```
Imagery: Planetary Computer STAC (sentinel-2-l2a, landsat-c2-l2), no key. Rules: protocol/CAUGHT_PROTOCOL.md section 6.

## 2026-11-20T18:02Z TO records: please add a `caught` extra to pyproject
`caught = ["numpy", "pandas", "pyarrow", "scipy", "pyproj", "shapely", "geopandas", "rasterio", "pystac-client", "planetary-computer", "requests"]`
Scar module is in PR from track/caught (docs/CAUGHT_SCAR_API.md has the interface); it needs this extra.

## 2026-11-20T18:02Z TO score: three-state labels format (track 54)
Release caught-v0.1 (GeoParquet + GeoJSON lines): one row per FPA FOD record; tier verified/probable/record-only; `geometry` = fire pixel label (or the honest disc for record-only); per searched disc: `fire_m2_disc`, `no_fire_m2_disc` (verified no fire, with `scar_floor_m2` and look interval `scar_pre`..`scar_post`), `unknown_m2_disc`, plus fire/unknown geometries. Full field list: docs/CAUGHT_SCAR_API.md. I will post here when the first file exists.

## 2026-11-20T18:02Z TO smoke: before/after scar pairs (track 52)
Format, coming with the S1 run: `release/caught_v0.1/scar_pairs/<rid>/{pre.png,post.png,dnbr.png,meta.json}` (RGB chips 10 m Sentinel-2, meta: lon, lat, pre/post dates, item ids, scar polygon in EPSG:4326, tier). I will post here when the first pairs exist.

## 2026-11-20T18:10Z TO smoke: scar before/after pair format (answer to your 17:55Z request)
Directory per fire: `scar_pairs/<rid>/` with
- `pre.png`, `post.png`: false-colour RGB (R=B12 SWIR2, G=B8A NIR, B=mean of B02,B03,B04), Sentinel-2 L2A 20 m grid, north up, same grid for both;
- `mask.png`: burn mask (255 = accepted scar pixel) on the same grid; `dnbr.png`: dNBR greyscale with the mask in orange;
- `meta.json`: rid (FPA FOD id), fire_name, lon/lat, pre_date, post_date, grid_epsg + grid_bounds (UTM, exact), bounds_wgs84_approx, scar_geometry (GeoJSON, EPSG:4326), method, score_median_dnbr, tier, inputs (item ids, sha256).
`scar_pairs/INDEX.json` lists the rids. First pairs: after the California 2020 run; I will post the path (release asset of caught-v0.1, and a small sample in results/caught/scar_pairs_sample/).

## 2026-11-20T18:40Z TO score: three-state table schema (answer to your 18:10Z request)
File (release caught-v0.1 and, once S1 is run, `results/caught/states_S1_sample.parquet` for a first look): `caught_states_v0.1.parquet` (GeoParquet, EPSG:4326), one row per (window, state):
- `rid` (FPA FOD record, FOD<FOD_ID>; placebo windows are not included), `state` in {fire, no_fire, unknown},
- `geometry`: polygon(s) inside the record's search disc (fire = verified/probable pixel label; no_fire = clear scar look minus fire; unknown = masked or no clear look; the three partition the disc),
- `t0`, `t1`: the interval the state holds for (fire: label interval; no_fire and unknown: the scar look's pre..post dates, or the record window if there was no look),
- `floor_m2`: for no_fire, the smallest burned area the look would have seen (protocol section 7); `tier` and `std_label` of the record.
Rasterise with any grid you like; cell lists can be produced on request at 20 m.

## 2026-11-20T19:14Z TO score, smoke, live: first samples on branch track/caught (commit a6196a6), dev data, formats final, numbers not
- score: `results/caught/states_S1_dev_sample.parquet` (three-state table: rid, state fire/no_fire/unknown, t0, t1, floor_m2, tier, std_label, geometry EPSG:4326).
- live: `results/caught/verified_S1_dev_sample.csv` (verified records: rid, lat/lon, radius, window, label interval, witnesses, agreeing pairs, label geometry).
- smoke: `results/caught/scar_pairs_sample_S1_dev/<rid>/` pre.png, post.png, mask.png, dnbr.png, meta.json (6 pairs).
Full S1 files follow once the rules are frozen (after the dev rounds); paths will be posted here.

## 2026-11-20T19:40Z TO live: verified fires years
My slices are 2018-2020 only (brief 50: CA 2020, US 2020, US 2018-2020), so no verified fire falls in your GOES-16+18 window (2023-01-10..2025-04-05). Columns you asked for are in `results/caught/verified_*.csv` (rid, LATITUDE, LONGITUDE, window t0/t1, label_t0/label_t1, witnesses = evidence kinds, tier = verdict). The pipeline can run a 2023-2024 slice later (FPA FOD 7th ed. reaches 2024) if time remains after my brief; I will say so here if I do.

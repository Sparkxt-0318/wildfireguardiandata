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

## 2026-11-20T23:57Z TO score, live: S1 (California 2020) full files on track/caught (ae19201), PR to main follows
- score: `results/caught/states_S1.parquet` (13,697 rows: fire 974, no_fire 3,981, unknown 8,742; schema as posted).
- live: `results/caught/verified_S1.csv` (378 verified records, CA 2020; columns rid, LATITUDE, LONGITUDE, r_m, t0, t1, label_t0, label_t1, FIRE_SIZE, FIRE_SIZE_CLASS, std_label, std_witnesses, witnesses, kinds, pairs, tier, geometry_wkt).
US 2020 (S2) is running (~7 h); US 2018-2020 (S3) after it. Final files go to release/caught-v0.1/.

## 2026-11-20T23:59Z TO smoke: S1 scar pairs (30 verified Sentinel-2 scars, California 2020) on track/caught (ff15f06), in PR #23
Path: `results/caught/scar_pairs_S1/scar_pairs/<rid>/` with pre.png, post.png, mask.png, dnbr.png, meta.json (same format as the sample); index: `results/caught/scar_pairs_S1/scar_pairs/INDEX.json`.

## 2026-11-21T01:08Z TO orchestrator: v0.2 received
Acknowledged. I start v0.2 after S2 and S3 are on main: protocol/CAUGHT_PROTOCOL_v0.2.md committed alone first (rules, new never-opened sealed set from a state and year not used so far), then the second scar sensor (Landsat 30 m beside Sentinel-2 20 m) and scar persistence on a second date, placebo limit 1 %, results as a dated v0.2 addition plus a machine-readable file. v0.1 rules and numbers stay untouched. Note: the container restarted twice tonight; S2 resumes from checkpoints (DECISIONS D-512).

## 2026-11-21T04:43Z TO orchestrator: fuel-type scar check done (before release)
results/CAUGHT_RESULTS.md, addition 2026-11-21T05:00Z (track/caught 7987c70, PR with S2): records ran my module (make_perimeter; scar.py at their 7ad17a7 = my frozen rules 530a3d5). Dev check: grass median 0.82, shrub 0.68, timber 0.46 (29 % below 0.2, Wilson 24.7-34.1; timber >= 300 acres 41 %, under-measures). (a) geometry = where a fire was found, not its burned area (data card, docs, results); (b) scar floor by fuel; (c) sealed recall by fuel re-tabulated (timber labelled 0.50 vs grass 0.76). No rule or result changed. Release after S2/S3 on main.

## 2026-11-21T04:57Z TO orchestrator: priorities acknowledged
Order kept: (1) S2 placebos finishing (~1.7 h), then S3 (~12-14 h at the current 2.5 windows/s; I will try more concurrency); (2) fuel-type check is done (addition 2026-11-21T05:00Z on track/caught), release after S2/S3 are on main; (3) v0.2 protocol drafted, committed alone once S3 is on main.

## 2026-11-21T15:40Z TO orchestrator: D-514 disclosure
Done in the data card (PR #43). S3 discs without a pixel label: 16 vertices (2.55 % less area than the circle). S1/S2: 256 vertices (0.01 %). No tier, count, recall or three-state area depends on them: matching and the states table use their own 256-vertex discs, and truth recall uses pixel labels only. The release is built from S3 alone (covers 2018-2020), so every released disc has 16 vertices, and export simplification would give 16 for S1/S2 too. The S3 section of CAUGHT_RESULTS.md will carry the same text.

## 2026-11-21T20:28Z TO live: verified fires 2018-2020
`results/caught/verified_S3_2018.csv`, `verified_S3_2019.csv`, `verified_S3_2020.csv` (PR #45; 13,793 verified records; columns rid, LATITUDE, LONGITUDE, t0, t1, label_t0, label_t1 (best interval), witnesses, kinds, tier, geometry_wkt). `verified_S3_2020.csv` equals `verified_S2.csv`.

## 2026-11-21T21:12Z TO orchestrator: release caught-v0.1 ready
PR #45 merged (main 8201f7d). Files under release/caught-v0.1/ (210 files, 313 MB, each under 100 MB; SHA256SUMS verified): caught_labels_v0.1_<year>.parquet (220,975 records: verified 13,793, probable 24,930, record-only 182,252), caught_states_v0.1_<year>.parquet (three states with intervals), scar_pairs/ (40), DATA_CARD.md, NOTES.md, heat_floors_m2.json. S3 headline 4,343; C1 verified 0.21 % passes; this track's 5 % probable guard fails at 5.30 % (reported, nothing re-tuned). No tag created.

## 2026-11-21T21:12Z TO score: final three-state table
release/caught-v0.1/caught_states_v0.1_<year>.parquet on main (GeoParquet, EPSG:4326). Columns: rid, tier, std_label, state (fire / no_fire / unknown), t0, t1 (interval of that state), floor_m2 (for no_fire: verified no fire above this area), geometry (simplified to about 3 m). Same schema as results/caught/states_S1.parquet, now for all US 2018-2020.

## 2026-11-21T21:12Z TO smoke: final scar pairs
release/caught-v0.1/scar_pairs/ on main: 40 verified Sentinel-2 scars from all US 2018-2020 (pre.png, post.png, mask.png, dnbr.png, meta.json per fire; INDEX.json). Same format as results/caught/scar_pairs_S1.

## 2026-11-21T21:12Z TO live: verified fires 2018-2020 on main
results/caught/verified_S3_2018.csv, verified_S3_2019.csv, verified_S3_2020.csv are on main (13,793 verified records).

## 2026-11-21T21:40Z TO orchestrator: release caught-v0.1 ready (PR #46)
Data card caveats 1-3 added (commit 06fcfa9; only release/caught-v0.1/DATA_CARD.md and its SHA256SUMS line; sums re-verified). They ride in PR #46 together with the v0.2 protocol, which is its own commit (49ff332) made before any v0.2 result, because both share the branch. One wording note: class A sealed recall is 0.04 in grass (n 73) and 0.05 in timber (n 88); shrub has only 3 class-A fires (0 caught), so the card says that instead of "every fuel". Release caught-v0.1 ready once #46 is merged.

## 2026-11-21T22:40Z TO orchestrator: v0.2 sealed set widened by protocol A1 (before opening)
Thanks for dispatching caught-v0.1. On the sealed set: the protocol's fallback (MN, then WI, then MI 2021) gave only 50 perimeters with no size class at n >= 30, so before any look I committed amendment A1 alone (a52a525, PR #47): all US WFIGS 2021 perimeters under 300 acres, capped at 1,500 by sha256 of the IRWIN id (decided by counts only). 795 qualify (A 211, B 385, C 129, D 70). Opened once at 22:23Z. The report will give C2 v0.2 on the 795 and, beside it, the same numbers for the protocol-as-written MN/WI/MI subset (small n, no gate). C1 v0.2 failure (1.80 %) stands; nothing re-tuned.

## 2026-11-22T01:26Z TO orchestrator: v0.2 results (PR #52); DONE v0.2 follows the merge
C1 v0.2 FAILS: v0.2 tier (any route) 1.80 % of searched S3 placebos (S1 2.47 %, S2 1.72 %); persistence is the cause (confirms 47 % of record scars and 34 % of placebo scars). Second sensor alone: 0.62 % (S2 0.53 %, S1 0.96 % with interval to 1.34 %), reported per route, not as a rule. C2 v0.2 on the sealed set (795): labelled recall above standard in B, C, D, not A; verified-only now above standard in B-D (any route +0.099 overall; second sensor only +0.058, 0.022-0.096; v0.1 was -0.047). Deviation D-518: the builder dropped the 3,061 WFIGS 2021 perimeters without an IRWIN id, so the sealed set run is the 795 with an id (not up to 1,500 of 3,855 as A1 meant); selection on id presence only, reported as is, not re-run. The 3,061 remain unopened if you want a further check.

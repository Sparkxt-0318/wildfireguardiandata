# inbox: smoke

Messages to track smoke. Newest at the bottom. Mark each item DONE in your outbox when acted on.

## FROM records (routed 2026-11-20T17:27Z) — 2026-11-20T17:40Z TO all: core on main at fe0052b
core/ is on main (standard library only). Summary (full text in docs/CORE_API.md):
- CLI: add `firewitness/<track>/cli.py` with `register(parser)` (+ optional `HELP`); found automatically, no shared file edited. `pip install -e ".[dev]"`; `python -m firewitness <track> <cmd>`.
- firewitness.core: keys (`load_keys`, `get_key`, `require_key` writes the key NAME to NEEDS.md, `redact`), hashing (`sha256_file`, `hash_inputs`), patches (`Patch`, `PatchSet`, `apply_patches`, `revert_patches`), evidence (`Witness`, `combine` -> yes/no/undecided, `fit_witnesses` unlabeled EM), placebo and cluster bootstrap, `load_region`.
- Key scan: `python scripts/check_keys.py` (CI runs it; `sh scripts/install_hooks.sh` for the pre-commit hook). Never commit a key value; keys.env stays outside the repo.
- Package data: region config at `firewitness/<track>/config/<region>.json` ships with the wheel.
- Shared root files (README, pyproject, CI): ask track 49 through outbox/records.md.

## FROM live (routed 2026-11-20T17:46Z) — 2026-11-20T17:40Z TO smoke: proposed format for the ten-fire export (frame series, pixel signal, detection times)
Proposal (reply in outbox/smoke.md if you need changes; I will keep to it unless you object):
Release asset `live_export_v0.1.tar.gz` and, in the repo, `results/live_export/<fire_id>/`:
- `fire.json`: fire_id, name, lat, lon, final_acres, discovery_utc (agency), satellites, ABI fixed-grid pixel (row, col) per satellite, box origin/size.
- `frames_<sat>_<band>.npz`: `t` (int64 seconds since epoch, frame start), `bt` (float32 [n_t, ny, nx] brightness temperature K for bands 7/14; reflectance factor for band 1), `cloud` (uint8 [n_t, ny, nx], ACM: 0 clear, 1 prob clear, 2 prob cloudy, 3 cloudy, 255 missing). Box is 32x32 pixels (2 km) centred on the fire pixel; band 1 is 64x64 at 1 km over the same area.
- `signal_<sat>.csv`: t_utc, bt7, bt14, dT, background_pred, z, cusum, cloud_flag, fdc_mask (per frame, at the fire pixel).
- `detections.csv`: method, sat, t_utc, note. Methods: agency_discovery, goes_fdc_first (per sat), viirs_first, modis_first, traceback_onset (+ interval lo/hi), traceback_distinguishable, live_detector_alert.
Times are UTC ISO 8601 with Z. Expected ready: after Part A runs (will post here).

## FROM caught (routed 2026-11-20T18:03Z) — 2026-11-20T18:02Z TO smoke: before/after scar pairs (track 52)
Format, coming with the S1 run: `release/caught_v0.1/scar_pairs/<rid>/{pre.png,post.png,dnbr.png,meta.json}` (RGB chips 10 m Sentinel-2, meta: lon, lat, pre/post dates, item ids, scar polygon in EPSG:4326, tier). I will post here when the first pairs exist.

## FROM orchestrator (2026-11-20T18:10Z) — merged so far
On main: #1 score, #2 records (core grouped-prior fitting, records tool 2). Before opening a PR, merge origin/main into your branch so DECISIONS.md appends do not conflict.

## FROM records (routed 2026-11-20T18:21Z) — 2026-11-20T18:21Z TO smoke: duplicate-collapse export format
`firewitness records link --export-examples N` (and results/collapse_examples/) will write one JSON file per example fire, schema:
{"example_id": str, "cluster_id": str (permanent fire id), "members": [{"source": "fpa_fod|ics209|mtbs|wfigs|wa_dnr|ok|ak", "record_id": str, "name": str|null, "date": "YYYY-MM-DD", "lat": float, "lon": float, "acres": float|null, "state": str}], "pairs": [{"a": record_id, "b": record_id, "probability": float, "outcome": "link|no_link|undecided", "witnesses": {"distance_km": ..., "days": ..., "size_ratio": ..., "name_similarity": ...}}], "merged": {"name","date","lat","lon","acres","state","n_sources"}, "raw_kept": same members list untouched}.
Per-state examples with 3 to 8 members each; first files land in results/collapse_examples/ within about 2 hours, with the same schema from the first file.

## FROM caught (routed 2026-11-20T18:21Z) — 2026-11-20T18:10Z TO smoke: scar before/after pair format (answer to your 17:55Z request)
Directory per fire: `scar_pairs/<rid>/` with
- `pre.png`, `post.png`: false-colour RGB (R=B12 SWIR2, G=B8A NIR, B=mean of B02,B03,B04), Sentinel-2 L2A 20 m grid, north up, same grid for both;
- `mask.png`: burn mask (255 = accepted scar pixel) on the same grid; `dnbr.png`: dNBR greyscale with the mask in orange;
- `meta.json`: rid (FPA FOD id), fire_name, lon/lat, pre_date, post_date, grid_epsg + grid_bounds (UTM, exact), bounds_wgs84_approx, scar_geometry (GeoJSON, EPSG:4326), method, score_median_dnbr, tier, inputs (item ids, sha256).
`scar_pairs/INDEX.json` lists the rids. First pairs: after the California 2020 run; I will post the path (release asset of caught-v0.1, and a small sample in results/caught/scar_pairs_sample/).

## FROM live (routed 2026-11-20T18:21Z) — 2026-11-20T18:19Z TO smoke: sample fire in the agreed format (branch track/live)
`results/live_export_sample/2023-ORWIF-230266/` on branch track/live (Bedrock fire, OR, 2023; both satellites; 2 MB). Includes fire.json name/final_acres and detections.csv with a UTC time per method (empty = not detected). Values are PRELIMINARY (Part A thresholds from 11 dev fires); the final ten fires come as release asset live_export_v0.1.tar.gz plus results/live_export/ once Part A/B are final. Boxes are 40x40 (not 32x32): 2 km bands centred on the site pixel; band 1 is 40x40 at 1 km over the central area. Code: firewitness/live/export.py.

## FROM records (routed 2026-11-20T19:29Z) — 2026-11-20T19:15Z TO smoke: collapse examples are on branch track/records
results/collapse_examples/*.json (12 files, schema in docs/RECORDS_EXPORT.md): one JSON per fire with members from fpa_fod, ics209plus and mtbs, the pairwise links with probabilities, the merged record and the raw records kept. `firewitness records link --export-examples N --out-examples DIR` makes more. They reach main with my next pull request (within about an hour); read them from the branch meanwhile.

## FROM caught (routed 2026-11-20T19:29Z) — 2026-11-20T19:14Z TO score, smoke, live: first samples on branch track/caught (commit a6196a6), dev data, formats final, numbers not
- score: `results/caught/states_S1_dev_sample.parquet` (three-state table: rid, state fire/no_fire/unknown, t0, t1, floor_m2, tier, std_label, geometry EPSG:4326).
- live: `results/caught/verified_S1_dev_sample.csv` (verified records: rid, lat/lon, radius, window, label interval, witnesses, agreeing pairs, label geometry).
- smoke: `results/caught/scar_pairs_sample_S1_dev/<rid>/` pre.png, post.png, mask.png, dnbr.png, meta.json (6 pairs).
Full S1 files follow once the rules are frozen (after the dev rounds); paths will be posted here.

## FROM orchestrator (2026-11-20T19:36Z) — how releases are made (DECISIONS D-010)
Cloud sessions cannot call the release API. Put your release files under release/smoke-v0.1/ (optional NOTES.md there), merge by PR, then write "TO orchestrator: release smoke-v0.1 ready" in your outbox. I dispatch .github/workflows/release.yml, which creates the GitHub release smoke-v0.1 with those files and a SHA256SUMS.txt. Do not create the tag v0.1 yourself: the umbrella v0.1 is cut by the orchestrator after all six tracks are DONE. Keep each file under 100 MB (git limit). Larger files go in a zip split under 100 MB, or are left out with the command that regenerates them.

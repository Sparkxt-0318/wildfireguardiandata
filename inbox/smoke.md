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

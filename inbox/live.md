# inbox: live

Messages to track live. Newest at the bottom. Mark each item DONE in your outbox when acted on.

## FROM records (routed 2026-11-20T17:27Z) — 2026-11-20T17:40Z TO all: core on main at fe0052b
core/ is on main (standard library only). Summary (full text in docs/CORE_API.md):
- CLI: add `firewitness/<track>/cli.py` with `register(parser)` (+ optional `HELP`); found automatically, no shared file edited. `pip install -e ".[dev]"`; `python -m firewitness <track> <cmd>`.
- firewitness.core: keys (`load_keys`, `get_key`, `require_key` writes the key NAME to NEEDS.md, `redact`), hashing (`sha256_file`, `hash_inputs`), patches (`Patch`, `PatchSet`, `apply_patches`, `revert_patches`), evidence (`Witness`, `combine` -> yes/no/undecided, `fit_witnesses` unlabeled EM), placebo and cluster bootstrap, `load_region`.
- Key scan: `python scripts/check_keys.py` (CI runs it; `sh scripts/install_hooks.sh` for the pre-commit hook). Never commit a key value; keys.env stays outside the repo.
- Package data: region config at `firewitness/<track>/config/<region>.json` ships with the wheel.
- Shared root files (README, pyproject, CI): ask track 49 through outbox/records.md.

## FROM smoke (routed 2026-11-20T18:03Z) — 2026-11-20T17:55:52Z TO live: export format accepted
Your proposed layout for the ten-fire export (fire.json, frames_<sat>_<band>.npz with t/bt/cloud, signal_<sat>.csv, detections.csv) is fine for the video renderer. Two additions I will use if present: fire.json "name" and "final_acres" for the caption, and in detections.csv a UTC time per method (empty = not detected). I will build the renderer against a small synthetic fixture in that format now; send a real fire directory under results/live_export/<fire_id>/ when you have one.

## FROM orchestrator (2026-11-20T18:10Z) — merged so far
On main: #1 score, #2 records (core grouped-prior fitting, records tool 2). Before opening a PR, merge origin/main into your branch so DECISIONS.md appends do not conflict.

## FROM records (routed 2026-11-20T18:21Z) — 2026-11-20T18:20Z TO live, caught: key scan false positive on GUIDs fixed
scripts/check_keys.py: the data.go.kr pattern now needs a letter beyond F, so upper-case hex GUIDs (IRWIN, WFIGS) pass. On track/records; merges to main with the next PR. Meanwhile your lower-casing workaround is fine.

## FROM orchestrator (2026-11-20T18:27Z) — PR #5 merged, relay dispatched
PR #5 merged (501fa98). I dispatched live-relay.yml on main once (trigger=manual) at 18:27Z. Watch the first run yourself and fix forward by PR if it fails; the D2 clock starts at the first committed record on live-log.

## FROM orchestrator (2026-11-20T18:41Z) — PR #6 merged, relay re-dispatched
PR #6 merged (f5bf891); live-relay.yml dispatched again on main at 18:41Z. Check that records land on live-log.

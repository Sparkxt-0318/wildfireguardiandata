# inbox: caught

Messages to track caught. Newest at the bottom. Mark each item DONE in your outbox when acted on.

## FROM records (routed 2026-11-20T17:27Z) — 2026-11-20T17:40Z TO all: core on main at fe0052b
core/ is on main (standard library only). Summary (full text in docs/CORE_API.md):
- CLI: add `firewitness/<track>/cli.py` with `register(parser)` (+ optional `HELP`); found automatically, no shared file edited. `pip install -e ".[dev]"`; `python -m firewitness <track> <cmd>`.
- firewitness.core: keys (`load_keys`, `get_key`, `require_key` writes the key NAME to NEEDS.md, `redact`), hashing (`sha256_file`, `hash_inputs`), patches (`Patch`, `PatchSet`, `apply_patches`, `revert_patches`), evidence (`Witness`, `combine` -> yes/no/undecided, `fit_witnesses` unlabeled EM), placebo and cluster bootstrap, `load_region`.
- Key scan: `python scripts/check_keys.py` (CI runs it; `sh scripts/install_hooks.sh` for the pre-commit hook). Never commit a key value; keys.env stays outside the repo.
- Package data: region config at `firewitness/<track>/config/<region>.json` ships with the wheel.
- Shared root files (README, pyproject, CI): ask track 49 through outbox/records.md.

## FROM smoke (routed 2026-11-20T18:03Z) — 2026-11-20T17:55:52Z TO caught: need the scar before-and-after pair format for the video tool
Please tell me (inbox/smoke.md) the export for before-and-after scar pairs: for each fire a directory with before and after images (GeoTIFF or PNG with a world file / bounds), the fire polygon(s) or burn mask (GeoJSON or raster), fire name, dates of the before and after scenes, and which method produced the scar mask (with a score if any). A minimum is fine: two RGB images, one mask PNG and a small JSON. I render side-by-side with a swipe and the mask outline.

## FROM orchestrator (2026-11-20T18:10Z) — PR #3 conflict resolved on your branch
PR #3 conflicted with main only in DECISIONS.md (both tracks appended). I pushed a merge commit 255bc92 to track/caught that keeps both sections. Run `git pull origin track/caught` before your next push. I merge PR #3 once CI passes on 255bc92. To avoid this next time: before opening a PR, merge origin/main into your branch.

## FROM orchestrator (2026-11-20T18:10Z) — merged so far
On main: #1 score, #2 records (core grouped-prior fitting, records tool 2). Before opening a PR, merge origin/main into your branch so DECISIONS.md appends do not conflict.

## FROM records (routed 2026-11-20T18:21Z) — 2026-11-20T18:20Z TO live, caught: key scan false positive on GUIDs fixed
scripts/check_keys.py: the data.go.kr pattern now needs a letter beyond F, so upper-case hex GUIDs (IRWIN, WFIGS) pass. On track/records; merges to main with the next PR. Meanwhile your lower-casing workaround is fine.

## FROM records (routed 2026-11-20T18:21Z) — 2026-11-20T18:20Z TO caught: `caught` extra added
pyproject.toml now has the `caught` extra exactly as you listed it (on track/records, in the next PR).

## FROM score (routed 2026-11-20T18:21Z) — 2026-11-20T18:10:33Z TO caught: label format for the score adapter
Track score needs the three-state label table (fire / verified no fire / unknown, with an optional time interval per fire label) to add an adapter. Interface wanted: per fire a raster or cell list with those states and dates. Tell me the file path and schema when merged; until then I use WildfireSpreadTS masks.

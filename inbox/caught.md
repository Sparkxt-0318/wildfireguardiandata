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

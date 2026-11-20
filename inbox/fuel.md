# inbox: fuel

Messages to track fuel. Newest at the bottom. Mark each item DONE in your outbox when acted on.

## FROM records (routed 2026-11-20T17:27Z) — 2026-11-20T17:40Z TO all: core on main at fe0052b
core/ is on main (standard library only). Summary (full text in docs/CORE_API.md):
- CLI: add `firewitness/<track>/cli.py` with `register(parser)` (+ optional `HELP`); found automatically, no shared file edited. `pip install -e ".[dev]"`; `python -m firewitness <track> <cmd>`.
- firewitness.core: keys (`load_keys`, `get_key`, `require_key` writes the key NAME to NEEDS.md, `redact`), hashing (`sha256_file`, `hash_inputs`), patches (`Patch`, `PatchSet`, `apply_patches`, `revert_patches`), evidence (`Witness`, `combine` -> yes/no/undecided, `fit_witnesses` unlabeled EM), placebo and cluster bootstrap, `load_region`.
- Key scan: `python scripts/check_keys.py` (CI runs it; `sh scripts/install_hooks.sh` for the pre-commit hook). Never commit a key value; keys.env stays outside the repo.
- Package data: region config at `firewitness/<track>/config/<region>.json` ships with the wheel.
- Shared root files (README, pyproject, CI): ask track 49 through outbox/records.md.

## FROM orchestrator (2026-11-20T18:10Z) — merged so far
On main: #1 score, #2 records (core grouped-prior fitting, records tool 2). Before opening a PR, merge origin/main into your branch so DECISIONS.md appends do not conflict.

## FROM orchestrator (2026-11-20T18:58Z) — PR #7 held for one change
PR #7 is in scope except for file placement: 20 result files sit at the top of results/ with generic names (results/dev_r1_M22.json ... results/sealed_opened.json, results/RULES_FROZEN.json, results/F3_dev_check.json). Results files are never changed after merge, so move them now, before merge, to results/fuel/ (keep results/ROUNDS_fuel.md and results/FUEL_RESULTS.md where they are), update any code paths, push, and I merge once CI is green. I removed the Claude footer from the PR body; leave it off.
Depth note for your DONE check later: 12 improvement rounds and the sealed opening within the first 90 minutes is fast. Make sure ROUNDS_fuel.md records, for each round, the wrong verdicts you read, the one cause named, the one rule changed, and the before/after F1 and F2, and that sealed_opened.json was written exactly once after the rules were frozen (commit order will be audited).

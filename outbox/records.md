# outbox: records

Messages from track records. Format: `## <UTC time> TO <track|orchestrator>: <subject>` then the body.

## 2026-11-20T17:40Z TO all: core on main at fe0052b
core/ is on main (standard library only). Summary (full text in docs/CORE_API.md):
- CLI: add `firewitness/<track>/cli.py` with `register(parser)` (+ optional `HELP`); found automatically, no shared file edited. `pip install -e ".[dev]"`; `python -m firewitness <track> <cmd>`.
- firewitness.core: keys (`load_keys`, `get_key`, `require_key` writes the key NAME to NEEDS.md, `redact`), hashing (`sha256_file`, `hash_inputs`), patches (`Patch`, `PatchSet`, `apply_patches`, `revert_patches`), evidence (`Witness`, `combine` -> yes/no/undecided, `fit_witnesses` unlabeled EM), placebo and cluster bootstrap, `load_region`.
- Key scan: `python scripts/check_keys.py` (CI runs it; `sh scripts/install_hooks.sh` for the pre-commit hook). Never commit a key value; keys.env stays outside the repo.
- Package data: region config at `firewitness/<track>/config/<region>.json` ships with the wheel.
- Shared root files (README, pyproject, CI): ask track 49 through outbox/records.md.

## 2026-11-20T18:20Z TO live, caught: key scan false positive on GUIDs fixed
scripts/check_keys.py: the data.go.kr pattern now needs a letter beyond F, so upper-case hex GUIDs (IRWIN, WFIGS) pass. On track/records; merges to main with the next PR. Meanwhile your lower-casing workaround is fine.

## 2026-11-20T18:20Z TO caught: `caught` extra added
pyproject.toml now has the `caught` extra exactly as you listed it (on track/records, in the next PR).

## 2026-11-20T18:21Z TO smoke: duplicate-collapse export format
`firewitness records link --export-examples N` (and results/collapse_examples/) will write one JSON file per example fire, schema:
{"example_id": str, "cluster_id": str (permanent fire id), "members": [{"source": "fpa_fod|ics209|mtbs|wfigs|wa_dnr|ok|ak", "record_id": str, "name": str|null, "date": "YYYY-MM-DD", "lat": float, "lon": float, "acres": float|null, "state": str}], "pairs": [{"a": record_id, "b": record_id, "probability": float, "outcome": "link|no_link|undecided", "witnesses": {"distance_km": ..., "days": ..., "size_ratio": ..., "name_similarity": ...}}], "merged": {"name","date","lat","lon","acres","state","n_sources"}, "raw_kept": same members list untouched}.
Per-state examples with 3 to 8 members each; first files land in results/collapse_examples/ within about 2 hours, with the same schema from the first file.

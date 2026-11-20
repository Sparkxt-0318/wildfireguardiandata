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

## 2026-11-20T19:15Z TO smoke: collapse examples are on branch track/records
results/collapse_examples/*.json (12 files, schema in docs/RECORDS_EXPORT.md): one JSON per fire with members from fpa_fod, ics209plus and mtbs, the pairwise links with probabilities, the merged record and the raw records kept. `firewitness records link --export-examples N --out-examples DIR` makes more. They reach main with my next pull request (within about an hour); read them from the branch meanwhile.

## 2026-11-20T19:32Z TO orchestrator: PR #10 (records, v0.1 content) ready for review and merge
PR #10 into main: tools 1-5, gates, results/RECORDS_RESULTS.md, overlay files in release/v0.1, collapse examples (smoke is waiting on them). CI should pass (78 tests, key scan). After the merge I will tag v0.1; a GitHub release object cannot be created with the tools I have (no release API, no gh), so the overlay files are committed under release/v0.1 and the tag marks them.

## 2026-11-20T20:06Z TO orchestrator: release folder renamed
release/v0.1 is now release/records-v0.1 on track/records (head pushed), references updated. No tag pushed. Contents: patches_us.jsonl.gz, crosswalk_us.parquet, fires_us.parquet, complex_parents_us.parquet, run_summary_us.json; data card docs/DATA_CARD_records_us.md.

## 2026-11-20T20:30Z TO orchestrator: PR #13 (small follow-up) and DONE status
#10 is merged, thank you. PR #13 adds only results/data/coverage/satellite_only_* and a coverage note in results/RECORDS_RESULTS.md (results/ only). All brief items are done; the open limits are stated in results/RECORDS_RESULTS.md (FIRED not obtained, so the ICS-209-PLUS to FIRED link does not meet R1; FOD to ICS recall 0.80; time repair recall low). I will write DONE with the commit hash on the board when #13 is merged.

## 2026-11-20T20:42Z TO orchestrator: PR #13 changed as asked
results/RECORDS_RESULTS.md on track/records (5d50494) now differs from main by two added lines only: the coverage line is restored exactly as on main, and a dated "Addition 2026-11-20T20:40Z" paragraph follows it. The rest of #13 is new files under results/data/coverage/. Ready to merge when CI is green.

## 2026-11-20T20:56Z TO orchestrator: DONE 200c186
PR #13 merged. Brief 49 is complete; DONE with main commit 200c186 written on board/records.md. Release folder release/records-v0.1 is on main for you to publish; no tag pushed by me.

## 2026-11-20T21:25Z TO orchestrator: depth-check items 1, 3, 4, 5, 6 in PR #14; item 2 running
PR #14: gridded weather check against gridMET (n, counts, Wilson intervals, planted recovery 300/300), Wilson intervals for the rate-only rows, failures listed as you asked, sealed-test entry in ROUNDS (appended), importorskip, DECISIONS lines (FIRMS key, append-only). Existing lines untouched. Item 2: protocol amendment pre-registers a 200-fire random sample (seed 1, 2016 to 2023, large fires with no perimeter); the imagery job runs in two shards (about 46 done, roughly 2 hours more); results go in a later PR as a dated addition. I do not re-tune anything.

## 2026-11-20T22:40Z TO orchestrator: depth-check item 2 done, PR #18
PR #18: the pre-registered 200-fire perimeter sample is complete (seed 1, 2016 to 2023, from 677 large fires with no perimeter). Scar found for 127 of 200; created and consistent with the recorded area 35 (17.5%, Wilson 12.9% to 23.4%); created and disagreeing 92 (all with scar area under 0.2 of the recorded area; median ratio 0.005); no scar although the look was clear 31; no clear look 36; rejected 6. Dated addition at the end of results/RECORDS_RESULTS.md, files in results/data/coverage/prereg/. All six depth-check items are now in PRs #14 (merged) and #18.

## 2026-11-20T22:40Z TO orchestrator: DONE again, main 7b1711e
PR #18 merged; all six depth-check items are on main (weather vs gridMET and the interval/failure/ROUNDS/test/DECISIONS additions in #14; the pre-registered 200-fire perimeter sample in #18). Board section rewritten with DONE 7b1711e and the open limits as reported.

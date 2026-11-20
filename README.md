# wildfireguardiandata

**firewitness**: tools that fix wildfire data instead of measuring how broken it is. Python 3.10+, MIT licence.

Fire records are split across agencies with no shared schema, and have been cleaned by hand, once per dataset. `firewitness records` is a reusable tool for the same job: it cleans values, repairs locations and times only when independent evidence agrees, finds duplicates, links records across sources, gives every real fire one permanent ID, and publishes where coverage is missing. Every change is a *patch* (record, field, old, new, rule, evidence, confidence); nothing is smoothed or overwritten, and any run can be reverted byte for byte.

```
pip install -e ".[dev,records]"
# other tracks: pip install -e ".[caught]" (imagery scar module), ".[live]", ".[smoke]" (smoke edge and video clips)
firewitness --help
firewitness records clean --input table.csv --table generic --out out/      # patches + clean table
firewitness records revert --patches out/patches.jsonl --clean out/clean.csv --out back.csv --columns out/input_columns.json
firewitness records link --task fod_mtbs        # links re-derived with the published links hidden
firewitness records ids  --out out/             # permanent IDs + crosswalk for the US run
firewitness records report --out out/           # coverage flags per state, year, agency
```

Region: every country-specific value is in `firewitness/records/config/<region>.json` (the run so far is `us`; a Korea run changes only that file).

## Results

See `results/RECORDS_RESULTS.md` (headline numbers with n, interval, source file and what each does not show), `results/ROUNDS_records.md` (improvement rounds), `protocol/RECORDS_PROTOCOL.md` (gates, baselines, splits, amendment log), `results/DATA_PULLS.md` (what was and was not obtained) and `docs/PRIOR_ART.md`.

## Layout

| Folder | Track | Branch |
|---|---|---|
| `firewitness/core/`, `firewitness/records/`, README, packaging, CI | records | `track/records` |
| `firewitness/caught/` | caught | `track/caught` |
| `firewitness/live/` | live | `track/live` |
| `firewitness/smoke/`, `firewitness/video/`, `clips/` | smoke | `track/smoke` |
| `firewitness/fuel/` | fuel | `track/fuel` |
| `firewitness/score/` | score | `track/score` |

Shared: `protocol/`, `results/`, `docs/`, `tests/`. A track adds commands by creating `firewitness/<track>/cli.py` (see `docs/CORE_API.md`); no shared file is edited.

## Keys

Keys live in `keys.env` outside the repository (see `firewitness.core.keys`). `scripts/check_keys.py` runs in pre-commit (`sh scripts/install_hooks.sh`) and in CI and fails if any key value or token shape is in a tracked file.

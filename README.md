# wildfireguardiandata

**firewitness**: tools that fix wildfire data instead of measuring how broken it is. Python 3.10+, MIT licence.

Fire records are split across agencies with no shared schema. `firewitness records` cleans them, links them across
sources, gives every real fire one permanent ID, and publishes where coverage is missing. Every change is a *patch*
(record, field, old, new, rule, evidence, confidence); nothing is smoothed or overwritten, and any run can be reverted.

```
pip install -e ".[dev,records]"
firewitness --help
firewitness records clean | link | ids | revert | report
```

Status: v0.1 in progress. See `results/` for gates and numbers, `protocol/` for what was fixed before results,
`docs/CORE_API.md` for the shared building blocks.

## Layout

| Folder | Track | Branch |
|---|---|---|
| `firewitness/core/`, `firewitness/records/`, README, packaging, CI | records | `track/records` |
| `firewitness/caught/` | caught | `track/caught` |
| `firewitness/live/` | live | `track/live` |
| `firewitness/smoke/`, `firewitness/video/`, `clips/` | smoke | `track/smoke` |
| `firewitness/fuel/` | fuel | `track/fuel` |
| `firewitness/score/` | score | `track/score` |

Shared: `protocol/`, `results/`, `docs/`, `tests/`. Each track writes only its own files and merges by pull request.
A track adds commands by creating `firewitness/<track>/cli.py` (see `docs/CORE_API.md`); no shared file is edited.

## Keys

Keys live in `keys.env` outside the repository (see `firewitness.core.keys`). `scripts/check_keys.py` runs in
pre-commit (`sh scripts/install_hooks.sh`) and in CI and fails if any key value or token shape is in a tracked file.

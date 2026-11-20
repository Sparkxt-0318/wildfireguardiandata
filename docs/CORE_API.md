# firewitness core API (track 49)

Standard library only. `from firewitness.core import ...`

## Command line: no shared file to edit
`firewitness <track> <command>`. A track adds commands by creating `firewitness/<track>/cli.py`:

```python
HELP = "one line shown in `firewitness --help`"
def register(parser):            # parser = this track's own argparse parser
    sub = parser.add_subparsers(dest="cmd")
    sp = sub.add_parser("mycommand", help="...")
    sp.add_argument("--region", default="us")
    sp.set_defaults(func=run)    # run(args) -> int exit code
```
Discovery is automatic (`firewitness/cli.py`); a track whose cli fails to import is reported and skipped.
`python -m firewitness ...` works too. Install: `pip install -e ".[dev]"` (extras: `records`).
Package data: put region config at `firewitness/<track>/config/<region>.json` (included in the wheel).

## keys
`load_keys(path=None) -> dict`, `get_key(name)`, `require_key(name, needs_file=None, track="records")`
(raises `MissingKey` and, if `needs_file` is given, adds the NAME to NEEDS.md), `redact(text)`.
Search order: `FIREWITNESS_KEYS`, `/home/user/wildfire 3 (1)/keys/keys.env`; environment variables override.
Never print a value. `scripts/check_keys.py` (pre-commit via `sh scripts/install_hooks.sh`, and CI) fails the
commit if any keys.env value or a known token shape appears in a tracked file.

## hashing
`sha256_file(path)`, `sha256_bytes(b)`, `hash_inputs([paths]) -> {path: {sha256, bytes}}`, `canonical_json(obj)`, `hash_obj(obj)`.
Record input hashes in every results file.

## patches (the only way to change data)
`Patch(record_id, field, old, new, rule, evidence, confidence)`; `PatchSet(patches, input_sha256, tool, meta)` with
`.add(patch)`, `.write(path)` / `PatchSet.read(path)` (JSON lines, hash-chained; tampering raises).
`apply_patches(records, patches, id_field=None, strict=True)` returns a new dict, input untouched; strict means
`patch.old` must equal the current value. `revert_patches(...)` is the exact inverse. `missing()` marks a field
that did not exist (insert) or is removed. `snapshot_input` / `verify_input_unchanged` prove inputs are never rewritten.

## evidence combination
`Witness(name, m, u)`: P(agree | true), P(agree | false). `combine(witnesses, observations, prior, hi=0.95, lo=0.05)`
returns `Verdict(prob, decision in {"yes","no","undecided"}, log_odds, contributions)`; an observation of `None`
is "no information". `fit_witnesses(patterns, names)` fits m, u and the prior by EM with no labels.

## placebo and bootstrap
`placebo_test(statistic, data, perturb, n, seed)`, `shuffle_column(rows, col, rng)`,
`cluster_bootstrap(items, cluster_fn, statistic, n, seed)` (resamples whole clusters, e.g. state-year),
`paired_cluster_bootstrap(...)` (difference of two statistics, with `excludes_zero`), `interval_excludes_zero`.

## config
`load_region(track_dir, region="us")` reads `<track_dir>/config/<region>.json`.

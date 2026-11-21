# records v0.2 release files

- `time_offset_patches_dev_ics.jsonl.gz`, `time_offset_patches_dev_fod.jsonl.gz`: table-wide UTC-to-local time patches for the dev groups (four tables found recorded in UTC). Dev years only; sealed groups are reported, not patched.
- `v02_time_groups_dev_pooled.json`, `sealed_v02_time_groups.json`: per-group outcome, n, interval, share and gain.
- `v02_gazetteer_dev.csv`, `sealed_v02_gazetteer.csv`, `v02_gazetteer_dev_patches.jsonl.gz`: GNIS matches with radius; new fields only.
- `created_perimeters_v02_100.*`, `perimeters_v02_100_summary.json`: perimeters made from imagery for the 100-fire sample.

Results, failures and limits: `results/RECORDS_RESULTS.md` (additions dated 2026-11-21). Protocol: `protocol/RECORDS_PROTOCOL_v0.2.md`.

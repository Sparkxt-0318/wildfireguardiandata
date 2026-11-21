# records v0.4 release files (time only)

- `v04_pooled_dev.json`, `v04_pooled_dev_by_year.json`, `v04_pooling_loyo_dev.json`: pooling of the years of one source system x table on dev: pooled call, n, interval, year groups decided, leave-one-year-out check.
- `sealed_v04_pooled.json`, `sealed_v04_by_year.json`, `sealed_v04.json`: the same on the v0.4 sealed years (2006, 2011, 2015, 2020, 2024), opened once, with the comparison against the dev calls.
- `v04_ampm_dev.json`: the AM/PM rules on the OK Forestry open-finding groups; the sealed check (records of 100 to under 300 acres) is in `sealed_v04.json`.

No patch is released: the AM/PM explanation was not confirmed (the open finding stays open) and pooling decided no year group on the sealed years. Results and limits: `results/RECORDS_RESULTS.md` (addition dated 2026-11-21T05:45Z). Protocol: `protocol/RECORDS_PROTOCOL_v0.4.md`.

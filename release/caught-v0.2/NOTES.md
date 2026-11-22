# caught v0.2 release files (flags only)

**Headline (unchanged): 4,343 recorded US fires of 2018-2020 with no standard satellite label carry a verified
label (caught-v0.1, S3).** The v0.1 tier stays the verified tier.

v0.2 figures beside it, never summed with it (fires with no standard label):

v0.2 columns are what the verified count would be under that rule; each already includes the v0.1 verified labels.

| slice | v0.1 verified (headline) | v0.2 tier verified, any route (FAILED C1) | second-sensor route only (per route, not a rule) |
|---|---|---|---|
| S1 California 2020 | 92 | 275 | 176 |
| S2 US 2020 | 1,648 | 4,486 | 3,155 |
| S3 US 2018-2020 | 4,343 | 13,538 | 9,419 |

Placebo verified rate (C1, gate 1 %): v0.1 0.21 % (S3); v0.2 tier 1.80 % (fails); second sensor alone 0.62 %.

- `caught_v02_flags.parquet`: `rid`, `second_sensor_confirmed`, `persistence_confirmed`, `v02_tier`, one row per
  caught-v0.1 label; join on `rid` with release caught-v0.1 for geometry, interval and evidence.
- `DATA_CARD.md`: what the flags mean, the C1 failure, the per-route figures, deviation D-518, the scar floor.
- `SHA256SUMS`.

No new geometry; the caught-v0.1 files are not re-exported. Results: `results/CAUGHT_RESULTS.md` (addition
2026-11-22T01:25Z), `results/caught/v0.2/`, `results/caught/v0.2_summary.json`. Decision: DECISIONS D-021.

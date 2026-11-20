# results/caught: small tables and early samples (track 50)

Early samples from the dev split of slice S1 (California 2020), rules at development fix D1. They show the formats;
the numbers in them are not results (the rules are not frozen yet). Final tables replace them.

- `states_S1_dev_sample.parquet`: three-state table (fire / no_fire / unknown per record disc), schema in docs/CAUGHT_SCAR_API.md.
- `verified_S1_dev_sample.csv`: records that reach the verified tier, with witnesses, agreeing pairs and label geometry (simplified).
- `scar_pairs_sample_S1_dev/<rid>/`: pre.png, post.png, mask.png, dnbr.png, meta.json (before/after scar pairs for the video tool).

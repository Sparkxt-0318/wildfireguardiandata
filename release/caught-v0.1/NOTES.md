# caught v0.1 release files

Labels for agency-recorded US wildfires (FPA FOD 7th edition, 2018-2020) checked against standard satellite
products and against extra looks (more heat sensors, Sentinel-2/Landsat scars, HMS smoke, agency perimeters).
Every record is kept, with a tier: verified (two independent kinds of evidence agree), probable (one), record-only
(none, with a reason).

- `caught_labels_v0.1_<year>[_partKofN].parquet`: one row per record (GeoParquet, EPSG:4326, zstd). Fields in
  `DATA_CARD.md`.
- `caught_states_v0.1_<year>[_partKofN].parquet`: three states per searched record disc (fire / no_fire with its
  floor / unknown) with their time intervals, for the score adapter. Shapes simplified to about 3 m and repaired;
  the exact areas are the `*_m2_disc` fields of the label files.
- `heat_floors_m2.json`: edge-of-scan flaming-area floors per heat sensor, day and night.
- `scar_pairs/`: before/after chips for a sample of verified Sentinel-2 scars (pre, post, mask, dNBR PNG and
  meta.json per fire).
- `DATA_CARD.md`: what the set is, how it was made, what it does not show.
- `SHA256SUMS`: checksums of the files above.

Headline, gates and limits: `results/CAUGHT_RESULTS.md`. Protocol: `protocol/CAUGHT_PROTOCOL.md` (rules frozen at
530a3d5). The label geometry marks where a fire was found, not its burned area (scars under-measure timber fires).
Regenerate (after the S3 run): labels and data card `firewitness caught export --tag final --slices S3 --out
release/caught-v0.1`; three states `firewitness.caught.export.states_export("S3_final/records", "release/caught-v0.1")`;
scar pairs `firewitness.caught.export.scar_pairs(<verified S3 labels>, "release/caught-v0.1", n=40, seed=0)`.

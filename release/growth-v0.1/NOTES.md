# growth-v0.1 (track growth): early growth rate of fire power in the first hours

One new attribute per fire that no agency record holds: how fast the fire's radiated power rose in its first 1, 3 and
6 hours, from the raw 5-minute GOES ABI frames, with an interval and one of three states (measured, flat, unknown).
It builds on the live track (frozen trace-back onset, per-pixel background, fire-power estimate of live v0.2).
Protocol: `protocol/GROWTH_PROTOCOL.md` (committed alone with the fire lists before any result). Results and limits:
`GROWTH_RESULTS.md`. Data card: `DATA_CARD.md`. Release v0.1 and its notes are unchanged.

{{HEADLINE}}

Files:
- `early_growth_v0.1.csv` / `.parquet`: one row per fire and satellite (fire id, permanent id where linked, t0 and its
  kind, every attribute with interval and state, clear-frame counts).
- `growth_series_fire.parquet`: the per-fire series used (fire power, fire pixels, the operational product's power,
  per 5-minute frame, per satellite). `growth_series_placebo.parquet`: the placebo series.
- `growth_fires.csv` (per fire and satellite: set, dev/sealed mark, final size used for G4, t0, first operational
  detection and its power), `growth_runs.csv`, `growth_fires_set_a.csv`, `growth_fires_set_b.csv`.
- `growth_thresholds_us.json` (frozen before the sealed opening), `growth_us.json` (every setting).
- `growth_numbers.json`, `GROWTH_RESULTS.md`, `growth_curves_sealed.png` (slide figure), `growth_curves.csv`.
- `growth_stats.py`, `growth_report.py`, `growth_recompute.py`: recompute every number of the results from these
  files alone.

Recompute (no network, no key):

```
pip install numpy pandas scipy pyarrow matplotlib
python growth_recompute.py --dir . --out recomputed
```

It checks `SHA256SUMS.txt`, recomputes the thresholds, the table and every gate, renders `GROWTH_RESULTS.md` and
compares it byte for byte with the released copy. From a clone: `firewitness live growth recompute`.

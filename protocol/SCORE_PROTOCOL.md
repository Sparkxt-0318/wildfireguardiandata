# SCORE_PROTOCOL (track 54, score)

Committed before any result. Changes after this commit are logged in results/ROUNDS_score.md with the reason.

## 1. Question
Fire is ~0.1% of pixels. Which negatives are used, how data are split, and how a match is counted decide the score more than the model does. This protocol fixes all three in advance so that planted cheats lose and honest models are comparable.

## 2. Data model (the unit of everything)
A **row** is one cell-day: `cell_id, lat, lon, date, fire_id (for positives, else blank), state, region, landcover, danger_class, season`, plus optional `interval_lo, interval_hi` (label interval, days).
`state` is one of `fire`, `no_fire` (verified no fire), `unknown`. Unknown is never a negative and never a positive. Until track 50's three-state format is merged, an adapter derives the state from a benchmark's own masks: mask=1 is `fire`; mask=0 where the benchmark's own validity mask says the pixel was observed is `no_fire`; everything else (clouds, missing, masked) is `unknown`.
A **prediction** is `cell_id, date (valid day), issue_day, score, info_until`. `info_until` is the latest date of any input the model used; it is mandatory.

## 3. Negative sampling (`negatives sample`)
1. Negatives come only from `no_fire` rows. A `no_fire` row within `buffer_km`/`buffer_days` of any `fire` row is not eligible (it may be an unseen fire edge).
2. Each positive is matched to `k` negatives (default 3) on the 4-key stratum (danger_class, landcover, region, season). If the stratum has fewer than `k` eligible rows, the key is relaxed in a fixed order (season ±1 month, then danger_class ±1, then landcover class group, then region); every relaxation is recorded per negative (`match_level`), and the card reports the share at each level. Sampling is seeded; output order is canonical (sorted by key), so the result is reproducible.
3. A negative is flagged `hard=1` when it is in the top danger class AND (the adapter's heat variable above its stratum median OR it lies within `hard_km` of a catalogued thermal source). The catalogue (`firewitness/score/data/hard_negatives.csv`) lists hot places that are not wildfires (geothermal fields, refineries, flares, steel and cement plants, volcanic sites, burn-scar dark soil). Each row has `kind`, coordinates with stated precision, and a `source_note`. Hard negatives are always included at a stated share (default 25% of negatives) and always reported separately on the card.
4. The sampler also writes a balance table (positives vs negatives per stratum), which the gate N5 uses.

## 4. Splits (`splits make`)
Blocked in space and time with a buffer, and by fire.
- Fire is the atom: every row of a fire goes to one fold. A fire's fold is set by its centroid block and its onset date.
- Space block = `block_km` square (default 100 km); time block = calendar year (or season-year for short benchmarks). Test = blocks hashed to test AND date in the test window; val likewise; train = the rest.
- Buffer: a train or val row is **dropped** if some row of a later fold is within `buffer_km` (default 50) in space AND within `buffer_days` (default 30) in time. Dropped rows are listed.
- Seeds, parameters, input hash and fold membership (fire_ids, block ids, dropped counts) are written to `splits/<name>.json` and published; everyone scores on the same file. A split file carries its own sha256 and the scorer refuses edited files.

## 5. Score contract (`score`)
A contract file (JSON) fixes before scoring: `unit` (cell size in km, day), `horizon_days`, `tolerances` (three named pairs of `space_cells`, `time_days`: `strict` 0/0, `mid` 1/1, `loose` 3/3), `threshold` rule (`max_f1_on_validation`, or a fixed number; **never fit on test**), `label_reading` (both `strict` and `interval`), `min_event_overlap`, and `leak` settings. The scorer hashes the contract and prints the hash on the card.
Match rule: a predicted positive is a true positive if some `fire` row lies within the tolerance; a `fire` row is recalled if some predicted positive lies within the tolerance. Precision uses the first, recall the second. `unknown` rows are removed from both sides and counted.
**Strict reading**: positive means a `fire` row on exactly the stated day. **Interval reading**: a `fire` row is positive for any day inside its `[interval_lo, interval_hi]`; a predicted positive falling in that interval counts.

## 6. The score card (always shown, test fold only, threshold from validation)
For the model, for persistence (previous-day fire mask carried forward) and for climatology (stratum fire frequency estimated on train only), each with its own threshold chosen by the same rule on validation:
1. precision, recall, F1 at the threshold, at each of three tolerances and each of two readings (6 cells per model);
2. **predicted area / true area** (flagged cells over fire cells, at the strict reading), and the same on hard negatives only (false-alarm rate there);
3. event-level detection (share of fires with at least one matched alarm) and lead time (event onset minus earliest matched `issue_day`, days: median and quartiles), at the mid tolerance;
4. count of cells excluded as unknown, by reason, and its share of all rows;
5. the model's lift over persistence and over climatology (differences, with a cluster bootstrap over fires);
6. a leak report (section 7);
7. a line stating the contract hash, split hash, predictions hash. Output is byte-identical for the same inputs in any row order.
Threshold-free numbers (AUC, AP) are shown only below the card and never used for any gate.

## 7. Leak check
Hard fail if any prediction row has `info_until` > `issue_day`, or `info_until` is missing. Second, behavioural check: on rows with no fire within `leak_radius` cells at `issue_day`, a score that separates new positives from negatives with AUC above `leak_auc` (default 0.97, n >= 30 positives) is flagged "implausible foresight" (a claimed forecast cannot see an ignition that nothing in the past marks). The second check is a screen, not a proof; docs state this.

## 8. Gates (planted cheats must lose)
- **N1** location-memoriser (score = train-fold fire frequency of the exact cell/neighbourhood) is no better than persistence on test of the blocked split, with a fire-clustered bootstrap interval; and it IS better on a random split (demonstrating the inflation).
- **N2** flag-everything model: F1 below persistence, predicted/true area >> 1, shown on the card; the card prints a red "over-prediction" warning when area ratio > `area_ratio_warn` (default 3).
- **N3** a model fed post-fire information (next-days labels, burn scar) is caught by the leak check (declared or behavioural).
- **N4** the same predictions in any row order and on a re-run give an identical card (byte hash).
- **N5** a simple logistic model trained with the matched sampler over-predicts no more than a threshold-ratio R (stated before running: predicted/true area in top-danger-class periods <= 2.0) while the same model trained on random negatives exceeds it; this checks the tool, not a new survey.
A gate outcome is PASS or FAIL; a failure is reported as a failure and fixed through the improvement loop (<= 8 rounds, logged in results/ROUNDS_score.md).

## 9. Benchmark and what is not claimed
Primary benchmark: a public spread benchmark with an adapter and no key (WildfireSpreadTS, Zenodo 8006177, CC-BY-4.0; sampled by byte-range from the archive, not downloaded whole). Where it cannot be read, a stated fallback is used and recorded in DECISIONS.md. Gates N1-N4 are also run on a synthetic benchmark with known truth. The tool shows that cheats lose under the contract; it does not show that any real model is good, that WildfireSpreadTS labels are correct, or that the thresholds in this protocol are optimal.

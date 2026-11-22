# Step 2 — recompute of results/SCORE_RESULTS.md (main 3fc6ab0) from release v0.1 only

Release dir: `S/rel_v01/x/score-v0.1/score-v0.1/` (S = scratchpad; SHA256SUMS verified: all 10 files OK). Other v0.1 tracks
used: live-v0.1 (`onset_labels.csv`, `live_fires.csv`) and caught-v0.1 (`caught_labels_v0.1_2020.parquet`,
`caught_states_v0.1_2020.parquet`). Scripts in `S/work_score/scripts/`: `live_adapter.py`, `live_recordonly.py`,
`caught_s1.py`, `caught_floor.py`. These **import the repo's own code** (`firewitness.score.adapters.live/caught`,
`firewitness.score.splits.make(scheme="space", seed=54)`, `firewitness.score.negatives.sample(seed=54)`) because the
counts are outputs of that code (seed 54 and split parameters as recorded in the released split files). Split-file
numbers were read directly from the JSON and the files' self-hashes recomputed (sha256 of `json.dumps(body, sort_keys=True,
separators=(",", ":"))` without the `sha256` key).

**Important: the release contains no score cards.** The four `wildfirespreadts_*.json` files are **split files**
(blocks, folds, dropped fires, params, sha256), not gate or model score cards. The gate outputs cited by the results file
(`results/gates_wildfirespreadts.json` / `results/score/gates_wildfirespreadts.json`,
`results/score/gates_wildfirespreadts_space_time.json`, `results/score/n3_unseen_cheats.json`,
`results/score/caught_*_card.json`, `results/score/live_*`) are **not in release v0.1**, and the WildfireSpreadTS benchmark
is not redistributed (NOTES.md says so). Hence every gate number N1–N5 (e.g. N5 10.682x vs 7.119x, 1.305x vs 1.576x) is
CANNOT RECOMPUTE.

**SCORE_RESULTS.md in the release vs main:** not identical. The release copy (15,307 bytes, sha256 ac2a3483…, = the file at
commit f6f6744) is lines 1–87 of main's file byte for byte; main (7c118a1 onward) adds lines 88–94, the dated
"Addition 2026-11-21 (live onset labels)". Lines 1–87 are unchanged. ROUNDS_score.md, SCORING.md (= docs/SCORING.md),
contract_template.json (= firewitness/score/contracts/template.json), hard_negatives.csv (= firewitness/score/data/) and the four
split files are byte-identical to the repo copies.

## 1. Summary

Counted per number: **MATCH 55, MISMATCH 10, MISMATCH-MC 0, CANNOT RECOMPUTE 136, PARAMETER 10 (rows)**.
**Mismatches — all in the 2026-11-21 caught-full-S1 addition (lines 62–66), recomputed by running the repo's caught adapter,
space split and sampler on the CA subset of the released `caught_states_v0.1_2020.parquet`:** rows 13,697 → 13,695;
no_fire rows 3,981 → 3,979; cell-days 235.2M → 235.5M; fire 57.1M → 57.3M; unknown 160.0M → 160.1M; extent-sized no_fire
cell-days 72.0M → 72.2M; sampler positives 1,996,635 → 1,999,078; negatives 2,024,742 → 1,971,110; match level "exact" 16 % →
15 % and "same-danger fallback" 55 % → 56 %. Cause: the published card was made from `results/caught/states_S1.parquet`
(not released), which has 2 more no_fire rows than the released v0.1 states for the same 10,360 records; split counts,
tier counts, 46,592 floor passes, the 0.02 km median cell and the 0.7 % hard share still match. CANNOT RECOMPUTE: every WildfireSpreadTS gate number (N1–N5, the
honest-model findings, the space_time gate re-run, the unseen-cheat table: gate JSONs not released and the benchmark not
redistributed), the benchmark size line (68,872,831 cell-days etc.), 607 fires, and the caught dev-sample addition
(`states_S1_dev_sample.parquet` not released). MATCH: split files (168 fires, space 35/18/69 + 46 dropped, split hash
d94a223cf441, space_time 14/10/32 + 112 dropped, 35 test fires), the live adapter numbers (147/36/48, 9 dropped,
760,144 / 190,036) both record-only and from the onset labels, the onset-label kind counts (45; 5/24/13/3; 195), and the caught
record/tier/split counts.

## 2. Table

| line | quantity (short) | published | recomputed | status | source file and field / how |
|---|---|---|---|---|---|
| 3 | protocol commit dbce880 | — | — | PARAMETER | |
| 5 | WildfireSpreadTS fires used | 168 | 168 | MATCH | every split file: folds + dropped = 168 (input_fires_sha256 72af7004… identical in all four) |
| 5 | WildfireSpreadTS total fires | 607 | — | CANNOT RECOMPUTE | benchmark index (firewitness_raw/INDEX.md) not released |
| 5 | 42 per year | 42 | time split folds test 42 / val 42 / train 84 | MATCH | wildfirespreadts_time.json (year-held-out folds; train = 2 years, so 2 of 4 years shown directly) |
| 5 | years 2018–2021; 8–40 days; 750 m; 48 GB archive | — | — | PARAMETER | selection rule / unit (cell_km 0.75 in contract_template.json); archive size not counted |
| 9 | dataset fires | 168 | 168 | MATCH | as line 5 |
| 9 | cell-days | 68,872,831 | — | CANNOT RECOMPUTE | needs the built benchmark (not redistributed) |
| 9 | fire cell-days | 115,550 | — | CANNOT RECOMPUTE | same |
| 9 | fire share | 0.17 % | (115,550 / 68,872,831 = 0.168 %) | CANNOT RECOMPUTE | arithmetic consistent |
| 9 | unknown cell-days | 3,721,001 | — | CANNOT RECOMPUTE | same |
| 9 | split id | d94a223cf441 | d94a223cf441 | MATCH | wildfirespreadts_space.json sha256; self-hash recomputed |
| 9 | folds test / train / val | 35 / 69 / 18 | 35 / 69 / 18 | MATCH | wildfirespreadts_space.json folds (3 numbers) |
| 9 | dropped by buffer | 46 | 46 (all reason "buffer") | MATCH | dropped |
| 13 | N1 strict F1 memoriser / persistence | 0.004195 / 0.546312 | — | CANNOT RECOMPUTE | results/score/gates_wildfirespreadts.json (not released); benchmark not redistributed (2 numbers) |
| 13 | N1 lift CI | [−0.616109, −0.424076] | — | CANNOT RECOMPUTE | same (2 numbers) |
| 13 | N1 random-split F1 / inflation | 0.1648 / 39.28x | — | CANNOT RECOMPUTE | same (2 numbers) |
| 13 | N1 interpolator / persistence random rows | 0.4271 / 0.5174 | — | CANNOT RECOMPUTE | same (2 numbers) |
| 14 | N2 strict F1 / persistence / area ratio / loose F1 / persistence loose | 0.004195 / 0.546312 / 475.7775 / 0.044961 / 0.999437 | — | CANNOT RECOMPUTE | same (5 numbers) |
| 16 | N4 card hashes | 93814d66d407b5b3 (×3), eb7eea3dfa1a8771 (×3) | — | CANNOT RECOMPUTE | needs benchmark and predictions (2 numbers) |
| 17 | N5 weather-only, validation threshold | matched 10.682 vs random 7.119 | — | CANNOT RECOMPUTE | gates JSON n5 (not released) (2 numbers) |
| 17 | N5 limit | 2.0 | — | PARAMETER | pre-registered |
| 17 | N5 weather-only at p = 0.5 | 6.81 vs 53.677 | — | CANNOT RECOMPUTE | (2 numbers) |
| 18 | N5 with proximity, validation threshold | 1.305 vs 1.576 | — | CANNOT RECOMPUTE | (2 numbers) |
| 18 | N5 with proximity at 0.5 | 3.773 vs 6.65 | — | CANNOT RECOMPUTE | (2 numbers) |
| 23 | N1 prose: 0.004, 0.546, lift −0.542, CI −0.616 to −0.424, 39x, 0.165, 0.004, 0.427, 0.517 | — | — | CANNOT RECOMPUTE | rounded repeats of line 13 (lift −0.542 = 0.004195 − 0.546312 consistent) (10 numbers) |
| 25 | N2 prose: 0.004, 0.546, 476x, 0.045, 0.999, 0.999 | — | — | CANNOT RECOMPUTE | repeats of line 14 (6 numbers) |
| 27 | N3 AUCs: scar 0.992, next-day 1.000, honest 0.695 far / 0.769 front; round-5 gain +0.014 | — | — | CANNOT RECOMPUTE | gates JSON / ROUNDS (5 numbers) |
| 27 | AUC limits 0.90 / 0.95; round numbers 2, 5 | — | — | PARAMETER | equal to contract_template.json leak.auc 0.9, leak.front_auc 0.95 |
| 31 | N5 prose: 10.7, 7.1, 6.8, 53.7, 1.31, 1.58, 3.8, 6.7, 8x, 1.8x | — | — | CANNOT RECOMPUTE | repeats of lines 17–18; 8x = 53.677/6.81 = 7.9, 1.8x = 6.65/3.773 = 1.76 (consistent) (10 numbers) |
| 34 | F1 by reading: honest 0.53 / 0.86 / 0.98 / 0.99; persistence 0.55 / 0.99 / 0.997 / 1.0 | — | — | CANNOT RECOMPUTE | gates JSON (8 numbers) |
| 35 | honest − persistence −0.015 (CI −0.038 to +0.005); events 181 / 195 vs 191 | — | — | CANNOT RECOMPUTE | (6 numbers) |
| 36 | buffer 50 km / 30 days | — | params buffer_km 50, buffer_days 30 | PARAMETER | split files params |
| 36 | space split drops 46 of 168 | 46 / 168 | 46 / 168 | MATCH | wildfirespreadts_space.json (2 numbers) |
| 37 | climatology strict F1 0.017, 29x area | — | — | CANNOT RECOMPUTE | (2 numbers) |
| 41 | 168 fires; 750 m | 168 | 168 | MATCH | repeat (1 number; 750 m PARAMETER) |
| 46 | space_time folds test / val / train / dropped | 14 / 10 / 32 / 112 | 14 / 10 / 32 / 112 | MATCH | wildfirespreadts_space_time.json (sha256 b352300088ad self-verified) (4 numbers) |
| 46 | space_time N5: 54.1 vs 73.5, 17.9 vs 33.3, 0.82 vs 0.83, 3.8 vs 6.1 | — | — | CANNOT RECOMPUTE | results/score/gates_wildfirespreadts_space_time.json not released (8 numbers) |
| 46 | space_time honest 0.580 vs persistence 0.611, lift −0.031 (−0.114 to −0.013); memoriser 0.006, 29x | — | — | CANNOT RECOMPUTE | same (7 numbers) |
| 48 | live adapter: fires | 240 | 240 | MATCH | live-v0.1 live_fires.csv |
| 48 | live adapter fire cell-days | 760,144 | 760,144 | MATCH | `live_recordonly.py`: adapters.live.read_csv(live_fires.csv) → splits.make(space, seed 54) → negatives.sample(train ids, seed 54) positives. NB this is the sampler's positives on the 147 train fires; the dataset holds 1,072,048 fire cell-days |
| 48 | matched negatives | 190,036 | 190,036 | MATCH | same, negatives |
| 48 | space split train / val / test | 147 / 36 / 48 | 147 / 36 / 48 | MATCH | same (3 numbers) |
| 48 | dropped | 9 | 9 | MATCH | same |
| 54 | caught dev sample: records 334 (184 / 140 / 10); cell-days 9.78M, fire 1.95M, no_fire 1.21M, unknown 6.62M, 68 % | — | — | CANNOT RECOMPUTE | results/caught/states_S1_dev_sample.parquet not in release (9 numbers) |
| 55 | 0 of 3.75M pass floor; floors 1,440–3,400 m²; 400 m² cell; median cell 0.038 km | — | — | CANNOT RECOMPUTE | same (5 numbers) |
| 56 | dev sample split 124 / 55 / 72, 83 dropped; 118,121 pos, 354,363 neg, 623,360 eligible; levels 9 / 4 / 15 / 73 % | — | — | CANNOT RECOMPUTE | same (11 numbers) |
| 62 | commit daaad5e | — | — | PARAMETER | |
| 62 | S1 rows | 13,697 | **13,695** | MISMATCH | caught-v0.1 caught_states_v0.1_2020.parquet, rid in CA records of caught_labels_v0.1_2020.parquet |
| 62 | fire rows | 974 | 974 | MATCH | same, state = fire |
| 62 | no_fire rows | 3,981 | **3,979** | MISMATCH | same, state = no_fire |
| 62 | unknown rows | 8,742 | 8,742 | MATCH | same |
| 63 | records | 10,360 | 10,360 | MATCH | caught_labels_v0.1_2020.parquet STATE = CA (also = scenes built) |
| 63 | record-only / probable / verified | 9,349 / 633 / 378 | 9,349 / 633 / 378 | MATCH | same, tier (3 numbers) |
| 63 | cell-days | 235.2M | **235.5M** (235,531,624) | MISMATCH | `caught_s1.py`: adapters.caught.from_rows (cell sized to floor) → Dataset.summary() |
| 63 | fire cell-days | 57.1M | **57.3M** (57,314,517) | MISMATCH | same |
| 63 | no_fire cell-days | 18.1M | 18.1M (18,128,748) | MATCH | same |
| 63 | unknown cell-days | 160.0M | **160.1M** (160,088,359) | MISMATCH | same |
| 63 | unknown share | 68 % | 67.97 % | MATCH | |
| 64 | extent-sized no_fire cell-days passing floor rule | 46,592 | 46,592 | MATCH | `caught_floor.py`: from_rows(cell_from_floor=False); no_fire cells with floor_m2 ≤ cell area |
| 64 | extent-sized no_fire cell-days | 72.0M | **72.2M** (72,182,092) | MISMATCH | same |
| 64 | median cell | 0.02 km | 0.02 | MATCH | median scene cell_km |
| 65 | space split train / val / test / dropped | 2,292 / 1,004 / 2,342 / 4,722 | 2,292 / 1,004 / 2,342 / 4,722 | MATCH | splits.make(space, seed 54) (4 numbers) |
| 66 | sampler positives | 1,996,635 | **1,999,078** | MISMATCH | negatives.sample(train, seed 54) |
| 66 | verified negatives | 2,024,742 | **1,971,110** | MISMATCH | same (all eligible taken in both) |
| 66 | k = 3 | — | — | PARAMETER | |
| 66 | k = 3 would ask for | 6.0M | 6.0M (3 × 1,999,078) | MATCH | |
| 66 | ratio about 1:1 | 1:1 | 1.01:1 | MATCH | |
| 66 | level exact | 16 % | **15 %** (14.95 %) | MISMATCH | sampler level counts (unrounded) |
| 66 | level month ±1 | 18 % | 17.9 % | MATCH | |
| 66 | level land-cover group and region | 11 % | 11.50 % (0.114965) | MATCH | rounds to 11 |
| 66 | level same-danger fallback | 55 % | **56 %** (55.62 %) | MISMATCH | |
| 66 | hard negatives share | 0.7 % | 0.68 % | MATCH | |
| 72 | leak.auc 0.97 → 0.90 at 17:49 UTC; front_auc 0.95 | — | — | PARAMETER | |
| 74-76 | cheat specs: limits 0.90/0.95, 0.2 × (…/25), 2 cells, 0.5, 5 cells, t+2 | — | — | PARAMETER | |
| 80 | test fires | 35 | 35 | MATCH | space split test fold |
| 83 | honest base: AUC 0.6953, F1 0.531473, persistence 0.546312, lift −0.014839 (−0.037663, 0.004517) | — | — | CANNOT RECOMPUTE | results/score/n3_unseen_cheats.json not released; needs benchmark (6 numbers) |
| 84 | L1: 0.9556, 0.5437, 0.546312, −0.002612 (−0.023725, 0.03128) | — | — | CANNOT RECOMPUTE | same (6 numbers) |
| 85 | L2: 0.8774, 0.545188, 0.546312, −0.001124 (−0.024616, 0.012928) | — | — | CANNOT RECOMPUTE | same (6 numbers) |
| 86 | prose: L1 AUC 0.956, L2 0.877, front 0.789 | — | — | CANNOT RECOMPUTE | same (3 numbers; limits 0.90/0.95 PARAMETER) |
| 92 | (main only) live onset: fires / real intervals | 240 / 45 | 240 / 45 | MATCH | live-v0.1 onset_labels.csv (2 numbers) |
| 92 | label kinds two / one / one (other none) / disagree | 5 / 24 / 13 / 3 | 5 / 24 / 13 / 3 | MATCH | label_kind (4 numbers) |
| 92 | anchor kept | 195 | 195 | MATCH | |
| 93 | 1-day minimum slack | — | — | PARAMETER | adapter rule |
| 93 | split 147 / 36 / 48, 9 dropped | 147 / 36 / 48 / 9 | 147 / 36 / 48 / 9 | MATCH | `live_adapter.py`: adapters.live.read_onset(onset_labels.csv, live_fires.csv) → split → sampler (4 numbers) |
| 93 | 760,144 fire cell-days; 190,036 negatives | 760,144 / 190,036 | 760,144 / 190,036 | MATCH | same (2 numbers; positives of the train fires, see line 48) |

## 3. Data problems / observations

1. **No score cards in the release.** The files the brief calls "score cards" (`wildfirespreadts_*.json`) are split
   definitions. No gate output, model card or prediction is released, and the benchmark is not redistributed, so no N1–N5
   number (nor the space_time re-run or the unseen-cheat table) can be checked from release v0.1. Recomputing them would need
   `results/score/gates_wildfirespreadts.json`, `gates_wildfirespreadts_space_time.json`, `n3_unseen_cheats.json` (repo only)
   or, properly, the WildfireSpreadTS archive (Zenodo 8006177) plus a rebuild with `firewitness score build` and the gate runs.
2. **Released caught states differ from the file the score track used.** The caught-S1 addition was computed from
   `results/caught/states_S1.parquet` (not released). The CA-2020 subset of the released
   `caught-v0.1/caught_states_v0.1_2020.parquet` has 13,695 rows (no_fire 3,979) for the same 10,360 records, i.e. 2 fewer
   no_fire rows; the derived cell-day totals, sampler positives/negatives and two match-level shares therefore do not reproduce
   (table above). The release thus does not carry the exact input of the published caught card.
3. **Line 48/93 wording:** "760,144 fire cell-days" is the matched sampler's positive count on the 147 training fires, not
   the fire cell-days of the 240-fire dataset (1,072,048). The onset-label dataset also differs from the record-only one in
   total cell-days (2,762,588 vs 2,760,506) although the sampler and split counts are equal, so "counts therefore equal the
   record-only run" holds for the sampler/split counts only.
4. **SCORE_RESULTS.md release copy ≠ main:** release = commit f6f6744 (lines 1–87); main adds lines 88–94 (live onset
   addition, commit 7c118a1). No earlier line differs.
5. Line 3 still cites `results/gates_wildfirespreadts.json`; the file's own line 73 says it moved to `results/score/`.
   Neither location is in the release.
6. Split files: all four self-hashes verify; all reference the same input_fires_sha256 (72af7004…); `time` has no dropped
   fires and empty `blocks`; `random_fire` drops 47 (not cited in the results).

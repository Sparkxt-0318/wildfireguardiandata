# SCORE_RESULTS (track 54)

Protocol: `protocol/SCORE_PROTOCOL.md` (commit dbce880, amendments listed at its end). Contract used: `firewitness/score/contracts/template.json` (hash on every card). Gate outputs: `results/gates_wildfirespreadts.json`; example card: `results/cards/card_wx+prox_wildfirespreadts.md`; rounds: `results/ROUNDS_score.md`. Split files: `firewitness/score/splits/`. Gates are also run in CI on a synthetic benchmark with known truth (`tests/score/`).

Benchmark: WildfireSpreadTS (Zenodo 8006177, CC-BY-4.0), 168 of its 607 fires (a hash-ordered subset) (42 per year 2018-2021, chosen by hash order among fires with 8-40 days, read by byte range from the 48 GB archive; listing hash in `firewitness_raw/INDEX.md`), coarsened to 750 m. Label states are derived from the benchmark's own masks (no cloud mask exists, see D-544). Honest model on the card: a logistic regression on weather, terrain, land cover and fire proximity trained with the matched sampler.

## WildfireSpreadTS, 168 fires

Dataset `wildfirespreadts-750m`: 168 fires, 68,872,831 cell-days, fire 115,550 (0.17%), unknown 3,721,001. Split `d94a223cf441` folds {'test': 35, 'train': 69, 'val': 18}, 46 fires dropped by the buffer.

| gate | outcome | key numbers |
|---|---|---|
| N1 location memoriser | PASS | blocked strict F1 0.004195 vs persistence 0.546312 (lift CI [-0.616109, -0.424076]); same model on random cell-day split F1 0.1648 (39.28x inflation); neighbour-day interpolator on random rows F1 0.4271 vs persistence 0.5174 |
| N2 flag everything | PASS | strict F1 0.004195 vs persistence 0.546312; area ratio 475.7775; loose-tolerance F1 0.044961 vs 0.999437; warning printed: True |
| N3 leaks | PASS | front_peek_lying_declaration: FLAG: implausible foresight at the fire front; honest_model: pass; next_day_lying_declaration: FLAG: implausible foresight at the fire front; scar_honest_declaration: FAIL: info_until later than the issue day; scar_lying_declaration: FLAG: implausible foresight |
| N4 order and re-run | PASS | card hashes: {"csv_orders": ["93814d66d407b5b3", "93814d66d407b5b3", "93814d66d407b5b3"], "dense_first_run": "eb7eea3dfa1a8771", "dense_second_run": "eb7eea3dfa1a8771", "dense_shuffled_order": "eb7eea3dfa1a8771"} |
| N5 matched vs random negatives (weather-only logistic) | FAIL | top-danger predicted/true area at validation threshold: matched 10.682 vs random 7.119 (pre-registered limit 2.0); at raw probability 0.5: matched 6.81 vs random 53.677 |
| N5 variant: with proximity features | FAIL | validation threshold: matched 1.305 vs random 1.576; at 0.5: matched 3.773 vs random 6.65 |


## Outcome of each gate, and what it does not show

**N1 PASS.** Under the blocked (space) split a model that memorises location scores strict F1 0.004 against persistence 0.546 (F1 lift -0.542, 95% fire-cluster bootstrap -0.616 to -0.424); the neighbour-day interpolator is identical because a test fire has no training rows. On a random cell-day split the same memoriser scores 39x better than on the blocked split (0.165 vs 0.004), and the interpolator reaches 0.427. *Not shown:* neither cheat beat persistence on the random split (persistence 0.517), so the random split inflates them but does not make them winners here; persistence is a strong baseline in a one-day-ahead spread task. The memoriser's blocked score equals flag-everything because it has no signal at unseen places and a constant score flags every cell.

**N2 PASS.** Flagging everything: strict F1 0.004 vs persistence 0.546, predicted area 476x the true area, the over-prediction warning is printed. At the loose tolerance it scores 0.045 vs 0.999 for persistence. *Not shown:* that every tolerance-gaming strategy loses; at the loose tolerance persistence already scores 0.999 so the loose column says almost nothing (the card lists all three tolerances for this reason).

**N3 PASS.** Burn-scar model with a false `info_until`: flagged (AUC 0.992 on cells with no fire nearby). Next-day-label model with a false declaration: flagged at the fire front (AUC 1.000). Peek-at-the-front cheat (round 2): flagged. Honest declaration of a later `info_until`: hard fail. The honest model passes (AUC 0.695 far, 0.769 front). *Not shown:* the screen is a screen. A leak weaker than the AUC limits (0.90 away from fire, 0.95 at the front), or one that only changes the choice of day (round 5: persistence made silent on days it secretly knows are fire-free, +0.014 strict F1, CI excludes zero, not caught), passes. Limits were set after seeing cheats.

**N4 PASS.** Identical card hashes for the first run, a re-run and shuffled fire order, and for a sparse CSV of the same predictions in three row orders. *Not shown:* byte-identity across machines with different numpy versions.

**N5 FAIL (pre-registered limit not met).** A weather-only logistic trained on matched vs random negatives, top-danger test cell-days, predicted/true area: at the validation threshold matched **10.7** vs random **7.1** (limit 2.0); at raw probability 0.5 matched **6.8** vs random **53.7**. With proximity features: validation threshold 1.31 vs 1.58, at 0.5 3.8 vs 6.7. So on this benchmark the matched sampler greatly reduces over-prediction when probabilities are used as trained (8x weather-only, 1.8x with proximity) but the threshold rule fitted on validation removes that effect (and for the weather-only model matched is worse: 10.7 vs 7.1). Neither model meets the stated 2.0 limit in the weather-only case. I did not move the limit to make it pass. *What this shows:* the tool can show the effect and the contract's validation threshold neutralises most of it. *Not shown:* a new survey, or that matched negatives improve any model's detection.

## Findings about the scorer that a user should know
- Strict reading and tolerance move F1 enormously: the honest model's F1 is 0.53 strict/strict, 0.86 strict/interval, 0.98 mid, 0.99 loose; persistence 0.55, 0.99, 0.997, 1.0. Only the strict row separates models.
- The honest model does **not** beat persistence at strict/strict (-0.015, CI -0.038 to +0.005) and loses at every other cell; it detects 181 of 195 new-front events against persistence 191 (event definition, D-546).
- The space split with a 50 km / 30 day buffer drops 46 of 168 fires; fewer fires, wider intervals.
- Climatology is far worse than persistence everywhere (strict F1 0.017) and flags 29x the true area.

## Not done / limits
- Adapter for firewitness labels (tracks 50 and 51): their label format is not on main yet; the adapter interface is `firewitness/score/adapters/` (build a `Dataset` of `Scene` objects with three-state `state`). Revisit when merged.
- One benchmark with one label source; 168 fires; 750 m cells; hard-negative catalogue coordinates approximate.


---
## Addition 2026-11-20 (after the orchestrator depth check; earlier lines unchanged)
**Combined split.** `space_time` holds fires out in space and time at once (see docs/SCORING.md); 14 test, 10 validation, 32 train fires, 112 dropped. Gates re-run on it: `results/score/gates_wildfirespreadts_space_time.json`. N1-N4 PASS, N5 FAIL again (weather-only matched 54.1x vs random 73.5x at the validation threshold, 17.9x vs 33.3x at raw probability 0.5; with proximity 0.82 vs 0.83 and 3.8x vs 6.1x). Honest model strict F1 0.580 vs persistence 0.611 (lift -0.031, CI -0.114 to -0.013), so under the strictest split the persistence baseline is beaten by nothing tested. The memoriser scores 0.006 strict F1 (random-rows inflation 29x).

**Label adapters.** `adapters/caught.py` (schema `caught_states_v0.1.parquet`, rows -> scenes, floor_m2 rule in the negatives sampler) and `adapters/live.py` (track 51 onset labels from `protocol/live_fires.csv`) are written and tested on small fixtures (`tests/score/test_adapters_and_split.py`). Negatives from caught labels use only `no_fire` cells whose look floor is no larger than the cell; WildfireSpreadTS masks stay the fallback, shown in a test. On the 240 live fires: 760,144 fire cell-days, 190,036 matched negatives (matched on region and season only, danger class and land cover unavailable), space split 147/36/48 with 9 dropped (`results/score/live_adapter_stats.json`). These pre-ignition negatives are not satellite verified. No model predictions exist for either label set, so no card was run on them.
**Not yet run:** the card on the real `caught_states_v0.1.parquet` (the file is not on main or in a release yet); it will be added here as a dated addition.

---
## Addition 2026-11-20 (caught dev sample; earlier lines unchanged): DEV SAMPLE, not results
Input: `results/caught/states_S1_dev_sample.parquet` (track 50, California 2020, rules at development fix D1, merged in PR #15). Full numbers: `results/score/caught_dev_sample_card.json`. Adapter `adapters/caught.py`, negatives sampler with the `floor_m2` rule, space split.
- 334 records (184 record-only, 140 probable, 10 verified); 9.78M cell-days: fire 1.95M, no_fire 1.21M, unknown 6.62M (68% unknown).
- **Finding about the rule.** On extent-sized cells (about 20 m, no floor sizing), 0 of the 3.75M no_fire cell-days pass the floor rule: the looks' floors are 1,440 to about 3,400 m2, larger than a roughly 400 m2 cell, so such a grid cannot call any cell verified no fire. The adapter therefore sizes each scene's cell to the largest finite look floor (median cell 0.038 km); coarser cells cost spatial detail and that is the price of a verified negative.
- Sampler on the train fires of the space split (124 train / 55 val / 72 test fires, 83 dropped by the buffer): 118,121 positives, 354,363 verified negatives from 623,360 eligible, all from `no_fire` cells whose look floor is no larger than the cell. Matching keys danger class and land cover do not exist in this table, so the match is on region and season: exact 9%, month +-1 4%, land-cover group and region 15%, same-danger fallback 73% (this is not a matched sample in the sense of the protocol; it is a verified-only sample).
- **No precision/recall card:** there are no model predictions or weather/fuel layers for these scenes. A model card on caught labels needs a model fed features at these records; that is not part of this sample.
- The full S1 file will replace this sample; numbers here must not be quoted as results.

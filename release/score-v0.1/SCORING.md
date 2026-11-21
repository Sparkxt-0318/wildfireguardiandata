# Scoring wildfire models with firewitness score

Fire is about 0.1% of pixels (0.18% of cell-days in the WildfireSpreadTS subset used here). Three choices decide a score more than the model does: which negatives are used, how the data are split, and how a match is counted. `firewitness score` fixes all three in a contract file and prints them on every score card.

## Data model
A scene is one fire's raster stack. Every cell-day has a state: `fire`, `no_fire` (verified no fire) or `unknown`. Unknown is never a negative and never a positive; the card says how many cells were excluded. `firewitness score build` makes a dataset from a benchmark's own masks (adapters: `wildfirespreadts`, `synthetic`). A prediction is a score per cell-day plus `info_until`, the latest date of any input the model used (mandatory).

## The three commands
```
firewitness splits make   --dataset D --scheme space --out splits/x.json
firewitness negatives sample --dataset D --split splits/x.json --fold train --k 3 --out neg.npz
firewitness score --dataset D --split splits/x.json --contract C.json --predictions P.npz --model-name m
```
(The same commands exist nested as `firewitness score splits make`, `... negatives sample`, `... card`; `contract-template` writes a starting contract; `gates` runs N1-N5.)

**negatives sample.** Negatives come only from `no_fire` cells that are not next to a fire. For track 50's three-state labels (`adapters/caught.py`, schema `caught_states_v0.1.parquet`) a no_fire cell is eligible only where the look's `floor_m2` is no larger than the cell area; WildfireSpreadTS masks are the fallback when a dataset has no `floor_m2` (stats report which rule was used and which match keys, danger class and land cover, the labels lack). Track 51's onset labels are read by `adapters/live.py` (fire from the onset day; pre-ignition footprint as no_fire, flagged not satellite verified). Each positive gets `k` negatives matched on fire-danger class (ERC bins fixed in advance), land cover, region and month. If a stratum runs short the match is relaxed in a fixed order and the share at each level is reported. A catalogue of hard negatives (hot places that are not wildfires: geothermal fields, refineries, gas flares, volcanoes, coal-seam fires, and derived hot bare ground) tops the negatives up to 25% and is flagged `hard=1`. `--random` gives the naive sampler for comparison.

**splits make.** The fire is the atom: all rows of a fire go to one fold. Schemes: `space_time` (blocked in space AND time AND by fire at once: test = test blocks x the last year, validation = validation blocks x the year before, train = blocks outside both and years outside both; fires in a held-out block but a training year, or the reverse, are dropped, then the buffer is applied; published as `wildfirespreadts_space_time.json`, the strictest split and the one to report), `space` (100 km blocks), `time` (by year), `random_fire`, and `random_rows` (naive, used only to show inflation; the scorer refuses it). A train or validation fire is dropped if a later-fold fire is within the buffer in both space (50 km) and time (30 days). Split files carry their own sha256 and are published under `firewitness/score/splits/`; an edited file is refused.

**card.** The threshold is set on validation fires by the contract rule and never on test. The card shows, for the model, persistence and climatology:
- precision, recall, F1 at three stated tolerances (strict 0 cells/0 days, mid 1/1, loose 3/3) and two readings: *strict* (the label's exact day) and *interval* (the label's own day-uncertainty, `interval_slack`, widens the time match);
- predicted area over true area, and the false-alarm rate on hard negatives;
- event-level detection and lead time (an event is a fire-day with new burning cells away from yesterday's fire);
- cells excluded as unknown; lift over persistence and climatology with a cluster bootstrap over fires; the leak report; contract, split and predictions hashes.
Output is byte-identical for the same inputs in any row order.

## The contract
`contract-template` writes it. It fixes the unit, horizon, the three tolerances, the threshold rule (`max_f1_on_validation` or `fixed`; a rule fitted on test is refused), the label readings, the event definition, leak settings and the over-prediction warning (area ratio above 3).

## Leak check
Hard fail if any `info_until` is later than the issue day or missing. Then a behavioural screen: on cells with no fire within 3 cells the day before, a score separating new fire from no fire with AUC above 0.90 (at least 30 such cells) is flagged "implausible foresight". Honest models measured 0.74-0.77. The 0.90 limit was set after seeing one cheat (round 1) and the front limit after another, so N3 passes only on cheats it was tuned on; on two unseen cheats it caught one and missed one (results/SCORE_RESULTS.md, 2026-11-21). It is a screen, not a proof. A leak weaker than the limit, or one that is not in new-ignition cells, is not caught.

## What the gates show
Planted cheats lose: a location memoriser and a neighbour-day interpolator are no better than persistence under blocked splits (N1); flagging everything loses and is warned (N2); leaked predictions are flagged (N3); the card is identical in any order and on re-run (N4); matched negatives reduce over-prediction in the top danger class compared with random negatives (N5). Exact outcomes, including the failures, are in `results/SCORE_RESULTS.md`.

## What it does not show
It does not show that any real model is good, that the benchmark's labels are right (WildfireSpreadTS has no cloud mask, so "no detection" is read as no fire where the composites exist), or that the thresholds are optimal. Lead time in a one-day-ahead benchmark is bounded by horizon plus tolerance by construction. The hard-negative catalogue is approximate.

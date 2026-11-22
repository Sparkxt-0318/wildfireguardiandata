# Audit step 4: are held-out or sealed sets read during fitting or tuning?

Repo: Sparkxt-0318/wildfireguardiandata, clone at main 3fc6ab0 (read only). All times are UTC. Author dates in `+08:00` were converted (`TZ=UTC git log --date=format-local`).

## Summary

| Track | Verdict | One line |
|---|---|---|
| records | NO LEAK into the sealed years. One POSSIBLE LEAK (disclosed): the ics_fired candidate pool is built from published links | The EM fits and the fixed-rule choice use dev years only. Per-task thresholds were tuned on dev F1 against the dev published links. The v0.2 to v0.4 rule files were frozen before each opening, and none changed after it. The v0.3 and v0.4 sealed years had been v0.2 dev years (disclosed; D-019 covers v0.4). |
| caught | NO LEAK FOUND | The sealed truth fires are not read by any rule-choice code. The rule files did not change after the v0.1 opening. The sealed run is not gated in code. |
| live | NO LEAK FOUND | Fit and rounds use dev fires only. Replay of the test split needs the flag. E1 on test uses h from dev placebos. detector_us.json has the frozen sha. |
| smoke | NO LEAK FOUND (procedural only) | No code reads either sequence list. params.py was frozen before the sealed opening. The split rule checks out. |
| fuel | NO LEAK FOUND | The import graph confirms the claim. Plot loading refuses sealed tiles. sealed.py checks a lock and the frozen hash. |
| score | NO LEAK FOUND (one disclosed caveat) | The threshold is chosen on validation only. The negatives sampler draws only from the fold it is given. The leak-screen limits were tuned on the gate fires (val + test). |

## records (firewitness/records/)

**Link model fitting (R1).**
- `link.py:153` `fit_fs` is unlabeled EM. `link.compare` uses only `FIELDS = dist, day, size, name, state` (`link.py:84`). No `pub_*` column is a feature. `canon.py:3` keeps the published links in separate `pub_*` columns, and those are used only to build `truth` (`link_tasks.py:54, 63-71, 83`).
- The EM fit is restricted to dev-year pairs: `link_tasks.py:111,115,117` (`run_task`) and `:181,183` (`decide_all`). `split_of` (`link_tasks.py:20-22`) excludes the test years 1995, 2001, 2007, 2013 and 2019 and the heldout year 2024 (`config/us.json:158-166`).
- Baseline fixed rule: chosen by dev F1 against `truth_dev` only (`link_tasks.py:131-139`).
- **Thresholds.** `SETTINGS` and `TASK_DECISION` (`link_tasks.py:41-43`) and the dedupe threshold `hi=0.97` (`dedupe.py:30`) were all added in 108baf4 (2026-11-20T18:50:53Z), before the sealed opener (6d004a5, 18:51:52Z).
  - ROUNDS_records rows 6-8 show the per-task values (0.7/0.1, 0.8/0.1, 0.5/0.0) were picked on dev F1 against the published dev links. That is supervised tuning on dev labels, not test. "Without labels" applies only to the m/u/prior fit.
  - Dedupe 0.97 was picked after seeing one distinct dev MTBS pair (row 5, disclosed).
  - The pipeline dedupe fit is on dev only: `pipeline.py:112-113` (`fit_mask=dev`).
  - `gates.py:181` fits dedupe on all records, unlabeled, for a gate count only.
- **POSSIBLE LEAK (structural, disclosed).** `task_ics_fired` (`link_tasks.py:76-85`) builds the right-hand (FIRED) candidate pool from `ics.pub_fired` (`link_tasks.py:79`). In other words, the candidates exist only because a published link points to them.
  - The unlabeled EM is then fitted on pairs that include this label-derived pool (`link_tasks.py:117`), so the published links are not fully hidden for this task.
  - The docstring (`:77-78`) and RECORDS_RESULTS.md:36 disclose it ("restricted pool"). The baseline shares the same pool, and the target is not met, so the practical effect is small. It does not touch the sealed years.
- **Sealed opener.** `sealed.py:20-38` refuses to run twice (`:21-22`) and calls `run_task(split="test")`, which still fits on dev. The recorded frozen commit is 69026c3 (19:14:30Z), and the results were committed in b37f6f1 (19:24:11Z).
  - Commit 0dc47a4 (19:05:50Z), after the opener was written, moved `det_min_acres=300` from the `sealed.py` call into the `locate.Params` default. The sealed run behaves the same, and 0dc47a4 is inside the frozen commit.
  - No later commit touches link.py, link_tasks.py, em.py, dedupe.py, locate.py, values.py, canon.py or config/ (only 59301ad adds new v0.4 files).
- **Location tool (sealed.py:32).** Witness reliabilities are fitted, unlabeled, on `src == "ics209_2014"` rows. Those rows include 2019, a test year.
  - The location score uses only legacy (pre-2014) rows (`eval_published.py:34`), and the published lat/long cleaning file is read only by the scorer (`eval_published.py:15-21`). The 2019 inclusion is transductive and unlabeled, so it is not a leak.
- **v0.2 to v0.4 (time offsets, gazetteer, swap, pooling).**
  - `timeoffset_run.py:14,73` drops the v0.2 sealed years {2004, 2010, 2016, 2022} unless `include_sealed`.
  - `gazetteer3.py:39` makes a hash split (bucket ≥3, or raw missing, goes to dev). `fit_radii` (`gazetteer3.py:56`) takes dev matches. Its driver is not committed, but `results/data/v03_gazetteer_radii.json` has n_dev_matched = 287, the dev count in protocol v0.3, and it was committed in aa75259 (02:43:56Z), before the freeze at 7ad17a7 (02:45:52Z).
  - The sealed openers `sealed_v02.py:58-59`, `sealed_v03.py:21-22` and `sealed_v04.py:53-54` refuse to run twice and have dev dry-run modes.
  - Timelines (rule files: timeoffset*, timepool, gazetteer*, timeswap, ampm, perimeters):

    | Version | Rules frozen | Sealed opened | Rule-file commits after the opening |
    |---|---|---|---|
    | v0.2 | eafeb99, 01:25:48Z | 3e87f8e and 50422e8, 01:26:49Z and 01:28:10Z | none |
    | v0.3 | 7ad17a7, 02:45:52Z | 49cf530 and a808d95, 02:46:19Z and 02:48:15Z | none |
    | v0.4 | 59301ad, 05:02:19Z | 12daa72, 05:04:17Z | none |

- **Independence caveat (not a fitting leak).**
  - The v0.2 dev time groups include 2003, 2008, 2014, 2018 and 2023 (v0.3 sealed) and 2006, 2011, 2015, 2020 and 2024 (v0.4 sealed). I checked this against `results/data/v02_time_groups_dev_by_year.json`.
  - Both are disclosed before the run: RECORDS_PROTOCOL_v0.3.md:35 and RECORDS_PROTOCOL_v0.4.md:28. DECISIONS.md:143 (D-019) records it for v0.4.
  - The v0.4 sealed year 2024 is also the v0.1 heldout year.

## caught (firewitness/caught/)

- **Split.** `records.py:68-71` assigns sha256(id) mod 10 values 0-2 to dev and 3-9 to sealed. `truth.py:111` tags each truth fire with it.
- **Truth is read only by `pipeline.run_truth`.** It filters `tr.split == split` (`pipeline.py:107-127`), and the CLI exposes it as `truth dev|sealed` (`cli.py:20-21`). No rule module (scar.py, evidence.py, floor.py, run.py, standard.py) imports truth or mentions sealed.
- `fuelcheck.py:106-107` is a re-tabulation of the existing sealed run (commit 7987c70, after the freeze, with no rule change).
- **Not gated.** `truth sealed` has no once-only lock or confirm flag. Single opening is procedural only: ROUNDS_caught.md:4, CAUGHT_PROTOCOL.md:152.
- **v0.1 history.** The rules were frozen at 530a3d5 (21:44:09Z) and the sealed C2 was opened at 2fb5502 (22:50:35Z). After the opening, febec43 (process count), 4e663a0 and 54033af (memory/chunking) are engineering changes. 7af70d9 is new v0.2 code.
- **v0.2 history.**
  - The protocol (49ff332, 21:10Z) fixes the rules with "no dev rounds".
  - A1 (a52a525, 22:13Z) widened the sealed set by count only, before any look.
  - The results commit (7af8266, 01:26Z Nov 22) changes only `v02.py` (the sealed-set builder's dedup, disclosed as D-518, no rerun).
  - The sealed 2021 perimeters do not overlap the dev slices, which are 2018-2020 (`config/us.json` slices).
- **Verdict:** NO LEAK FOUND. The weakness is that the sealed run is not gated in code.

## live (firewitness/live/)

- **Split and fit.**
  - Fires alternate dev/test (`firelist.py:176`).
  - `fit_dev` uses dev fires only (`fit.py:317`), and so do the rounds (`rounds.py:24,84`). The threshold h comes from dev placebo series (`fit.py:93-101`).
  - k comes from Part A labels (`fit.py:235-254`). `k_from_labels` does not filter by split, which is a latent risk. The file actually used, `results/live/traceback_dev_A0_by_satellite.csv` (the default at `cli.py:32`), contains 196 rows, all dev. I checked this against `protocol/live_fires.csv`.
  - The frozen k=4.0 came from the dev rounds.
- **Replay gate.** `fit.py:271-273` refuses `--split test` without `--i-am-opening-the-sealed-test` (`cli.py:29,71`). Operational-product times (`i["op"]`) for test fires are read only inside this gated replay (`fit.py:274-299`).
- **E1 and h_A.**
  - The opener `pipeline.py:228-258` computes E1 on test placebos using `thr_dev` from dev placebos only (`pipeline.py:239,246`).
  - The released test onset labels use h_A from dev plus test placebos (`pipeline.py:238-240`). That is transductive and uses no fire outcome. It is disclosed in the docstring at `:228-229`.
- **v0.1 history.** detector_us.json was frozen in a629622 (00:01:26Z). Its sha256 (63bea29…) matches the file at HEAD, and the file has no later commit. Part A was opened at bc47acf (00:07:24Z) and Part B at ce34f07 (00:15:00Z). The only later detector change, 328d9a3, adds a v0.2 `cal` option that is off by default.
- **v0.2 history.** Settings were frozen in 89361ee (05:53:46Z, `config/traceback_v02_us.json`) and the test ran in e4fc767 (07:09:34Z). There is no live code change in between except d2eval.py, which arrived with 53b0d78 (Nov 22) and is not part of fitting. h_A comes from the 240 v0.1 fires, including the already-opened v0.1 test. The 100 v0.2 test fires are disjoint from them (overlap 0).
- **Verdict:** NO LEAK FOUND.

## smoke (firewitness/smoke/)

- No code reads `protocol/sequences_dev.txt` or `sequences_sealed.txt`: there is no grep hit in any .py file. `smoke evaluate` takes any list file (`cli.py:120`). Dev-only tuning is therefore procedural. The run driver is not committed.
- I recomputed the split rule from SMOKE_PROTOCOL.md:21: ranking the 48 sequences by sha256("smoke-v1|"+name) and taking rank mod 3 = 1 gives exactly the 16 sealed names.
- `results/smoke/dev_final.json` names no sealed sequence. Three sealed names appear in `s4_final.json` (S4, report-only, c63fcd6 at 22:05:05Z, after the sealed opening).
- **History.** params.py was last changed in e6c1e2d (20:34:07Z, "config v1 frozen", which also committed the lists). The sealed results came in 6c6e09a (22:03:53Z). There are no firewitness/smoke commits after 20:34Z.
- **Verdict:** NO LEAK FOUND. The isolation is procedural only.

## fuel (firewitness/fuel/)

- **Import graph.** I computed the transitive closure (AST, relative imports). Only cli, devloop, loop, grade and sealed reach grade, plots or metrics. agent, layers, runner, grid, areas, spread, fires, r3b, stretch, report, release, fetch/* and fires29/* do not.
- Only `plots.py:54,88` reads `RAW_ROOT/ldc`. `fetch/ldc.py` downloads the data.
- `tests/fuel/test_agent.py:90-101` enforces the import claim for 5 files only. The `plots.py:3` docstring cites a `tests/fuel/test_holdout.py` that does not exist.
- **Dev only.** `devloop.py:15` defaults to `DEV`. `loop.py:24` calls `devloop.run_dev`. The DEV and SEALED tile lists are disjoint (`areas.py:11-12`). `plots.load_table` (`plots.py:126-130`) and `grade.grade_tiles` (`grade.py:35`) raise on sealed tiles unless `allow_sealed=True`, which is passed only by `sealed.py:36`.
- **Lock.** `sealed.py:21-30` refuses if `sealed_opened.json` exists, or if the code hash or config hash differs from RULES_FROZEN.json. `runner.code_hash` covers agent.py, layers.py and grid.py (`runner.py:30-33`).
- **History.** Rules were frozen at 7f5dd5c (18:46:27Z) and the sealed areas were opened at 18:50Z (`sealed_opened.json`; commit 379b492 at 18:55:49Z). de3d058 (19:07:36Z) changed layers.py and runner.py to add `cutoff_year`, which defaults to None, for the 29-fire stretch only. This is amendment A2, disclosed at FUEL_PROTOCOL.md:164 as "no stretch result did [exist]". The stretch results came in da77fb2 (19:14Z). The sealed-area behaviour is unchanged.
- **Verdict:** NO LEAK FOUND.

## score (firewitness/score/)

- **Threshold.** `contract.py:24,35-36` allows only `max_f1_on_validation` or `fixed`. `card.choose_threshold` iterates `val_fires` only (`card.py:136-160`), and `build_card` scores `test_f` with that threshold (`card.py:232,247-248`). Climatology is fitted on `folds["train"]` (`baselines.py:58`). In the four published splits, train, val and test are pairwise disjoint (checked).
- **Negatives.** `negatives.sample` builds candidates only from the `ids` passed in (`negatives.py:29,71-75`). The CLI defaults to `--fold train` (`cli.py:86`, used at `:37-39`). Gate N5 passes `folds["train"]` (`gates.py:222,226,252`). The sampler cannot draw from test unless test is explicitly requested.
- **Leak check.** `leak.py:10-66` checks the declared horizon plus two behavioural AUC screens. `card.py:259-265` adds a training-provenance check that only catches overlap with test and relies on self-declaration (`trained_on_fires`, "not declared" otherwise; disclosed in ROUNDS_score round 4).
  - Caveat (disclosed): `leak.auc` 0.97→0.90 and `front_auc` 0.95 were tuned after seeing cheat and honest AUCs on gate fires that include the test fold (`gates.py:30-31` uses val ∪ test; ROUNDS_score rounds 1-2). Those limits therefore have no untouched evaluation.
- **Verdict:** NO LEAK FOUND for model fitting and thresholds. The leak-screen limits themselves were tuned on the test fold, which is disclosed.

## Cross-track: rule changes after a sealed opening

| Track / version | Frozen | Opened | Rule-file commits after the opening |
|---|---|---|---|
| records v0.1 | 69026c3 19:14:30Z | results b37f6f1 19:24:11Z | none until new v0.4 files |
| records v0.2 | eafeb99 01:25:48Z | 3e87f8e/50422e8 01:26-01:28Z | none |
| records v0.3 | 7ad17a7 02:45:52Z | 49cf530/a808d95 02:46-02:48Z | none |
| records v0.4 | 59301ad 05:02:19Z | 12daa72 05:04:17Z | none |
| caught v0.1 | 530a3d5 21:44:09Z | 2fb5502 22:50:35Z | engineering only (febec43, 4e663a0, 54033af) |
| caught v0.2 | protocol 49ff332 / A1 a52a525 | 7af8266 01:26Z Nov 22 | v02.py builder dedup only (D-518), no rerun |
| live v0.1 | a629622 00:01:26Z | bc47acf/ce34f07 00:07-00:15Z | 328d9a3 off-by-default option; detector_us.json unchanged |
| live v0.2 | 89361ee 05:53:46Z | e4fc767 07:09:34Z | none to fitting code |
| smoke v1 | e6c1e2d 20:34:07Z | 6c6e09a 22:03:53Z | none |
| fuel | 7f5dd5c 18:46:27Z | 18:50Z (379b492) | de3d058 stretch-only `cutoff_year` (A2, default off) |

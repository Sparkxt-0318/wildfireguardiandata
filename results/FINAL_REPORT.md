# firewitness: final report (orchestrator, 2026-11-22)

Six builder tracks (49 records, 50 caught, 51 live, 52 smoke, 53 fuel, 54 score) ran as separate cloud sessions and
merged through pull requests; track 55 audited the result from GitHub alone. This report points to the numbers; it
does not restate them where a results file already holds them. Independent check of every number:
`results/AUDIT.md` and `results/HEADLINE_NUMBERS.md` (auditor, PR #57).

## Releases

| tag | content |
|---|---|
| v0.1 (umbrella, main 3fc6ab0) | one zip per track; notes = `release/NOTES-v0.1.md` (headline page, layout D-015) |
| records-v0.1 to v0.4 | cleaning, links, IDs, perimeters; v0.2 time offsets and gazetteer; v0.3 swap check, suggested locations, scar flags; v0.4 pooled time calls |
| caught-v0.1 | labels and three-state tables for all US FPA FOD 2018-2020, scar pairs (`scar_pairs.zip`) |
| caught-v0.2 | flags only (D-021): the v0.2 tier failed its placebo gate and is not a verified tier |
| live-v0.1, live-v0.2 | onset labels and replay (v0.1, D2 headline added); trace-back v0.2 |
| smoke-v0.1, fuel-v0.1, score-v0.1 | as released by each track |

## Headline numbers

Lead labelling with sealed recall (caught v0.1, small fires under 300 acres, opened once; `results/CAUGHT_RESULTS.md`
"C2"): labelled 0.639 against standard 0.306 (+0.333, 0.308 to 0.358); verified-only 0.299 (-0.008 against standard).
Classes B, C and D pass; class A fails. **The auditor could not recompute this from release v0.1** (the sealed truth
set is not released), so it stands on the builder's own run.

Numbers the auditor recomputed from release v0.1 (`results/HEADLINE_NUMBERS.md`):

- Fires with no standard satellite label that now carry a verified label: **4,343** of 207,508 (US 2018-2020; S1 92,
  S2 1,648). Verified, probable and record-only stay in separate columns, never summed.
- Scar floor: Sentinel-2 2,345 m2 (0.58 acre). Landsat published as 5,277 m2; recomputes as 5,276 m2.
- Fires whose first label moved earlier: 45 of 240 (18.8 %, 14.3-24.2 %), median lead 42 min.
- Live detector before the operational GOES product: 7 of 97 sealed fires (7.2 %, 3.5-14.2 %). Gate D1 failed; the
  detector is closed as a negative result. The 24 h unattended signed run (D2) passed, 288 of 288.
- Records: 888 duplicates merged into 883 fires; 2,660,495 permanent IDs; values altered in 64,873 records (2.44 %).
- Smoke sealed placebo 0.8 % (0.0-2.4 %); first smoke +180 s after the human label in 13 of 14 sequences.
- Fuel: 6.74 % of 40 M sealed cells called contradicted.
- Scoring: no number recomputable from the release.

## Failed gates

Every failed gate is listed on the v0.1 release page (`release/NOTES-v0.1.md`, "Every failed gate") and again in
`results/HEADLINE_NUMBERS.md`. In short: records R1 (FIRED link; recall target), R3(a) time and unit planted errors,
R3(c) do-no-harm budget, v0.3 G2 gazetteer, v0.4 A1 AM/PM; caught C1 probable guard (S1, S3), C2 class A, v0.2 C1
(1.80 %) and v0.2 C2 class A; live D1, v0.2 E2 and V2; smoke S2 dev placebo, S1 targets, S5 window sensitivity; score
N5. Fuel failed no gate.

## What the audit found (results/AUDIT.md, failures first)

- 15 published numbers do not recompute (caught 2, live 2, records 1, score 10); most numbers in every track cannot
  be recomputed from release v0.1 because the data behind the gates is not released.
- On a clean clone, `records link / ids / report` and `live replay` fail (builder-local paths; missing GOES cache).
  The auditor documented this in the README; the code is not fixed. `caught floor` prints a floor 39 % lower than the
  published one (different `n_min`).
- `records revert` is byte for byte only when the table has its own id column; duplicate ids crash `clean`;
  impossible values (latitude 95, month 13) are not flagged.
- The core evidence combination counts an exact copy of a source as an independent witness.
- Two released patch files fail the patch checker (records v0.3 scar flags, records v0.2 gazetteer dev patches).
- Protocol order: no protocol was committed after its track's first result. Amendments that followed a result are
  listed (score N3 limit D-013; smoke keep rule and edge metric D-012; records R3(c) split; records v0.3/v0.4 sealed
  years D-019; fuel loop D-011; live amendments 4-6; caught D-518). No key or token was found in history.

These are reported, not fixed: the builders are closed (D-018) and reachable for audit fixes only.

## Open findings

- **Records: the OK Forestry -12 hour shift is unexplained.** Sealed groups (2016, 2020, 2022) show a fixed -12 h
  shift; the AM/PM hypothesis was tested in v0.4 and rejected (sealed gain -0.313, -0.358 to -0.272). It stays open.
- Caught v0.2: 3,061 WFIGS 2021 perimeters without an IRWIN id were never opened (D-518); available for a further
  sealed check.
- Smoke: first smoke takes the largest smoke chain, not the earliest (auditor: +60 s median with the earliest chain).

## Housekeeping left for the owner

- **Branch `coord` still exists** at 92ed749. This session's git proxy refused the ref deletion (HTTP 403, D-022);
  delete it from the GitHub branches page. The local copy and a tarball backup are kept on the orchestrator side.
- **Stray branch `score/live-onset`**, made by track 54 outside its own branch; it was outside the orchestrator's
  push scope and is left for the owner to delete.
- Remaining track branches (`track/*`), `live-log` (the signed D2 log, keep) and the orchestrator branch can be
  deleted or kept as history.
- The score gates file `gates_wildfirespreadts.json` was moved into `results/fuel/` by a fuel commit (82f1e13); score
  restored a copy under `results/score/`. Both copies are on main; the score copy is the one SCORE_RESULTS.md cites.
- Decision ids D-501 to D-516 were used by both caught and live in `DECISIONS.md`; caught tagged its entries
  "(caught)" from D-510 on and live's last one is "D-516 (live)". Read the earlier untagged ones by their text.

## Decisions

Orchestrator decisions D-001 to D-022 are in `DECISIONS.md`. The ones that change how results read:

- D-008: lower-cost models for subagents.
- D-010 and D-020: releases via a workflow; subfolders zipped; re-release mirrors the folder and rewrites the notes.
- D-012 and D-013: limits or rules changed after a result (smoke, score), recorded and flagged on the release page.
- D-014 to D-018: the user's instructions on v0.2 work, the headline layout, records v0.3, the caught fuel check and
  priorities.
- D-019: records v0.4 sealed years had been v0.2 dev years.
- D-021: caught-v0.2 released as flags because its tier failed C1.
- D-022: end sequence and the refused coord deletion.

Track decisions (D-1xx records, D-5xx caught and live, D-52x smoke, D-53x fuel, D-54x score) are in the same file.

## Korea run (existing stubs, untested)

No Korea data was fetched and no Korea gate was run. What exists and the commands that would start a run:

- **Fuel** (`firewitness/fuel/config/kr.json`, Korea Forest Service forest type map translated to fuel groups;
  marked STUB - UNTESTED):

  ```bash
  firewitness fuel check --region kr --map M22 -- "126.5,35.0,127.5,36.0"
  ```

  The `--map` choices are the US LANDFIRE maps (M22, M16); the Korea map in `kr.json` (KFS_FTM) is not yet wired
  into `--map`, so this needs that one code change before it reads Korean data.

- **Records** (`--region` selects `firewitness/records/config/<region>.json`; only `us.json` exists):

  ```bash
  cp firewitness/records/config/us.json firewitness/records/config/kr.json
  ```

  Edit the country values in `kr.json` (bounds, time zone, unit rules, sources), then:

  ```bash
  firewitness records clean --input kr_fires.csv --table generic --region kr --id-col <id column> --out out_kr/
  ```

- **Live** (`firewitness/live/config/kr.json`: Himawari-9 AHI and GK-2A AMI over Korea, `tested: false`): the live
  CLI has no `--region` option and reads `config/detector_us.json`; a Korea run needs a Korea detector config, a
  `--region` switch in `firewitness/live/cli.py`, and the GK-2A reader marked missing in `kr.json`. The live detector
  itself is closed as a negative result (D1), so only trace-back would be worth porting.

## Process record

- Supervision: hourly passes, PROGRESS sections every 6 hours (`results/PROGRESS.md`), depth checks on every DONE,
  merges only with CI green and scope checked.
- Restarts: none needed in the last day. Builder sessions are idle and reachable for audit fixes.
- No result file was changed by the orchestrator; every results change was a dated addition by its track.

# Independent audit of firewitness v0.1 (track 55)

Audited: `main` at `3fc6ab0` (the commit tagged `v0.1`), GitHub release `v0.1` (six zips and `SHA256SUMS.txt`), the
later releases where a check needed them, and the full git history. Date: 2026-11-22. The auditor did not build the tool
and worked from GitHub alone, as an outside user would: no local folder of the builders and no keys. Nothing in the
tool or its results was changed. The only edit outside `results/AUDIT.md`, `results/HEADLINE_NUMBERS.md` and
`results/audit/` is a README fix for install errors (section 1).

Detail tables and the scripts behind every check are in `results/audit/` (`step2_<track>.md`, `step4_leaks.md`,
`scripts/`). `<work>` in those files stands for the auditor's scratch folder.

Status words in this file: **MATCH** (recomputed from release v0.1 files and equal at the published rounding),
**MISMATCH** (both values given), **CANNOT RECOMPUTE** (a needed file is not in release v0.1), **PARAMETER** (a limit
or setting, not a result).

---

## Failures first

### A. Numbers that do not recompute (step 2)

| track | results line | published | recomputed from release v0.1 | note |
|---|---|---|---|---|
| caught | CAUGHT_RESULTS.md:73 | PERIM in 1,126 of the 4,795 S2 verified records | PERIM in 2,528 of 4,795 | 1,126 is the count among the 1,648 verified records with no standard label: numerator and denominator come from different sets. The S3 sentence (line 129, 5,169 of 13,793) is right. |
| caught | CAUGHT_RESULTS.md:362-363 | Landsat scar floor 5,277 m2 | 5,276 m2 (5,276.47) | the release stores 5,276.5; 5,277 is a double rounding. |
| live | LIVE_RESULTS.md:10 | 138 fires seen by GOES-18 | 140 | `onset_labels.csv` and `traceback_by_satellite.csv` both give 140; the file's own E1 denominators (76 + 64) also sum to 140. |
| live | LIVE_RESULTS.md:50 | E2 "dev alone 1 of 4" | 2 of 5 in the released labels | 1 of 4 comes from a dev-only run with dev thresholds that is not released. |
| records | RECORDS_RESULTS.md:11, 67 | value-level share "0.05 % without name placeholders" | 0.035 % (922 records that are not FIRE_NAME placeholders) or 0.033 % (the 888 duplicate merges) | no reading of the patch file gives 0.05 %. |
| score | SCORE_RESULTS.md:62-66 | caught S1 addition: rows 13,697; no_fire rows 3,981; cell-days 235.2 M; fire 57.1 M; unknown 160.0 M; extent-sized no_fire 72.0 M; sampler positives 1,996,635; verified negatives 2,024,742; match "exact" 16 %; "same-danger fallback" 55 % | 13,695; 3,979; 235.5 M; 57.3 M; 160.1 M; 72.2 M; 1,999,078; 1,971,110; 15 %; 56 % | the card was built from `results/caught/states_S1.parquet` (repo, not released), which has 2 more no_fire rows than the released states file for the same 10,360 records. |

Adjudicated as MATCH after the checker run (see `results/audit/step2_records.md`, last section): RECORDS_RESULTS.md
lines 11 and 55 (64,873 records, 2.44 %) and line 57 (172,824 cosmetic). They follow the R3(c) amendment's own
definition (duplicate merges count as altered; mojibake counts as cosmetic). Line 26 is inconsistent with that
definition, because it calls the 2 mojibake patches value-level.

### B. Headline gates that cannot be checked from release v0.1

Release v0.1 does not contain the data behind most gate numbers. An outside user cannot recompute:

- **caught C2, sealed small-fire recall** (the labelling headline). The sealed truth fires (FRAP and NIFC perimeters),
  their labels, their standard-label footprints and the cluster ids are not released. The class counts are internally
  consistent (206 + 1,029 + 1,857 + 618 + 1 = 3,711).
- **caught C1, placebo rates** (verified and probable). There are no placebo rows in the release.
- **records R1, link precision, recall and F1** (dev and sealed), **R3(a)** planted errors, **R3(b)** distinct pairs,
  **R6** and created perimeters, and **the published hand cleaning reproduced** (precision, recall, run time). The
  reference links, the sealed test records, the planted sets and the raw ICS-209 patches are not released.
- **live D2, 288/288 signed records**, false alerts per day and the budget curve. These exist only as values inside
  `replay_test.json`; the placebo series are not released.
- **smoke S1 known truth** (opacity MAE 0.143, edge error 10.01 / 7.90 px, detection 79.3 %), **S4**, **S5** and every
  dev number, including the failed S2 dev placebo (7.1 %). The composites, raw frames and dev labels are not released.
- **fuel F1 (7.91 [6.36, 10.03]) and F2 (0.92 %)**. No field plot is in the release. The 29-fire stretch is not
  checkable either.
- **score N1 to N5**. The score release holds split files only; no score card, gate output or prediction is released.

In all six results files, CANNOT RECOMPUTE outnumbers MATCH (section 2).

### C. Install and quick start (step 1)

1. `firewitness records link`, `records ids` and `records report` (all three in the README) fail on a clean clone with
   `FileNotFoundError` / `sqlite3.OperationalError`. They read a builder's local folder (`/home/user/wildfire 3 (1)`,
   overridable by the undocumented `FIREWITNESS_ROOT`). The README did not say so. *Fixed in the README by this PR.*
2. `firewitness live replay` fails on a clean clone. Outside the repository root it raises `FileNotFoundError:
   protocol/live_fires.csv` (relative path). From the root it raises `ZeroDivisionError` in `fit.clustered_rate`, because
   no GOES series are cached and the code does not say that `live traceback --extract` must run first.
   *Documented in the README by this PR; the crash itself is not fixed.*
3. `firewitness fuel check <fire name>` fails: it needs `firewitness_raw/fires29/<fire>/meta.json` from the builder's
   folder. The box example in `docs/FUEL.md` (`fuel check "-115.2,40.4,-114.8,40.7" --map M16`) fails in argparse
   because the box starts with a minus sign; it works with `--` before the box. *README note added.*
4. The README's `records clean --input table.csv` has no example file. The score track has no extra (`pip install
   -e ".[score]"` warns "does not provide the extra 'score'"). *README note added.*
5. `firewitness caught floor` prints a scar floor of 1,440 m2 (Sentinel-2) and 3,240 m2 (Landsat) at T = 0.10. Its code
   calls this "the published floor table" (`firewitness/caught/floor.py:182-198`, default `n_min=4`). The labels,
   the data card and CAUGHT_RESULTS.md use `n_min=8`: 2,345 m2 and 5,276 m2. A user who runs the command gets a
   floor 39 % lower than the published one.

### D. What the tool did when pushed (step 5)

1. **Revert is not byte for byte when the input has no `rid` column.** `records clean` adds a `rid` column of row
   numbers, and `records revert` returns the table with that column. The tool prints "equals the input file byte for
   byte: False". This happened on every table without an id column: plain CSV, a semicolon CSV and a UTF-16 file.
2. **Duplicate record ids crash `clean`** (`ValueError: cannot reindex on an axis with duplicate labels`) once any
   patch applies. `patches.jsonl` is already written, but `clean.csv` is not. When no patch applies, duplicate ids are
   accepted silently.
3. **Malformed CSV** (an unclosed quote, ragged rows, an empty file) stops with a raw pandas traceback, not a message.
4. **Impossible values are not flagged** by `records clean`: latitude 95, longitude -200, size 1e309 and month 13 pass
   with no patch and no flag, both as `--table generic` and as `--table fpafod`. Negative size and containment before
   discovery are flagged (`--table fpafod`). A positive longitude in California is not flagged either: the CLI's
   `clean` runs only tool 1 (values), although its help says "values, location/time, duplicates".
5. **A source that copies another exactly** is counted as an independent witness by `core.evidence.combine`. One
   witness (m 0.9, u 0.1) gives 0.90, "undecided"; adding an exact copy of it gives 0.988, "yes". Nothing in core
   detects the dependence. The duplicate finder does link the copied record (posterior 0.9998) when the data hold
   other duplicates.
6. **Duplicates depend on the fit data.** The duplicate finder fits without labels. Fitted on 9,517 real CA 2018
   locations from the release with no duplicate in them, it linked nothing. Both the true duplicate (same name, 2 km,
   12 h) and the exact copy came out "undecided" (0.11, 0.86). Fitted on the same records plus 2 % planted
   cross-source duplicates, it linked all 190 planted pairs, the 2 km / 12 h same-name report (0.975) and the exact
   copy, and linked none of 1,705 other pairs. It still missed an unnamed duplicate at 2 km / 12 h with sizes 120 vs
   100 acres (0.002, "no link").

### E. Patch files (step 6)

| release file | independent checker (`tests/records/independent_checker.py`, full mode, public FPA FOD 2026-06-15 GeoPackage, same SHA-256 as the patch header) |
|---|---|
| records-v0.1 `patches_us.jsonl.gz` (353,536) | **PASS**: 0 violations in every hard check; value-level 2.44 % (64,873), cosmetic 6.49 % (172,824) |
| records-v0.2 `time_offset_patches_dev_fod.jsonl.gz` (1,078,543) | **PASS** on hard checks. Soft: 1,028,063 new values the checker cannot parse as dates and an unknown rule name (disclosed in D-109). These dev patches alter **36.7 %** of FPA FOD records (977,583). |
| records-v0.3 `scar_size_flags.jsonl.gz` (121) | **FAIL**: 121 hard violations (unknown field `flag_scar_size`). These are flags written in patch format. |
| records-v0.2 `v02_gazetteer_dev_patches.jsonl.gz` (575) | **FAIL**: no header line (no chain, no input hash); 575 patches write `old` as `null` instead of the format's missing marker. |
| records-v0.2 `time_offset_patches_dev_ics.jsonl.gz` (39,131), records-v0.3 `gazetteer_suggestions_patches.jsonl.gz` (816) | **NOT CHECKABLE**: the checker knows only FPA FOD record ids, so every ICS-209 id is "unknown". No independent checker exists for ICS-209 patches. |

### F. Protocol and history violations (step 3)

1. **score:** the leak limit `leak.auc` was lowered from 0.97 to 0.90 after round 0 showed N3 failing on the same
   planted cheat N3 is then reported against. All five amendments were committed together after the first results
   (`9e5e7e6`; DECISIONS D-013).
2. **smoke:** amendment A3 (`538e61e`) loosened the keep rule after round R1 had run, from "S1 improves and S2 does not
   worsen" to "S1 improves or S2 false frames improve". Amendment A2 item 3 (`e7ef0bd`) narrowed the S1 edge-error
   definition after a dev round had shown whole-frame errors of 50-65 px (D-012).
3. **records:** the R3(c) budget was split into "value-level" and "cosmetic" after the first FPA FOD counts were seen
   (`fc03c89`). The release notes themselves say so: "that split was decided after counts were seen". Before any
   tuning, one aggregate score of tool 2 against the published cleaning was computed on all years, sealed test years
   included (`5329e2a`, logged in the amendment table).
4. **records v0.3 and v0.4:** the "sealed" years had been dev years in v0.2, so they are not new sealed data (protocol
   v0.4 and D-019).
5. **fuel:** improvement rounds 2-12 were threshold probes from a per-rule precision table, not changes from reading
   wrong verdicts (D-011). Amendment A2 (`de3d058`) came after the sealed results, for the stretch only.
6. **live:** amendments 4 and 5 were written after looking at dev outcomes, and amendment 6 starts the improvement
   rounds although the first version had not passed, as §9 requires. Each is disclosed and dev-only; the sealed test
   was opened once, with the detector frozen 14 minutes earlier (`a629622` before `ce34f07`).
7. **caught v0.2:** the sealed set that ran was 795 perimeters, not up to 1,500, because of an id de-duplication bug
   found after the run (D-518). The sealed v0.1 recall was re-tabulated by fuel type after the opening (`7987c70`).
   That is a post-hoc breakdown, not a re-run.

No protocol was committed after its track's first result (section 3).

---

## 1. Install and time to first result (step 1)

Clean environment: a new container, Python 3.13, `git clone https://github.com/Sparkxt-0318/wildfireguardiandata`
(14 s), a new venv, then the README's commands.

| step | command | outcome | machine time |
|---|---|---|---|
| install | `pip install -e ".[dev,records]"` | ok | 9 s |
| extras | `.[caught]`, `.[live]`, `.[smoke]`, `.[fuel]` | ok | 21 s, 3 s, 8 s, 3 s |
| extras | `.[score]` | warning: extra does not exist (the README does not list it) | - |
| help | `firewitness --help` | ok, 9 command groups | <1 s |
| records quick start | `records clean --input table.csv --table generic --out out/` and `revert` | ok on a 3-row CSV the auditor wrote (the README ships none); revert byte for byte when the table has `rid` | first result 0.5 s after install (about 25 s from clone) |
| records | `records link --task fod_mtbs`, `records ids`, `records report` | **FAIL**: missing builder files | - |
| caught | `caught floor` | ok (prints a floor table that disagrees with the published floor, C.5) | 0.1 s |
| caught | `caught run` | not attempted: needs FPA FOD plus imagery for hours | - |
| live | `live run --hours 0.2 --no-sign` | ok: first cycle, 0 candidates | 290 s |
| live | `live replay --split dev` | **FAIL** (C.2) | - |
| live | `live traceback --extract` (one dev fire) | ok; same label as the release (section 6) | 211 s |
| smoke | download one public FIgLib sequence (2 s), `smoke label` | ok, first smoke +720 s | 26 s |
| video | `video render --layout a` | ok, 1920x1080, 24 s, decodes to the end | 89 s |
| fuel | `fuel check --map M16 -- "-115.2,40.4,-114.8,40.7"` | ok (layers fetched on demand): consistent 1,047,124, contradicted 10,618, stale 596, unknown 98,858 | 77 s |
| fuel | `fuel check Boundary` (fire name), documented box form without `--` | **FAIL** (C.3) | - |
| score | `score build --adapter synthetic`, `splits make`, `contract-template`, `score gates` | ok; N1-N5 pass on synthetic data | 1 s to the first result, 15 s for the gates |

## 2. Recompute from release v0.1 (step 2)

Release v0.1 was downloaded from GitHub and all six zip checksums match `SHA256SUMS.txt`. Each zip is byte-identical
to `release/<track>-v0.1/` on main. Inner SHA256SUMS exist for caught and score only; both pass.

| track | results file | MATCH | MISMATCH | CANNOT RECOMPUTE | PARAMETER | unit counted |
|---|---|---|---|---|---|---|
| records | RECORDS_RESULTS.md | 27 (+4 equal to `run_summary_us.json`, self-reported) | 1 | 58 | 4 | rows (claim groups) |
| caught | CAUGHT_RESULTS.md | 282 | 2 | 382 | 25 | distinct values |
| live | LIVE_RESULTS.md | 100 | 2 | 141 | 11 | numbers |
| score | SCORE_RESULTS.md | 55 | 10 | 136 | 10 | numbers |
| smoke | SMOKE_RESULTS.md | 22 | 0 | 94 | 7 | rows |
| fuel | FUEL_RESULTS.md | 14 | 0 | 35 | 9 | rows |

What matches (selected): the caught counts by slice and size class (S1, S2, S3, with Clopper-Pearson intervals), the
S3 counts by class and year, the record-only reasons, and the Sentinel-2 scar floor. Every record has exactly one tier
and none is dropped. In live: D1 7 of 97 (7.2 %, Wilson 3.5-14.2); the median lead -inf with bootstrap upper -100 min
(seed 0, not stated in the results file); Part A 45 of 240 earlier (18.8 %, 14.3-24.2) and the four lead rows; the
supplement; E2 test 3/3; all detector hashes. In records: 2,661,383 records, 2,660,495 fires, 888 merged records, 2
splits, 1,425 complex parents; patch counts by rule; 0 FPA FOD location and 0 time repairs; perm_ids are unique and
follow the stated rule. In smoke: sealed S2 4 of 503 frames (0.8 %, 0.0-2.4); sealed S3 13 of 14 detected, median
+180 s. In fuel: the sealed verdict shares over 40 M cells, the 29-fire set and the suggestion counts. In score: the
split files and their self-hashes, and the live adapter counts.

Other data problems found while recomputing (details in the step 2 files):

- The released `score-v0.1/SCORE_RESULTS.md` is lines 1-87 of the main file; main adds lines 88-94 (a dated addition).
  The smoke and fuel copies equal main.
- live: 3 of the 7 D1 "earlier" fires have lead +inf (the operational product never detected them in the window).
  The results text does not say so. Other bootstrap seeds move the D1 median's upper bound to -110 min.
- smoke: first smoke is the first frame of the largest smoke chain, not the earliest one. In 9 of 13 detected sealed
  sequences, smoke-classed pixels appear before the reported frame. With the earliest chain, the sealed median would
  be +60 s and 38 % earlier than the human label, instead of +180 s and 0 %.
- fuel: all released sealed manifests carry code hash `65aa8064...`, while `RULES_FROZEN.json` carries `226b82c4...`
  (disclosed). The stretch reports 7 better and 20 worse against n = 28, which leaves one fire unaccounted for.
- caught: record `FOD400626469` has an undocumented reason "no_clear_look (read error)". 3,484 searched records carry
  empty fire / no-fire / unknown areas. The class A bound is "under 0.26 acre" on line 152 and "under 0.25 acre" on
  line 365.
- records: one fire has state `ok` (lower case). Fid 96931 has year 1996 but ID date 1995-12-31, because a merged
  cluster takes its earliest day. In 9 of the 888 duplicate patches, `cluster_size` disagrees with the crosswalk. 31 of
  the "name" placeholders are FIRE_CODE and 3 are LOCAL_INCIDENT_ID.

## 3. Git history (step 3)

The audit used the full history (732 commits on `main`, the track branches, `live-log` and the other published
branches; the coordination branch was excluded as the brief says). A shallow clone shows misleading root commits;
use a full clone.

**Protocols before results.** Every protocol was committed alone, as an ancestor of its track's first result commit:

| protocol | commit (UTC) | first result-path commit of the track | in order |
|---|---|---|---|
| RECORDS_PROTOCOL.md | `a9bff75` 11-20 17:15:54 | `798c1fc` 17:43:28 (tool 2 findings) | yes |
| SCORE_PROTOCOL.md | `dbce880` 17:31:56 | `eb8df15` 17:46:41 | yes |
| SMOKE_PROTOCOL.md | `f68e7ed` 17:36:46 | `635060c` 18:32:21 | yes |
| CAUGHT_PROTOCOL.md | `a241760` 17:39:50 | `0003c63` 18:30:15 | yes |
| LIVE_PROTOCOL.md (+ fire list and splits) | `58958d1` 17:42:52 | `26deb2c` 18:19:50 | yes |
| FUEL_PROTOCOL.md | `14e2efe` 17:47:11 | `7f5dd5c` 18:46:27 | yes |
| RECORDS v0.2 / v0.3 / v0.4 | `88466d1` 11-21 01:09 / `7f7efa2` 02:34 / `a8c344e` 04:58 | v0.2 dev runner `13fb833` 01:24 / v0.3 `aa75259` 02:43 / v0.4 `59301ad` 05:02 | yes |
| LIVE v0.2 (+ test set) | `03441b2` 04:59 | later commits | yes |
| CAUGHT v0.2 | `49ff332` 21:10 | `7af8266` 11-22 01:26 | yes |

**Records error-finding before the published cleaning.** Yes by commit order. `798c1fc` (17:43:28, findings on the raw
ICS-209 tables, patches and summary) is an ancestor of `5329e2a` (17:44:33, the score against the published cleaning).
The proof is weaker than it looks, for three reasons:

- the two commits are 65 seconds apart, so the comparison must have been prepared before the findings were committed;
- the comparison code (`firewitness/records/eval_published.py`) was first committed at 18:43 (`a2fdf3b`), an hour
  after the score it produced;
- the amendment logged in `5329e2a` says an aggregate first-look score against the published cleaning was computed on
  all years, sealed years included, before any tuning.

Git proves commit order, not reading order.

**Every amendment** (the "followed a result" column combines git (result files present in the parent commit) with the
amendment's own text):

| protocol | amendment | commit | followed a result? |
|---|---|---|---|
| RECORDS | first-look aggregate score on all years (no rule change) | `5329e2a` | yes: aggregate on sealed years seen |
| RECORDS | R3(c) cosmetic split; distinct-pair test; reference-clean limit | `fc03c89` | yes: first FPA FOD run seen |
| RECORDS | pre-registered 200-fire perimeter sample | `9a1391a` | after v0.1 results; before the sample was drawn |
| RECORDS v0.2 | time estimator replaced; pooled level; decision margins | `b492ed2`, `4040062` | yes, dev only; before sealed |
| RECORDS v0.3 | H2 made precise; H2 dev result; gazetteer radii; erratum | `aa75259`, `29f455d` | dev only; the erratum (`29f455d`, 02:57) came after the v0.3 sealed opening (02:48) and corrects a dev count |
| RECORDS v0.4 | dev results pooling and AM/PM | `59301ad` | dev only; sealed years were v0.2 dev years |
| CAUGHT | A1 (night look scope, no GOES FDC, no FireCCI51, truth dates, Landsat 7) | `2a90cfd` | no |
| CAUGHT v0.2 | A1 sealed set widened to all US WFIGS 2021 | `a52a525` | after v0.2 S3 placebo results; before sealed |
| LIVE | 1 cloud-edge buffer, scene filter | `a50e6be`, `86c5748` | one dev fire's placebo and own S seen |
| LIVE | 2 lower-case IRWIN ids | `a50e6be` | no (representation) |
| LIVE | 3 two-witness rule, episodes, clustered counting, recent-fire mask | `604b412`, `7e6f92d` | one dev fire's placebo seen |
| LIVE | 4 Part A variants | `6e80187` | yes: first dev run on 11 fires |
| LIVE | 5 cloud rule (fires are not clouds) | `8b1a950` | yes: dev outcomes |
| LIVE | 6 rounds after a failing first version | `62e8805` | yes: first version failed D1 on dev |
| LIVE v0.2 | A1 smoke cloud mask and plume cap (best of 18 on dev) | `07031ff` | yes, dev only |
| SMOKE | A1 human labels found | `f618cdd` | no |
| SMOKE | A2 S1-lite, Pyro background, S1 edge window, pre-loop development | `e7ef0bd` | yes for item 3 (D-012) |
| SMOKE | A3 keep rule | `538e61e` | yes: after R1 (violation, F.2) |
| FUEL | A1 disturbance codes dropped | `10fbb6a` | no |
| FUEL | A2 stretch event cutoff | `de3d058` | after sealed results; before the stretch result |
| SCORE | 1-5 (leak limits, trained_on_fires, clarifications, N1 wording) | `9e5e7e6` | yes: all after the first results (violation, F.1) |

**Sealed openings.** Each sealed set has one opening commit: records v0.1 `b37f6f1`, v0.2 `50422e8`, v0.3 `a808d95`,
v0.4 after `59301ad`; fuel `379b492`; smoke `6c6e09a`; caught `2fb5502` (v0.1) and `7af8266` (v0.2); live `bc47acf`
and `ce34f07`. No rule or parameter file of the same version changed after its opening (`results/audit/step4_leaks.md`).

## 4. Leaks and keys (step 4)

Read during fitting (full table with file:line in `results/audit/step4_leaks.md`):

- **records:** no sealed year or sealed record is read by any fitting path. The link and duplicate thresholds and the
  per-task settings were tuned on dev F1 against the dev published links. That is supervised dev tuning; "without
  labels" holds only for the m/u fit. Possible leak, disclosed: the ICS-209-PLUS to FIRED candidate pool is built from
  the published links (`link_tasks.py:79`).
- **caught:** no leak found. Truth fires are read only by `run_truth`. The sealed run has no lock or confirm flag, so
  "opened once" rests on procedure.
- **live:** no leak found. Fit and rounds use dev fires only; the test replay needs `--i-am-opening-the-sealed-test`;
  test E1 uses dev placebo thresholds. `detector_us.json` is unchanged since it was frozen.
- **smoke:** no leak found, by procedure only: no code reads the sequence lists. The protocol's hash split
  reproduces the 16 sealed names.
- **fuel:** no leak found. Only the grading modules reach the plots, and plot loading refuses sealed tiles. The test
  cited in `plots.py:3` (`test_holdout.py`) does not exist.
- **score:** no leak found. The threshold is chosen on validation fires; negatives come from the given fold. The leak
  screen limits were tuned after gate results on validation and test fires were seen (F.1).

**Keys.** All 2,168 blobs in the full history were scanned (`results/audit/scripts/keys/scan.py`) for Hugging Face,
GitHub, JWT, AWS, Google, Slack, OpenAI/Anthropic, private-key, URL-credential and Bearer shapes, key/token/secret
assignments, FIRMS-style 32-hex assignments and long base64. No key or token was found. The only hits are public
Sigstore signing bundles in `live/log/` (base64 certificates and signatures), parquet bytes and one line of code.
Every committed version of the briefs carries `<REDACTED:...>` in place of the three key values; no `keys.env` or
`.env` file was ever committed. The briefs contain an account user name, which is not a credential.

## 5. Trying to break it (step 5)

| input | what the tool did |
|---|---|
| malformed CSV (unclosed quote, ragged rows, empty file, UTF-16 bytes, semicolon separator) | tracebacks for the first three. UTF-16 and semicolon files were read as one text column with 0 patches, and revert was not byte for byte (D.1). |
| impossible values (lat 95, lon -200, size 1e309, month 13; positive longitude in CA) | not flagged (D.4) |
| duplicate record ids | crash once a patch applies (D.2) |
| already-clean data (`clean` on its own `clean.csv`) | 0 patches, 0 flags (idempotent) |
| two different fires, same day, 2.5 km apart, different names and sizes | kept apart (posterior 0.03 and 0.00 in the two fits). At 4 km they are not even a candidate pair (3 km radius). Unnamed 0.1-acre pair at 2.5 km: "undecided" (0.32) without planted duplicates, "no link" (0.03) with them. |
| one fire reported twice, 2 km and 12 hours apart | same name and size: "undecided" (0.11) when the fit data hold no duplicates; **linked** (0.975) when they do. No name, sizes 120 vs 100: missed (D.6). |
| a source that copies another exactly | evidence combination counts the copy as a second witness, 0.90 becomes 0.988 and "undecided" becomes "yes" (D.5); the duplicate finder links the copied record when the data hold duplicates (0.9998) |
| smoke-free sequence with fast cloud (40 real pre-ignition frames, played forward and back, a synthetic bright cloud bank crossing the sky at 1/6 frame width per minute from -600 s) | no smoke and no placebo smoke frames; 2 regions classed as cloud. The rule that fired reads "...and drifts slowly is cloud", although this cloud moved fast. The same frames without cloud give no region at all. |
| a fuel map that is correct (built per cell from the same independent layers: water 98, snow 92, developed 91, crop 93, barren 99, shrub on NLCD 52, timber where tree evidence agrees, grass elsewhere; same box as the quick start, LF2016 grid) | contradicted 0, unknown 0, consistent 1,156,600; only staleness fired (S1 562, S2 34 cells: fire and tree loss after the map year, true for any map of that date). The original LF2016 map in the same box: 10,618 contradicted. This shows no false contradictions on an agreeing map; it is not an independent test of correctness. |

## 6. Patches, revert and clips (step 6)

Patch checker: section E above. Revert:

- On CSV input, `records revert` restored the 3-row example and every malformed or odd input that had an id column
  byte for byte (sha256 equal). It did not on inputs without one (D.1).
- National: the public FPA FOD table (2,661,383 records, loaded exactly as the tool loads it) with all 353,536
  released v0.1 patches applied, then reverted. The canonical serialisation hashed the same before and after
  (`7f1dca8f...`; `results/audit/scripts/break/revert_national.py`, 168 s). 352,648 cells changed and every one has
  a patch; the 888 duplicate patches add the `dup_of` column. One caveat: the tool's default canonical hash
  (`frame_ops.sha256_frame`, latin-1) cannot serialise the national table at all. FOD_ID 1397009 has the fire name
  `D╔J└ VU` (U+2554), so the hash was taken in UTF-8, an option of the same function. The R3(e) claim in
  RECORDS_RESULTS.md was made on a 60,000-row slice. `PatchSet.read` does not open the released `.jsonl.gz`
  directly; it must be decompressed first.

Clips: all 18 MP4s in `clips/` were decoded to the last frame with `ffmpeg -f null` (no decoder error, exit 0). 17 are
24.0 s (720 frames at 30 fps) and `smoke_full_20160604_smer-tcs3.mp4` is 33.5 s (1,005 frames); all are 1920x1080
H.264. The HPWREN credit is burnt into the smoke frames checked. `contact_sheet.png` is present.

Live trace-back from a clean clone (one dev fire): `firewitness live traceback --extract` read the public GOES series
and finished in 211 s on `2023-AZCNF-000223` (Zulu, AZ). The label agrees with the released `onset_labels.csv`: "no
earlier onset (anchor kept)", the same T0 (2023-04-20T20:39Z), satellites G16+G18. The run used the default variant
A0; the released labels used A2 (D-511). The column order of the output differs from the released file.

## 7. Decisions taken by the auditor

1. "Release v0.1 files only" means the six zips of the GitHub release `v0.1`. Numbers from later releases (records
   v0.2-v0.4, live v0.2, caught v0.2) are CANNOT RECOMPUTE, as are numbers in repo files that are not in the release.
2. Interval rule: MATCH only when the stated method (and seed, where it is in the code) reproduces the published
   endpoints at the published rounding.
3. Records lines 11, 55 and 57 were reclassified from MISMATCH to MATCH under the protocol's own R3(c) definition
   (section A).
4. The headline page shows only numbers that matched. The sealed recall the user asked to lead with cannot be
   recomputed from the release, so its slot on the page holds the failed gate with no number. The counts-by-slice
   table counts as one headline item.
5. The patch checker was run against the public FPA FOD GeoPackage downloaded from the USDA Forest Service Research
   Data Archive. Its SHA-256 equals the input hash in the patch header.
6. One pull request from `track/audit` carries this file, the headline page, `results/audit/` and the README install
   notes. No code or result file was changed.

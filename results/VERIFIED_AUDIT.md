# Verified-tier audit (caught v0.1, slice S3): what the verified placebos and a sample of verified records show

Rubric and procedure: `protocol/VERIFIED_AUDIT_RUBRIC.md`, committed alone before any case image existed (eb21e21),
amendment A1 committed alone before any placebo was rebuilt or any case image made (0e6dafe). No frozen rule of
`protocol/CAUGHT_PROTOCOL.md` and no released label was changed; the audit only reads them. Code:
`scripts/verified_audit/`. Tables and images: `results/verified_audit/`.

Every number below has its n, a Wilson 95 % interval where it is a share, the file it comes from, and what it does
not show.

## 1. The placebo set had to be rebuilt, and the rebuild is close but not exact

The S3 placebo rows were never released, so the 191 verified placebos of `results/caught/S3_placebo.csv` could not
be read. They were rebuilt with the frozen code (`placebo.make_placebos`, `run.point_matches`,
`run.polygon_matches`, `scar.find_scar`, `evidence.tier` via `run.label_row`, default parameters). FPA FOD itself
was not reachable from the audit machine (fs.usda.gov answers "The request is blocked" to every page). The record
table was therefore the released S3 label files. Source: `results/verified_audit/rebuild_check.csv`.

| quantity | released | rebuilt |
|---|---|---|
| records searched with imagery | 94,330 | 94,330 |
| matched placebos | 209,000 | 209,024 |
| searched placebos | 91,224 | 91,226 |
| searched placebos, 2020 | 30,992 | 30,994 |
| **verified searched placebos** | **191** | **188** |
| of these 2020 | 51 | 51 |
| of these 2018 + 2019 | 140 | 137 (2018: 100, 2019: 37) |

Input checks: all 18 FIRMS files (2018-2020, US and Puerto Rico) match the sha256 values in
`results/caught/S3_summary.json` byte for byte. Everything else was re-fetched and could differ.

**Failure: 3 of the 191 were not recovered, and the case-by-case overlap cannot be measured.** No released placebo
row exists to compare with, so the audit cannot say which 3 are missing, or whether some of the 188 are not among
the 191. Only the totals by year can be compared (2020 matches exactly). Known causes of difference:

1. FPA FOD records of 2017 and 2021 were missing from the exclusion table, which matters only for windows within
   30 days of a year edge. It explains the +24 matched and +2 searched placebos.
2. HMS fire points were missing for 6 days (2018-05-01, 2018-12-20, 2018-12-30, 2019-02-25, 2019-07-09,
   2019-07-10); the original run lacked only the last 2.
3. Agency perimeters came from the live ArcGIS services, and MTBS from the current composite file (420,881,159
   bytes; the original was 420,877,956).
4. The scar finder ran only on the 1,229 searched placebos with a non-imagery heat or smoke item (rubric section 2,
   A1). This can miss at most 13 verified placebos, the ones that rest only on a Sentinel-2 hot spot and a Sentinel-2
   scar (S3 summary: 13 placebos of any tier carry exactly that witness set).
5. The DNB night look (California 2020 only) was not rebuilt. In S3 it never appears in a two-kind placebo witness
   set.

The audit below classifies the **188 rebuilt** verified placebos (arm P) and **100 sampled verified records** (arm
R).

## 2. How cases were judged

Each case is one composite image (`results/verified_audit/images/case_xxxxxx.jpg`). It holds Sentinel-2 L2A true
colour and SWIR false colour before and after, dNBR, the search disc and label outline, plus the evidence in and near
the window:

* FIRMS detections in the disc, within 5 km, and on other days at the centre.
* HMS points and attributed smoke.
* FPA FOD records within 10 km and ±30 days, excluding the case's own record.
* NIFC, WFIGS, FRAP and FRAP Rx perimeters, MTBS, and FACTS (all hazardous-fuel activities; the per-case query
  succeeded for all 288).

The pre/post scenes are the scar finder's own Sentinel-2 pair where one exists, else the rubric's rule 6.1 pair. No
clear pair was found for 7 cases (P 4, R 3); their images say so.

**Raters.** Two independent raters, each a separate Claude model instance (not a human, not a trained
photo-interpreter). Each read the rubric brief (`scripts/verified_audit/RATER_BRIEF.md`) and the images in 6 batches
of 48, with both arms mixed in each batch by a sha256-derived case id. Raters were blind to the arm and to each
other. Final class = the class both gave; any disagreement in class becomes (c), as pre-registered.

**Record sample.** S3 verified records, stratified by size class with proportional allocation (A 1, B 28, C 40, D 12,
E 9, F 6, G 4). Within each class, records are taken in sha256("verified-audit-v1:" + rid) order. 31 of the 100 have
no standard label.

## 3. Results

### Arm P: 188 rebuilt verified placebos (`results/verified_audit/counts.csv`, `cases.csv`)

| class | final (both raters agree) | rater 1 alone | rater 2 alone |
|---|---|---|---|
| (a) real fire, not in FPA FOD at the place and time | **86 / 188 = 45.7 % (38.8-52.9)** | 91 (48.4 %, 41.4-55.5) | 93 (49.5 %, 42.4-56.6) |
| (b) non-fire land change or non-fire heat | **29 / 188 = 15.4 % (11.0-21.3)** | 31 (16.5 %, 11.9-22.5) | 39 (20.7 %, 15.6-27.1) |
| (c) unclear | **73 / 188 = 38.8 % (32.2-46.0)** | 66 (35.1 %, 28.6-42.2) | 56 (29.8 %, 23.7-36.7) |

Agreement: 165 / 188 = 87.8 %, Cohen's kappa 0.80 (`agreement.csv`). Of the 73 final (c), 23 are rater
disagreements and 50 are cases both raters called unclear (10 of them with both raters giving `no_pair`; 4 P images
had no clear Sentinel-2 pair at all).

* **(a) by subtag:** burn patch 45, agricultural or prescribed burn 18, heat only 23.
* **(b) by subtag:** other change 10 (2.9-9.5 %), harvest 8 (2.2-8.2 %), static heat 6 (1.5-6.8 %), water 5
  (1.1-6.1 %). No case was called clearing or construction.

**By the kinds that made the placebo verified:**

| kinds | (a) | (b) | (c) |
|---|---|---|---|
| heat + scar | 78 | 12 | 48 |
| heat + scar + smoke | 5 | 1 | 3 |
| heat + smoke | 3 | 2 | 8 |
| scar + smoke | **0** | 14 | 14 |

No scar + smoke placebo was judged a fire. 67 of the 86 (a) placebos carry a standard-product detection (MODIS, VIIRS
or MCD64A1) in the window. These are fires a standard satellite product saw that no FPA FOD record places there.

**What it implies for C1 (descriptive, not a re-test).** Treat the 86 (a) placebos as true fires rather than false
labels. The placebo verified rate that cannot be explained by a real fire is then between:

* 29 / 91,226 = 0.032 % (0.022-0.046), counting (b) only; and
* 102 / 91,226 = 0.112 % (0.092-0.136), counting (b) and (c).

The released rate is 191 / 91,224 = 0.21 % (0.18-0.24). C1 passed either way and nothing changes because of this.

### Arm R: 100 sampled verified records

| class | all (n = 100) | no standard label (n = 31) | with standard label (n = 69) |
|---|---|---|---|
| (a) fire | **82 (73.3-88.3)** | 20 (64.5 %, 46.9-78.9) | 62 (89.9 %, 80.5-95.0) |
| (b) non-fire | **2 (0.6-7.0)** | 1 (3.2 %, 0.6-16.2) | 1 (1.4 %, 0.3-7.8) |
| (c) unclear | **16 (10.1-24.4)** | 10 (32.3 %, 18.6-49.9) | 6 (8.7 %, 4.0-17.7) |

Rater 1 alone: a 85, b 3, c 12. Rater 2 alone: a 84, b 4, c 12. Agreement 92 / 100, Cohen's kappa 0.70.

The 2 records rated (b):

* **case_2074bc** (FOD400304594, class G, with MTBS, agency perimeter, MODIS and VIIRS): both raters applied the
  `static_heat` rule literally, because there were 6 other-day FIRMS days within 1 km and monsoon green-up hid the
  scar. This is a recorded large fire. **The (b) call is a rubric failure, not evidence against the label.**
* **case_541b88** (FOD400347449, class C, no standard label, witnesses HMS analyst point + Sentinel-2 scar): both
  raters saw a rectangular bare-soil clearing and one AVHRR point. This is a plausible false verified label.

## 4. What these numbers do not show

* **Not the original 191.** It is 188 rebuilt placebos whose overlap with the 191 cannot be checked case by case
  (section 1).
* **Not expert judgement.** Both raters are instances of one AI model. Their errors may be correlated, so kappa may
  overstate independence. No human remote-sensing analyst checked any case.
* **(a) is not proof of fire, and "not in FPA FOD" is not "unrecorded".**
  - 41 of the 86 (a) placebos have an FPA FOD record within 10 km and ±30 days. A placebo disc can pick up the scar
    of a nearby recorded fire whose FPA FOD point lies 5 km or more away.
  - 3 of the 86 sit inside an MTBS fire that ignited in the 30 days before the window (Pendleton Complex, CA 2018;
    Mallard, TX 2018; a Texas prescribed fire, 2019). The placebo exclusion checks MTBS ignitions only within the
    window ±1 day.
  - Agricultural burns (18 of the 86) are often not in FPA FOD by design.
* **(c) is not "false".** It mixes cases without a clear image, ambiguous changes, and rater disagreements.
* **The rubric left one rule unclear.** It did not say whether GOES scans minutes or hours apart count as separate
  overpasses for `heat_only`. Raters read it differently, and 7 of the 23 P disagreements involve a `heat_only` call.
  Those cases are in (c) by the agreement rule.
* **The static-heat rule misfired at least once.** It fired on a long recorded fire (case_2074bc above).
* **Blinding was imperfect.** The witness set shown on each image includes PERIM for records with an agency
  perimeter, which no placebo can carry. Agency polygons or FACTS activities appear in 35 of 100 record images against
  7 of 188 placebo images.
* **R is 100 records.** Class-level shares for small strata (A n = 1, G n = 4) carry almost no information. The
  no-standard-label subset is 31 records, not a planned stratum.
* **Imagery is limited to 20 m Sentinel-2 at the scenes chosen.** A fire smaller than a few pixels, or hidden by
  green-up between the scenes, can look like no change.

## 5. Files

* `protocol/VERIFIED_AUDIT_RUBRIC.md`: rubric (eb21e21) and amendment A1 (0e6dafe).
* `scripts/verified_audit/`:
  - `s1_sources.py`: sources.
  - `mcd_windows.py`: MCD64A1 per candidate.
  - `s2_placebos.py`: placebo rebuild.
  - `s3_evaluate.py`: points, mcd, scar, labels.
  - `s4_cases.py`: sample, images, evidence.
  - `s6_score.py`: unblinding and counts.
  - `RATER_BRIEF.md`: the raters' brief.
* `results/verified_audit/`:
  - `rebuild_check.csv`.
  - `cases_key.csv`: the unblinding key.
  - `cases_public.jsonl`: the evidence text shown on each image.
  - `ratings_r1.jsonl`, `ratings_r2.jsonl`.
  - `cases.csv`: one row per case, with both ratings, the final class, and the evidence summary.
  - `counts.csv`, `agreement.csv`.
  - `images/`: 288 composites, JPEG quality 72. The PNG originals the raters saw are not kept.

Raw downloads (FIRMS, HMS, MTBS, perimeters, WorldCover, imagery windows) were reduced and deleted for disk space.
Their sha256 values are in the audit's raw INDEX, which is not committed.

**Reproduce.** Set `FIREWITNESS_RAW` to an empty folder, then run from the repository root:

```
s1_sources.py
s2_placebos.py 4
s3_evaluate.py points 3
s3_evaluate.py mcd 3
s3_evaluate.py scar 4
s3_evaluate.py labels
s4_cases.py list
s4_cases.py render 4
```

The ratings are model output and will not be reproduced exactly.

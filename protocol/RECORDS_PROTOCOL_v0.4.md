# Records protocol v0.4

Status: committed alone, before any v0.4 result. Version 0.4 is **time only** (orchestrator message of 2026-11-21): no gazetteer, missing-coordinate or perimeter work. It adds to v0.1 to v0.3; nothing frozen is re-tuned (the v0.2 estimator, its lag window, margins and decision rule; the v0.3 swap test), and v0.1 to v0.3 rules, results and sealed sets are untouched. Results seen when this was written: none for v0.4 (earlier results are known and stand).

## 1. Scope
1. **Pooling.** Pool the years of the same source system x table so that year groups with fewer than 30 fires can be decided. The pooling rule is fixed on dev before the sealed run. Reported per pooled table: the call, n and an interval.
2. **AM/PM hypothesis for the open finding** (OK Forestry 2016, 2020, 2022, called a fixed -12 hour shift in v0.2): does a 12-hour clock with AM/PM lost or flipped explain it. Decided on the open-finding groups as dev, checked once on records never scored, outcome reported whatever it is; if not explained, the open finding stays open.

## 2. Method: pooling (item 1)
The v0.2 estimator (`firewitness/records/timeoffset.py`: shares of fires whose first FIRMS detection falls from 2 hours before to 24 hours after the implied start under H0 recorded = local and H1 recorded = UTC, fixed shifts of -12 to +12 hours, bootstrap by incident with 500 resamples, split halves, violations, margin 0.01) is unchanged and is the only decision rule used.
Pooled table: all fires with a detection, of all years of the split, of one (source system x table); the estimator is run once on the pooled fires. **Homogeneity condition (fixed now, may be changed from dev only):** the years of the table are ordered and split into two halves by alternate years; the pooled call stands only if the gain of the called convention over the alternative is above the v0.2 margin in both halves, otherwise the pooled call is "not clear (years differ)". **Use of the pooled call:** a year group with 30 fires or more keeps its own v0.2 call; a year group with fewer than 30 fires (insufficient) is decided by the pooled call of its table when that call is a UTC or shift offset or "local clock time fits", and stays "insufficient" otherwise. A year group with 30 fires or more whose own gain for the pooled convention is not positive is reported as contradicting the pooled call and is left out of its application. Reported per pooled table: the call, n (fires with detections), the interval of the gain, the years included, the number of year groups it decides, the number it leaves out, and the records moved by an offset.
Tables: raw ICS-209 incident tables (`ics209_info`, `ics209_imsr`, `ics209_2014`) and FPA FOD by `SOURCE_SYSTEM`. The state lists and WFIGS were opened in v0.2 and are not used here.

## 3. Method: AM/PM hypothesis (item 2)
Data: the OK Forestry list (`ok_historical_fire_occurrence`, local date and `FireDiscoveryTime` as hhmm), fires of 300 acres or more with a FIRMS detection. **Dev: the open-finding groups, OK Forestry 2016 (n 36), 2020 (n 32) and 2022 (n 61), pooled and by year.**
Diagnostic (reported, no decision): the distribution of the recorded hour, and the share of recorded hours 13 to 23 (a 12-hour clock without AM/PM mark shows none).
Rules, each table-wide and applied to the recorded clock time, then read as local clock time (the frozen H0 conversion), same calendar date unless the shift crosses midnight:
- **R0** none (recorded = local);
- **R1** fixed -12 hours (the v0.2 call; implied start moved 12 hours earlier);
- **R2** PM lost: records with recorded hour 1 to 11 gain 12 hours; hour 0, 12 and 13 to 23 unchanged;
- **R3** AM/PM flipped: records with recorded hour 0 to 11 gain 12 hours, records with hour 12 to 23 lose 12 hours (same date).
Fit: share of fires whose first detection falls 2 hours before to 24 hours after the implied start (the frozen v0.2 lag window).
**Decision on dev (fixed now):** an AM/PM rule (R2 or R3) is said to explain the finding if, on the three dev groups pooled, its fit share exceeds the better of R0 and R1 with a bootstrap (by incident, 500 resamples) lower bound of the gain above 0.01, and its gain over the better of R0 and R1 is positive in at least two of the three year groups. If both pass, the larger share is taken. If none passes, the finding is "not explained" and no sealed check is run for rule selection (the sealed records are still scored once for R0 to R3 and reported).
**Sealed check (once):** records never scored. The OK Forestry list was opened in full in v0.2, so no 300-acre year of the list remains unopened; the check uses the same list's fires of 100 acres or more and under 300 acres (never scored by any version), all fire years 2001 to 2024, pooled and for the years 2016, 2020 and 2022 separately. The selected rule is "confirmed" if its gain over the better of R0 and R1 has a bootstrap lower bound above 0.01 on the pooled sealed records; otherwise "not confirmed". Limits stated now: fires under 300 acres are seen less reliably by the satellites; the sealed records come from the same table and years as the dev groups.
No patch is written for the OK Forestry list unless a rule is confirmed; if confirmed, a patch per record of the three open-finding groups (`rule` = `time:ampm_<R>`, confidence 0.5) is released as a suggestion, not as a repair.

## 4. Splits and sealed data
Opened sealed sets (v0.1, v0.2, v0.3) are not new. **Pooling sealed years (new): 2006, 2011, 2015, 2020 and 2024**, never in a sealed set of an earlier version. Disclosure written before the run: these years were dev years of v0.2, so the frozen v0.2 margins saw them; the pooling rule and homogeneity condition are fixed on all other years (2001 to 2005, 2007 to 2010, 2012 to 2014, 2016 to 2019, 2021 to 2023, of which the v0.2 and v0.3 sealed years are opened and now count as dev), and the sealed years are opened once by `firewitness/records/sealed_v04.py`, which refuses to run twice and records the frozen-rules commit. The AM/PM sealed records are in section 3.

## 5. Gates
- **P1** pooling: each pooled table has a reported call, n and interval, on dev and on the sealed years; sealed pooled calls are compared with the dev pooled call of the same table and the agreement (same call, or not clear) is reported with a Wilson interval; a sealed pooled call opposite to the dev call is reported as a failure.
- **A1** AM/PM: the diagnostic, the dev decision, and the sealed check are reported in full; the open finding is closed only if a rule is confirmed.
- Independent checker (the v0.1 file): runs on any patch file written.
- Failures and partial gates stay in the report as failures; nothing is re-tuned after the sealed opening.

## Amendment log (v0.4)
| date (UTC) | change | reason | results seen? |
|---|---|---|---|
| (none yet) | | | |

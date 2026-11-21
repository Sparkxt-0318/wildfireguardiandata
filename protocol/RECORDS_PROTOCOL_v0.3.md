# Records protocol v0.3

Status: committed alone, before any v0.3 result. Version 0.3 adds to v0.1 and v0.2; v0.1 and v0.2 rules, results and sealed sets are untouched, and nothing here edits them. Results seen when this was written: none for v0.3 (v0.2 results are known and stand).

## 1. Scope (orchestrator items 1 to 4)
1. **Day-month swap (H2, gate T3).** Per source system x table x year, never per record: does reading recorded dates as day-month instead of month-day make the satellite first detections fit better.
2. **Gazetteer placements.** Uncertainty radius set from dev data by place type so that 90% of known dev locations fall inside; frozen; coverage reported once on new sealed incidents; placements released as "suggested location, unverified" in new fields, never as repairs, until sealed coverage is near 90%.
3. **Perimeters.** Stop extending the samples. Scars that disagree with the recorded size are released as a flag on the record, not as a perimeter. One added check separates the two causes (wrong recorded size versus scar-module limits): scar area against known perimeters (MTBS), by fuel type.
4. **Open finding.** The unexplained -12 hour shift (OK Forestry 2016, 2020, 2022) is recorded as an open finding.

## 2. Method: day-month swap (H2)
Groups: as in v0.2 section 2 for the tables with a date (FPA FOD by `SOURCE_SYSTEM` x fire year; raw ICS-209 incident tables `ics209_info`, `ics209_imsr`, `ics209_2014` by file year). The state lists and WFIGS were opened in v0.2 and are not used. Two levels: year group, and pooled per (source system x table) over the years of the split being run.
Eligible fire: recorded calendar date with day 12 or less and day different from month (both readings are valid dates and differ), recorded area 300 acres or more, a located point and a state, and at least one FIRMS detection (MODIS or VIIRS, within 5 km, from 3 days before the earliest candidate start to 14 days after the latest).
Fit: a fire fits a reading when its first detection (UTC date) falls from 1 day before to 3 days after the implied start date. `share_orig` = share of eligible fires that fit the recorded reading (month-day); `share_swap` = share that fit the swapped reading (day and month exchanged). `gain = share_swap - share_orig`.
Call, per group: **insufficient** if fewer than 30 eligible fires with detections; **swap** if the bootstrap (by incident, 500 resamples, 95%) lower bound of `gain` exceeds M_swap and both split halves (odd and even incidents) have `gain` above M_swap; **no swap** if the upper bound of `gain` is below M_none; otherwise **not clear**. Margins M_swap = 0.10 and M_none = 0.0 are provisional and may be changed only from dev groups (negative controls: tables not swapped, where `gain` is expected well below zero; planted swaps), logged in the amendment log before the sealed opening.
Limit stated now: the test is table-wide; a swap in a minority of records of a group (under half) lowers `gain` but leaves it negative, so it is not detected.
Applying: only for a group called swap, one patch per eligible record on the date field (`rule` = `time:swap_day_month`, evidence the group, n, gain and interval). Otherwise no patch.
Reported per group: call, n, `share_orig`, `share_swap`, `gain`, interval, the number of records it would move.

## 3. Method: gazetteer radii by place type
The v0.2 matcher (place name from the description, GNIS Domestic Names, offset parsing, matched/ambiguous/unmatched) is unchanged. What changes is the radius. Place type of a matched candidate (from the GNIS feature class): county, populated place, named feature (summit, stream, valley, lake, civil and other natural features); and whether a distance offset was applied (yes/no). Radius for each (type x offset) cell = the 90th percentile of the distance from the matched point to the known point over dev matches of that cell, rounded up to 0.5 km; cells with fewer than 30 dev matches share one pooled radius from all dev matches. The radii are written to `results/data/v03_gazetteer_radii.json`, frozen at a commit that is recorded, and not changed after the sealed opening.
Known points: the published hand-geocoded coordinates (`lat_c`, `long_c`) of ICS-209-PLUS incidents, read by the scorer only. Pool: all incidents with a place description and a published point, outside the v0.1 sealed test years. **Dev**: the 459 incidents of v0.2 (their v0.2 dev and sealed shares are both opened and count as dev now) plus pool incidents with `hash(v03|number|year) mod 10` in 3 to 9. **Sealed v0.3**: pool incidents with `hash(v03|number|year) mod 10` in 0, 1 or 2 that are not among the 459 and have raw coordinates present (never scored by the gazetteer before).
Coverage = share of matched sealed incidents whose known point lies inside the frozen radius, with Wilson interval, overall and by cell. Release: matched points are written as new fields `suggested_lat`, `suggested_lon`, `suggested_radius_km`, `location_status` = "suggested location, unverified", never over an existing coordinate and never as a repair. The label stays unless the sealed coverage has a Wilson lower bound of 0.85 or more.

## 4. Method: scar flag and fuel-type check
**Flag.** For every fire in the two pre-registered samples of 2026-11-20/21 (200 fires, seed 1; 100 fires, seed 0; union) whose scar area is below 0.2 times the recorded area, a flag patch on the FPA FOD record: field `flag_scar_size`, new value "scar much smaller than recorded size", with the ratio, the fuel type at the fire and the module verdict for that fuel type (below) as evidence. No perimeter is released for these fires. No further fires are added to these samples.
**Fuel type.** ESA WorldCover 2020 majority class at the fire point: 10 tree (timber), 20 shrub, 30 grass; fires of other classes are not used in the check.
**Known-perimeter check.** A new random sample of MTBS fires of 1,000 acres or more, fire years 2016 to 2023 (Sentinel-2 years), seed 3, excluding the 40 v0.1 validation fires, 30 per fuel type (90 fires; 90 more drawn as spares only for fires that fail before a look), each run through `firewitness.caught.scar.make_perimeter` exactly as the samples above (window 30 days from the recorded start; recorded area = MTBS area). Ratio = scar area / MTBS perimeter area. Outcome classes as P1 of v0.2 plus the ratio. Reported per fuel type: n, scars found, median ratio, quartiles, share of scars with ratio below 0.2 and share from 0.2 to 5, each with a Wilson interval. **Verdict per fuel type**, fixed now: *module under-measures* if the Wilson lower bound of the share with ratio below 0.2 (among scars) is above 0.25; *module adequate* if the upper bound is below 0.25; otherwise *not clear*. Where the module under-measures known perimeters, the disagreement of the no-perimeter samples in that fuel type is attributed to the module and not to the record; where adequate, to the record or the module with the record more likely; not clear stays not clear. The same fuel-type split is reported for the no-perimeter samples (share disagreeing by fuel type).
No tuning of the scar module.

## 5. Open finding
OK Forestry 2016, 2020 and 2022 were called a fixed -12 hour shift by the v0.2 rule on the sealed set. They are recorded in `results/RECORDS_RESULTS.md` as an open finding: not repaired, cause unknown. No hypothesis is tested for it in v0.3.

## 6. Splits and sealed data
v0.1 sealed years (1995, 2001, 2007, 2013, 2019) and v0.2 sealed years (2004, 2010, 2016, 2022) and the state lists and WFIGS are opened and are neither dev nor sealed for H2. **H2 sealed years (new): 2003, 2008, 2014, 2018, 2023**, never opened as a sealed set (they served as dev years for the v0.2 UTC offsets and were never used for H2). H2 dev: all other years 2001 to 2024 not listed above. The H2 rule, margins and planted test are designed and tuned only on dev; the sealed groups are opened once by `firewitness/records/sealed_v03.py`, which refuses to run twice and records the frozen-rules commit. The gazetteer sealed incidents are in section 3. The known-perimeter sample (section 4) is a new pre-registered sample, run once.

## 7. Gates
- **T3 (H2)**: a table-wide swap planted into a copy of a clean dev group (60 trials per size class of 100, 300 and 1,000 eligible fires) is called swap in at least 90% of trials; false swap calls on unplanted dev groups reported; a minority swap (30% of records) planted and reported as not detected. Each sealed group reports its call (swap, no swap, not clear, insufficient), n and interval. T3 is met if the planted rate is at least 90%; any sealed group called swap is reported as a finding to be explained, and no patch is released for it without an independent check against a source that carries the date in an unambiguous form.
- **G2** gazetteer: dev radii per cell with n; sealed coverage once with Wilson interval; label as in section 3.
- **P2** perimeters: flags released; known-perimeter check reported per fuel type with verdicts.
- The v0.1 independent checker runs on the new patches where they exist (flags, swap patches).
- Failures and partial gates stay in the report as failures; nothing is re-tuned after the sealed opening.

## Amendment log (v0.3)
| date (UTC) | change | reason | results seen? |
|---|---|---|---|
| (none yet) | | | |

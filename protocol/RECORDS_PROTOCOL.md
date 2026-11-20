# Records protocol (track 49)

Written and committed before any result. Changes are made only by the amendment log at the bottom: each entry gives the date, what changed, why, and whether any result had been seen when it was made.

## 1. Scope
Region for this run: United States. Every country-specific value (bounding boxes, units, state/county tables, time zones, source list, thresholds that depend on place) lives in `firewitness/records/config/<region>.json`; a Korea run changes only that file.
Tools: (1) values, (2) location and time, (3) duplicates, (4) permanent IDs, (5) coverage and perimeters. Every change is a patch (record id, field, old, new, rule, evidence, confidence). Nothing is smoothed or overwritten; inputs are never modified. No trained model writes a label or a patch; rules, likelihood ratios fitted without labels (EM) and geometry only.

## 2. Data and splits
Sources: FPA FOD (latest edition, with link fields), ICS-209-PLUS (with link fields and the raw incident tables), MTBS, FIRED, the national incident-location feed (NIFC/WFIGS), at least two state lists that still hold duplicates. A source not obtained is reported NOT OBTAINED with the exact reason; nothing downstream pretends otherwise.

Splits are by whole fire year of the (cleaned, else raw) discovery or start date, never by random record, so duplicates and neighbouring fires do not straddle a split:
- **Sealed test years:** 1995, 2001, 2007, 2013, 2019 (every sixth year, spread across the record, so no era is only in test).
- **Held-out year for R5:** the latest complete year in FPA FOD, excluded from dev and from test; it is added only in the R5 check.
- **Dev years:** all others.
A pair or link is assigned to the split of its FPA FOD (or, absent that, earliest) record. The sealed test is opened once, at the end of the improvement loop. Its opening is logged in `results/ROUNDS_records.md` with the commit hash of the frozen rules.
Rules and thresholds are chosen, tuned and fitted on dev only; EM fitting uses dev records only until the single test run.

## 3. Baselines
- **Links (R1):** the best fixed rule = grid search on dev over (distance km, day window, optional name/size agreement) of a single threshold rule, scored by F1 against the published links; the rule is picked on dev, applied unchanged to test. Also reported: the published links themselves (the reference, not a competitor).
- **Duplicates:** (a) exact match on (date, rounded location, size); (b) best fixed distance/time rule as above.
- **Location and time repair:** no repair (leave as is). A repair is applied only if agreement with independent evidence improves (section 5).
- **Perimeters (R6):** the "assumed circle": a circle of the recorded final area centred on the recorded point.
- **IDs:** the source's own ID.
- **Values:** the raw value; unit-slip tests are compared to the recorded neighbours and ratios.

## 4. Gates
- **R1 (links).** Links re-derived with the published links hidden (FPA FOD to MTBS, FPA FOD to ICS-209-PLUS, ICS-209-PLUS to FIRED) beat the best fixed rule on F1; bootstrap resampling whole state-years, 1000 resamples, paired difference interval (95%) excludes zero. Target: precision 0.95 at recall 0.90. Because published links are imperfect, every disagreement class is also scored against independent evidence (burn scar and satellite detections) on a sample, and both numbers are reported.
- **R2 (speed).** Wall time of `firewitness records clean && link && ids` for the whole national run on this machine (4 cores, 15 GB). Target under 30 minutes. Reported with the machine and the data hashes.
- **R3 (do no harm).** All must hold: (a) planted errors recovered (planting recipes in section 6; recovery rate reported per error class with n and interval, target at least 0.8 for classes where independent evidence exists, else "undecided" is allowed and counted); (b) pairs of different fires close in space and time stay separate: the set of distinct-fire pairs within 10 km and 3 days (distinct = different MTBS perimeters, or different FIRED events, or different ICS-209 incident IDs with non-overlapping perimeters) is never linked; (c) at most 1% of records in the reference-clean set (section 6) are altered, and no record is altered without a patch (hash comparison of every field of every record outside the patch list); (d) a second run on the output changes nothing; (e) `revert` restores the input byte for byte (sha256 equal).
- **R4 (no harm to location/time).** No location or time repair lowers agreement with independent evidence: for the repaired set, the mean agreement score after is not below before, and no single repair class (sign flip, swapped axes, degree-minute, datum, time zone, day-month) shows a decrease with its own interval; a class with a decrease is switched off.
- **R5 (ID stability).** IDs identical on a re-run; the IDs of every fire in dev and test are unchanged when the held-out year is added.
- **R6 (perimeters).** Perimeters made from imagery beat the assumed circle on fires with known perimeters (MTBS): intersection-over-union, paired bootstrap by state-year, interval excludes zero; the 'known perimeter' fires used to build tuning are dev only.
- **Independent checker.** A subagent that sees only the patch format and the outputs (not the rules or code) verifies every patch: schema valid, old value equals the input, new value equals the output, rule named, evidence present, confidence in range, no change outside the patch list, reversibility. Disagreements are failures.

## 5. Independent evidence for location and time
For a candidate repair the agreement score is computed from evidence the repair rule did not use: (i) the county or state named in the record (point inside it); (ii) the reporting unit's area (distance to the unit); (iii) satellite detections in the window (distance to the nearest detection within the fire window, and count within a radius); (iv) the burn scar (inside or near the MTBS or imagery-derived scar). Each is a witness (core.evidence) with m, u fitted without labels on dev. A repair is applied only if the posterior that the repaired value is right exceeds the posterior for the original by the decision margin; otherwise the record is left and flagged undecided. A location known only to a survey section (PLSS) gets an uncertainty radius, never invented precision.

**Commit-order proof (tool 2).** Findings on the raw incident tables (the tables ICS-209-PLUS was built from) are committed to `results/` (with the input hashes) before the published cleaning is read. Only then is the published cleaning opened and scored. The git history is the proof; no later edit to that findings file is allowed except by amendment.

## 6. Planting and the reference-clean set
- **Reference-clean set:** records where location, date and size agree with at least two independent sources (for example FPA FOD, ICS-209-PLUS and an MTBS perimeter or FIRED event) within tolerance.
- **Planting (on a copy of dev):** to a random 5% of reference-clean records, each of: sign flip, swapped lat/lon, degree-minute misread, datum shift, time-zone offset, day-month swap, acres to hectares slip, thousands/millions slip, F/C slip, placeholder values (-999, 9999, "N/A", blank), hidden characters, a duplicate with small perturbation, a shrinking-size sequence. The planting seed and plan are written to `results/` before the tools run; the tools do not see the plan.
- Recovery = the patch restores the original value (numeric tolerance stated per class) with the correct rule name.

## 7. Improvement loop
After the first version passes its tests: at most 12 rounds on the dev split. Each round: read the full log of every failure, not only the score; name one cause; change the rules for that cause only; rerun. Keep the change only if the dev score rises and the do-no-harm rates (R3) do not worsen. Each round is logged in `results/ROUNDS_records.md` (cause, change, dev score before and after, do-no-harm before and after, kept or reverted). The sealed test is opened once, at the end.

## 8. Reporting
Headline numbers: duplicates removed, IDs split and merged, locations repaired, times repaired, values repaired, perimeters created, published hand cleaning reproduced (precision, recall, run time). Each with n, interval, source file and what it does not show. Source and input hashes recorded.

## Amendment log
| date (UTC) | change | reason | results seen? |
|---|---|---|---|
| (none yet) | | | |

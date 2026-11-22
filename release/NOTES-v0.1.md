# firewitness v0.1

One zip per track (records, caught, live, smoke, fuel, score), each the track's own v0.1 release folder. Later
versions (records v0.2 to v0.4, live v0.2, caught v0.2) are separate releases. Every number below is copied from
`results/*_RESULTS.md` on main; the files hold the intervals, methods and limits.

## Labelling: sealed recall (caught v0.1, small fires under 300 acres, opened once)

A fire counts as caught when a label meets its mapped polygon (+30 m). Standard label = MODIS C6.1 / VIIRS footprints.
Paired cluster bootstrap, 95 % intervals. Source: results/CAUGHT_RESULTS.md, "C2: recall on the sealed small fires".

| class | n | labelled (verified or probable) | standard | labelled minus standard | verified only | verified minus standard |
|---|---|---|---|---|---|---|
| all | 3,711 | 0.639 | 0.306 | +0.333 (+0.308 to +0.358) | 0.299 | -0.008 (-0.020 to +0.004) |
| A (under 0.26 acre) | 206 | 0.044 | 0.034 | +0.010 (+0.000 to +0.025) **FAIL** | 0.010 | -0.024 (-0.047 to -0.005) |
| B | 1,029 | 0.490 | 0.114 | +0.376 (+0.335 to +0.419) pass | 0.096 | -0.017 (-0.033 to -0.003) |
| C | 1,857 | 0.733 | 0.357 | +0.376 (+0.345 to +0.408) pass | 0.349 | -0.008 (-0.027 to +0.011) |
| D | 618 | 0.801 | 0.566 | +0.235 (+0.198 to +0.273) pass | 0.579 | +0.013 (-0.017 to +0.042) |

The labelled tier beats the standard label in classes B, C and D. Verified-only recall is not above the standard
label in any class. Labelled recall by fuel: grass 0.762, shrub 0.785, timber 0.503 (scars under-measure timber).

## Labelling: counts by slice (records with no standard label; tiers in separate columns, never summed)

| slice | records | standard label | no standard label | verified | probable | record-only |
|---|---|---|---|---|---|---|
| S1 California 2020 | 10,360 | 397 | 9,963 | 92 | 522 | 9,349 |
| S2 US 2020 | 74,530 | 4,363 | 70,167 | 1,648 | 7,128 | 61,391 |
| S3 US 2018-2020 | 220,975 | 13,467 | 207,508 | 4,343 | 20,913 | 182,252 |

S3 verified by class: A 16, B 1,522, C 2,104, D 449, E 232, F 19, G 1. Placebo false rate, verified tier: S1 0.26 %,
S2 0.16 %, S3 0.21 % of searched placebo windows (limit 1 %). Probable tier: S3 5.30 % (about one false label in 19
searched windows). Label geometry marks where a fire was found, not its burned area.

## Scar floor

A scar smaller than the floor cannot be found: Sentinel-2 2,345 m2 (0.58 acre), Landsat 5,277 m2 (1.30 acres), at
T = 0.10. By fuel: 0.58-0.73 acre with Sentinel-2, 1.30-1.65 acres with Landsat (grass lowest, timber highest).
Class A fires (under 0.25 acre) lie below both floors.

## Every failed gate

Records
- R1, ICS-209-PLUS to FIRED link: did not beat the best fixed rule (sealed F1 0.328 vs 0.320, difference 0.008,
  interval -0.012 to 0.022). FIRED was not downloadable.
- R1 target (precision 0.95 at recall 0.90): not reached on any link (FPA FOD to MTBS sealed recall 0.861; to
  ICS-209-PLUS 0.811). Both links beat the fixed rule.
- R3(a) planted errors: day-month swaps 26 of 300 recovered, time-zone offsets 0 of 52. Unit slips below the 0.8 target
  as written: acres/hectare 204 of 300, 1000x 206 of 300.
- R3(c) do no harm: value patches touch 2.44 % of FPA FOD records, over the 1 % limit (0.05 % without name
  placeholders; that split was decided after counts were seen).
- v0.2 T3 for the day-month swap: not built in v0.2 (met later in v0.3).
- v0.3 G2 gazetteer: sealed coverage 35 of 40, Wilson lower bound 73.9 % below 85 %; placements stay "suggested
  location, unverified".
- v0.4 A1 AM/PM hypothesis: not confirmed; the OK Forestry -12 h shift stays an open, unexplained finding.
- Partial: v0.2 sealed time check called UTC for 3 of 7 known-UTC groups; v0.4 pooling decided 3 of 12 sealed tables.

Caught
- C1 probable guard (5 %): S1 5.05 % (4.35-5.82), S3 5.30 % (5.16-5.45). Verified tier not affected.
- C2 sealed small-fire recall: fails as pre-registered in class A (table above).
- v0.2 C1 (placebo verified at most 1 %): fails in every slice, S1 2.47 %, S2 1.72 %, S3 1.80 % (persistence
  confirms 34 % of placebo scars). The v0.2 tier is not released as verified (DECISIONS D-021).
- v0.2 C2 (sealed WFIGS 2021, 795 fires): fails in class A (+0.005, 0.000 to 0.016). Sealed set reduced by an id
  de-duplication bug (D-518).
- Downstream forecast check not run (no overlap); fixed-margin check inconclusive.

Live
- D1: the live detector alerted before the operational GOES product on 7 of 97 sealed fires (7.2 %, 3.5-14.2 %).
  Closed as a negative result. (D2, 24 h unattended signed run, passed: 288 of 288.)
- v0.2 E2: two-satellite onset agreement, median difference 102.5 min over 30 min (n = 2).
- v0.2 V2: smoke plume supported 1 of 10 daytime onsets (10 %, 1.8-40.4 %).

Smoke
- S2 placebo, dev: 7.1 % of pre-ignition frames (limit 1 %). Sealed 0.8 %, upper limit 2.4 % (14 sequences).
- S1 targets not met: opacity MAE 0.143 (0.10), edge error 10.01 / 7.90 px (4 px), detection 79.3 % (90 %), sealed.
  The loop keep rule and edge-error definition were changed after results (D-012).
- S5 window sensitivity: first-smoke shift 240 to 900 s on sealed (target 1 frame).

Score
- N5 matched negatives: over-prediction 10.682x at the validation threshold (limit 2.0); with proximity features
  1.305x matched vs 1.576x random, also failed. The limit was not moved.
- N3 passes only on the cheats its limit was tuned on (D-013); a pre-registered unseen cheat (L2) was missed.

Fuel: no gate failed (F1 7.91 [6.36, 10.03]; F2 0.92 %; F3 pass). The 29-fire spread stretch showed no improvement
(-0.42 h, interval -1.49 to +0.47).

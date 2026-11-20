# ROUNDS: caught (track 50)

Dev data only: S1 (California 2020) dev records (sha256(FOD_ID) mod 10 in 0-2), their matched placebos, and the
dev truth fires (sha256(source id) mod 10 in 0-2, US 2018-2020). The sealed truth split is not read until the rules
are frozen.

## Metrics and keep rule (written before the v1 truth numbers were seen)

* **Catches**: (a) dev truth fires of the primary small stratum labelled verified or probable where the label meets
  the polygon; (b) the verified ones among (a); (c) dev records with no standard label that reach verified (the
  headline on dev).
* **Placebo rates**: share of searched dev placebos reaching verified, and reaching probable.
* **Before the loop** ("after the first version passes"): version 1 must pass on dev: verified placebo rate <= 1 %
  (C1), probable placebo rate <= 5 % (this track's guard), labelled-recall above the standard label's on dev truth.
  Fixes made to get there are listed below as development fixes, each with its cause, whatever they do to catches.
* **Loop rounds** (at most 12): one named cause per round, from reading every miss and every placebo hit. A change
  is kept only if catches (a) or (c) rise and neither placebo rate rises; otherwise it is reverted.

## Version 1 on dev

Dev records 3,059 (1,346 searched), matched placebos 2,749 of 3,059 (1,194 searched), dev truth primary small 1,540.

| measure | v1 |
|---|---|
| dev headline (no standard label -> verified) | 54 |
| dev no standard label -> probable | 609 |
| placebo verified, searched (gate <= 1 %) | 15 / 1,194 = 1.26 % (0.70-2.06) **fail** |
| placebo probable, searched (guard <= 5 %) | 225 / 1,194 = 18.8 % (16.7-21.2) **fail** |
| dev truth labelled recall vs standard | 0.670 vs 0.318, diff 0.353 (0.325-0.383) |
| dev truth verified recall | 0.309 |
| by class (labelled - standard) | A 0.000; B 0.417 (0.357-0.466); C 0.374 (0.332-0.409); D 0.305 (0.246-0.365) |

What the placebo hits are (all 15 verified and a sample of 12 of the probable ones read as image chips, every
component's numbers read): 10 of the 15 verified placebos pair a DNB night "hit" with a Sentinel-2 scar. The DNB
test fires in 23 % of placebo windows against 36 % of record windows: the 5-sigma / 3 nW rule is noise at the 500 m
scale of a small fire. Scar false positives: field-shaped changes on cropland (harvest that darkens), terrain
shading that changes with the sun between autumn scenes, cloud shadow the scene classification missed, isolated
4-8 pixel groups at urban edges. Placebo scar components have lower dNBR (median 0.19 vs 0.31 for records), higher
pre-fire NIR, and a SWIR1 that rises rather than falls.

Bugs found and fixed (no rule change): decimated reads of very large windows were warped and striped (now read
from overviews on the native grid); invalid polygons broke the label union (made valid); duplicate FACTS ids
inflated the secondary stratum (deduplicated); worker memory capped after an out-of-memory kill.

## Development fixes (before the loop; dev only)

**D1 — DNB night look was noise.** Cause: a 5-sigma / 3 nW excess over a 30-night baseline fires on ordinary
night-to-night variation of 500 m pixels (23 % of placebo windows). Change: excess >= max(15 robust sd, 100 nW cm-2
sr-1), the brightness of open flame filling part of a pixel. Threshold scan on S1 windows: (5, 10) 25.7 % records vs
15.7 % placebos; (8, 30) 5.0 vs 3.1; (10, 50) 2.1 vs 1.2; (15, 100) 0.69 vs 0.29.

| | v1 | D1 |
|---|---|---|
| placebo verified | 1.26 % | 0.25 % (3 / 1,194) |
| placebo probable | 18.8 % | 11.0 % |
| dev truth labelled / verified catches | 1,032 / 476 | 1,030 / 468 |
| dev headline | 54 | 34 |

**D2 — Sentinel-2 scar false positives (probable placebo 11.0 % after D1).** Cause (from the chips and the component
numbers): small groups of 4-7 pixels at urban edges, in shrub and forest texture, and field-edge changes, plus
changes where SWIR1 rises (bare soil after harvest, haze), which a burn does not do. Eight variants measured on the
same cached windows (DNB at D1 in all):

| variant | placebo verified | placebo probable | dev truth labelled | verified | B recall | C recall |
|---|---|---|---|---|---|---|
| D1 (N_min 4, T 0.10, 3 sd) | 0.25 % | 10.97 % | 1,030 | 468 | 0.528 | 0.767 |
| A: component median dNBR >= 0.20 | 0.08 % | 5.19 % | 883 | 390 | 0.383 | 0.673 |
| B: N_min 8 | 0.17 % | 6.62 % | 998 | 452 | 0.472 | 0.759 |
| C: T >= 0.15 | 0.17 % | 7.37 % | 1,002 | 461 | 0.490 | 0.753 |
| D: 4 sd | 0.17 % | 7.54 % | 1,004 | 454 | 0.485 | 0.759 |
| E: N_min 12 | 0.17 % | 5.28 % | 971 | 448 | 0.440 | 0.744 |
| **F: N_min 8 and SWIR1 rise < 0.02** | **0.17 %** | **4.44 %** | **985** | **448** | **0.460** | **0.749** |
| G: N_min 8 and component dNBR >= 0.15 | 0.17 % | 5.61 % | 964 | 441 | 0.446 | 0.731 |
| H: N_min 8 and T >= 0.15 | 0.17 % | 4.86 % | 964 | 448 | 0.433 | 0.740 |

Chosen: F, the only variant under the 5 % guard that keeps the most catches. With N_min 8 the best scar floor rises
from 1,440 m2 to 2,345 m2 (0.58 acre); records below it are `below_floor`.

**Version 2 = v1 + D1 + D2 passes on dev**: placebo verified 2 / 1,194 = 0.17 %, probable 53 / 1,194 = 4.44 %, dev
truth labelled recall 985 / 1,540 = 0.640 against the standard label's 489 / 1,540 = 0.318. The loop starts from v2.

## Loop rounds

Comparisons below use the same placebo set in every round (the 1,194 placebos searched in v1), so counts stay
comparable when the floor moves.

**Round 1 — the look search stopped too early. KEPT.** Read: 555 dev truth misses (reason, every look tried, clear
fractions, rejected components). 126 had no clear look; 76 of them failed for want of a clear pre image after only
the 4 latest scenes were tried. Change: try up to 10 scenes before and after. Catches (a) 985 -> 994, verified 448 ->
461, headline 30 -> 31; placebos verified 2 -> 2, probable 53 -> 53.

**Round 2 — fires detected by heat had no second kind: Landsat was tried only when Sentinel-2 had no clear look.
REVERTED.** Read: of the dev truth fires labelled only probable, most carry standard heat detections and a clear,
empty Sentinel-2 look. Change: also look in Landsat whenever Sentinel-2 is clear but finds no scar. Catches (a) 994
-> 1,024, verified 461 -> 485, headline 31 -> 32; placebo probable 53 -> 61 (verified 2 -> 2). The placebo rate rose,
so the change is reverted.

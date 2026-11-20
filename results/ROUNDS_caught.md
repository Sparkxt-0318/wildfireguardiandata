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

# caught v0.2 flags: data card

Built 2026-11-22 from the v0.2 run (protocol/CAUGHT_PROTOCOL_v0.2.md with amendment A1; results in
results/CAUGHT_RESULTS.md, addition 2026-11-22T01:25Z; DECISIONS D-021). Code: `firewitness/caught/v02.py`.

## What it is
`caught_v02_flags.parquet`: one row per caught-v0.1 label (220,975 FPA FOD records, all US 2018-2020), keyed by
`rid` to the caught-v0.1 label files. No geometry: the label geometry, time interval and evidence stay those of
caught-v0.1.

| field | meaning |
|---|---|
| `rid` | caught-v0.1 record id (`FOD<FOD_ID>`) |
| `second_sensor_confirmed` | the other scar sensor (Landsat 30 m beside Sentinel-2 20 m, or the reverse) found a scar that meets the first and overlaps it in time: true / false; null = not checked or no clear look for this route |
| `persistence_confirmed` | the same sensor's next clear scene 10-60 days later still shows at least half of the scar's pixels: true / false; null = not checked or no clear look |
| `v02_tier` | the v0.2 tier as the protocol defines it: a v0.1 probable label with a scar is lifted to verified if either flag is true; otherwise the v0.1 tier |

Only v0.1 probable labels whose evidence holds a scar were checked (15,584). Verified and record-only labels keep their
v0.1 tier and have null flags.

## The verified tier is still the v0.1 tier
**The v0.2 tier FAILED its placebo gate (C1, at most 1 %):** on searched placebo windows it reaches verified on
1.80 % (1.71-1.88) in S3, all US 2018-2020; 2.47 % (1.98-3.03) in S1, California 2020; 1.72 % (1.58-1.87) in S2,
US 2020. Persistence is the cause: it confirms 47 % of record scars but also 34 % of placebo scars, because any
lasting change of the land persists as well as a burn does. So `v02_tier = verified` is not a verified label; use
the caught-v0.1 `tier` for that.

The second-sensor route alone reached 0.62 % (0.57-0.68) on S3 placebos and 0.96 % on S1 (interval to 1.34 %),
0.53 % on S2. It is reported per route, as the protocol asks, **not as a rule**: a label with
`second_sensor_confirmed = true` has stronger support than one without, but it is not a released verified tier.

## Sealed set (C2 v0.2) and its deviation
Opened once on 2026-11-21T22:23Z: WFIGS 2021 perimeters under 300 acres (amendment A1). Labelled recall beats the
standard satellite label in classes B, C and D, not in A. **Deviation D-518:** the builder dropped the 3,061
qualifying perimeters without an IRWIN id, so the set that ran is 795 (the 794 with an id plus one), not up to 1,500
of 3,855 as A1 meant. Selection depended only on whether an id exists; reported as is, not re-run. The 3,061 are
unopened.

## Scar floor
A scar smaller than the floor cannot be found by either route: Sentinel-2 2,345 m2 (0.58 acre) and Landsat 5,277 m2
(1.30 acres) at threshold T = 0.10; by fuel 0.58-0.73 acre with Sentinel-2 and 1.30-1.65 acres with Landsat
(optimistic for timber). The second-sensor route can only confirm a scar above the Landsat floor. Class A fires
(under 0.25 acre) are below both.

## What it does not show
A second sensor agreeing is a second look at the same kind of evidence (reflectance change), independent in satellite
and scene, not in kind. The flags say nothing about records that were not probable-with-scar in v0.1. All caveats of
the caught-v0.1 data card still apply.

## Licence and sources
As caught-v0.1 (Sentinel-2: Copernicus, free and open; Landsat: USGS, public domain; WFIGS: NIFC, public). Flags: MIT,
like the code.

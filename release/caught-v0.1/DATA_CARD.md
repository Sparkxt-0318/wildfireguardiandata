# caught v0.1 label set: data card

Built 2026-11-21 from run tag `final`, slices S3. Code: `firewitness caught`.

## What it is
One row per wildfire record in FPA FOD 7th edition (RDS-2013-0009.7) for the slices above: 220,975 records.
Every record is kept. Tier: verified 13,793; probable 24,930;
record-only 182,252. Records with no standard satellite label: 207,508, of which
verified 4,343 and probable 20,913.

## Fields
`geometry`: the pixel label (scar components and agreeing heat-pixel footprints, clipped to the search disc) for
verified and probable fires with a pixel label; otherwise the search disc (honest radius `r_m` = location
uncertainty `r_loc_m` + radius of the recorded area). `t0`, `t1`: the record's window; `label_t0`, `label_t1`: the
interval the agreeing evidence allows. `tier`, `reason` (record-only: below_floor, no_clear_look,
location_too_uncertain, clear_look_nothing_found). `evidence`: JSON list of every agreeing item (witness, kind,
dates, details). `pairs`: agreeing independent kinds. `std_label`, `std_witnesses`: standard products (MODIS,
VIIRS S-NPP, VIIRS NOAA-20 active fire; MCD64A1; MTBS) in the window. Three states in the searched disc:
`fire_m2_disc`, `no_fire_m2_disc` (verified no fire above `scar_floor_m2` between `scar_pre` and `scar_post`),
`unknown_m2_disc`. `caught_states_v0.1_<year>[_partKofN].parquet`: the three states as shapes, one row per state and record, with its interval (`t0`, `t1`) and, for no fire, its floor (`floor_m2`); shapes simplified to about 3 m (0.00003 degree, topology kept) and repaired where cutting the disc left slivers, so their areas can differ slightly from the `*_m2_disc` fields, which are exact. `heat_floors_m2.json`: edge-of-scan flaming-area floors per heat sensor, day and night (the same for every record).

## How it was made
protocol/CAUGHT_PROTOCOL.md (fixed before results). No trained model writes a label. No smoothing, dilation,
filling or interpolation. Inputs: see results/CAUGHT_RESULTS.md (hashes) and the raw index.

## What it does not show
- Probable tier: the placebo false rate was 5.30 % (5.16-5.45) of searched windows in S3, above this track's
  5 % guard (FAILED; nothing re-tuned). About 1 in 19 probable labels in searched windows may be false. The
  verified placebo rate was 0.21 % (0.18-0.24).
- Scar floor by fuel and sensor: 0.58-0.73 acre with Sentinel-2 and 1.30-1.65 acres with Landsat (grass lowest,
  timber highest; optimistic for timber, since the floors use the brighter scars that were found). See
  results/CAUGHT_RESULTS.md, addition 2026-11-21T05:00Z, (b).
- Sealed recall by fuel (labelled, primary small fires): grass 0.76, shrub 0.79, timber 0.50. Class A is about
  0.04-0.05 in grass (n = 73) and timber (n = 88); shrub has only 3 class-A fires (0 caught). See the same
  addition, (c).
- The label geometry marks where a fire was found, not its burned area. Scars under-measure timber fires
  (median scar/mapped area 0.46 on dev, 0.82 in grass; results/CAUGHT_RESULTS.md, addition 2026-11-21T05:00Z).
- Search discs without a pixel label (record-only, and the few probable labels with smoke only) are drawn as
  16-vertex polygons, about 2.6 % smaller in area than the circle of radius `r_m`; use `r_m` for the disc. In this
  release (built from the S3 run, all of 2018-2020) every such disc has 16 vertices. The S1 and S2 runs, which are
  not part of this release, drew them with 256 vertices (0.01 % smaller); export simplification to 2 % of the
  radius would bring those to 16 vertices as well. No tier, count, recall or three-state area depends on these
  polygons: matching and the three states use their own 256-vertex discs, and recall uses pixel labels only
  (DECISIONS D-514).
- FireCCI51 was not checked (host unreachable from the build network); a fire labelled only by FireCCI51 counts
  here as "no standard label".
- "Verified no fire" holds only above the stated floor and only for the scar look's interval.
- A verified label says two independent kinds of evidence agree with the record in place and time; it does not
  prove the record's area, cause or exact start.
- Location uncertainty is inferred from coordinate precision; FPA FOD records placed at a survey-section centroid
  with many decimals get a radius that is too small.

## Licence and sources
FPA FOD (USDA Forest Service, public domain); FIRMS (NASA, open); MCD64A1 (NASA LP DAAC); MTBS (USGS/USFS); HMS
(NOAA); Sentinel-2 (Copernicus, free and open); Landsat (USGS, public domain); ESA WorldCover (CC BY 4.0); agency
perimeters (NIFC, CAL FIRE, public). Labels: MIT, like the code.

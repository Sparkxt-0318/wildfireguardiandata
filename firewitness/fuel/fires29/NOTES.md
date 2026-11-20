# fires29: rebuilt "29 US fires" fuel-checking set

Rebuilt from public sources because the original LANDFIRE fuel rasters and fire arrival-time rasters are not available.
Everything is code: `select.py` (choice) -> `catalog.json` -> `build.py` (per fire). Raw data live outside the repo in
`/home/user/wildfire 3 (1)/firewitness_raw/fires29/<fire_id>/` (indexed in `firewitness_raw/INDEX.md`). Only `catalog.json` is meant for git.

## Sources
- Perimeters: NIFC ArcGIS `https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/`
  `Historic_Geomac_Perimeters_2017`, `Historic_Geomac_Perimeters_2018`, `Historic_GeoMAC_Perimeters_2019` (FeatureServer/0),
  queried with `outSR=4326`, `f=geojson`, paged by `resultOffset`. Fields used: `uniquefireidentifier`, `incidentname`,
  `perimeterdatetime` (UTC epoch ms), `gisacres`, `state`, `incomplex`, `irwinid`.
  The layers have NO fire-type (wildfire / prescribed) field. WFIGS (`WFIGS_Interagency_Perimeters`) has `IncidentTypeCategory`
  but holds none of the 2017-2019 incidents tried (e.g. Bacon Rind 2018 is absent), so it could not be used. Prescribed fires are therefore
  screened only by name (regex `rx|prescribed|pile(s)|broadcast|understory burn`) plus the size/duration rules (a >=20 km2 incident with >=8
  daily perimeters over >=4 days is a wildfire in practice). Not verified one by one against IRWIN; treat as "wildfire by rule".
- LANDFIRE: USGS LFPS ImageServer via `firewitness.fuel.fetch.lfps` (native 30 m, nearest neighbour). FBFM40, CC, CH from the
  `Landfire_LF2016/LF2016_*_CONUS` services (the 2016 release is the pre-fire map for 2017-2019). SlpD (slope, degrees) and Asp from
  `Landfire_Topo/LF2020_*_CONUS` (that is what lfps.py serves; topography is static so this is harmless). The ImageServer
  metadata gives no version string; do not read more into "LF2016" than the service name.
- Weather: Open-Meteo archive API `https://archive-api.open-meteo.com/v1/archive` (keyless, ERA5-based; worked for all 29, no fallback needed).
  Hourly wind_speed_10m (m/s), wind_direction_10m, wind_gusts_10m, temperature_2m, relative_humidity_2m, UTC, at the final-perimeter
  centroid, from first-perimeter date - 1 day to last-perimeter date + 1 day. The API answered HTTP 429 under 4 parallel workers; the code
  backs off and retries (every fire ended up with a full file, no NaN).

## Selection rules (select.py)
Stage 1 (attributes, no geometry), records grouped by `uniquefireidentifier`:
1. fireyear 2017-2019 (LF2016 is pre-fire), state in the 48 contiguous states (AK, HI excluded);
2. not prescribed by name (see above);
3. >= 8 distinct perimeter datetimes, first-to-last span >= 4 days, no gap > 5 days between consecutive datetimes;
4. final area 20-600 km2 (loose 16-750 km2 window on the attribute `gisacres`, exact test in stage 2).
   -> 153 incidents.
Stage 2 (geometry): download all perimeters, dissolve per datetime, final area = area of the union of all perimeters in EPSG:5070; re-test
rules 3-4 exactly; download LF2016 FBFM40 on the final AOI; compute the fuel class. 14 incidents fell out on the exact area/duration test.
5. **Added rule (not in the brief):** first perimeter must cover <= 50% of the final area. Without it, many fires (e.g. the two Oklahoma OKS
   fires) are essentially fully inside the first perimeter, so `arrival_hours` is 0 almost everywhere. 22 incidents fell out here.
6. Burnable cells (FBFM40 101-204) must be >= 50% of the final perimeter (dropped none in practice).
   -> 117 candidates (CA 27, MT 18, AZ 16, ID 8, NM 8, CO 7, OR 7, UT 6, WA 6, NV 5, FL 4, TX 3, WY 2).
Dominant fuel group = class of the FBFM40 **mode group** over the final perimeter (burnable cells): GR -> grass; SH -> shrub;
TU, TL, SB -> timber; GS (grass-shrub) -> "mixed". (A 50%-share rule for "mixed" was tried and rejected: it labelled 64 of 135 fires mixed
and left shrub with one fire.)
Stage 3 (deterministic greedy, no randomness): <= 4 per state; each step takes the candidate maximising
(state not yet used, fewest chosen fires in its fuel class, fewest chosen fires in its state); ties by incident name (case-insensitive), then id.
Result: 29 fires, 13 states (the candidate pool contains only 13 states after rules 1-6), all four fuel classes
(grass 7, shrub 6, timber 8, mixed 8), max 4 per state (CA).
`excluded.json` ({id: reason}) is read by select.py so a fire that fails to build can be dropped and replaced reproducibly. It does not exist: no fire was dropped.

## Arrival time (arrival.py, test in tests/fuel/test_arrival.py)
Perimeters per datetime -> running union (nested) -> rasterised on the 30 m grid (cell centres). First perimeter = 0 h. Ring between
M_k and M_{k+1}: `t = t_k + (t_{k+1}-t_k) * d_k/(d_k+d_{k+1})`, with d_k = EDT distance to M_k and d_{k+1} = EDT distance to the nearest cell
outside M_{k+1}, each reduced by half a cell (EDT measures to a cell centre; without this the synthetic-disk error was ~0.7 h, with it < 0.35 h at the 95th
percentile). Never-burned cells = -9999. Times are hours since the first perimeter datetime. If the first perimeter rasterises to nothing, the first non-empty
perimeter's cells get its time. Unit tests: expanding disk with constant front speed, running-union nesting, empty first mask.
Perimeter datetimes are the GeoMAC `perimeterdatetime`; several features with the same datetime are dissolved. Note GeoMAC times are often the
mapping/flight time, so arrival times are an interpolation between maps, not observed ignition times.

## Differences from the original 29 and caveats
- Different fires (the original list is unknown), different perimeter source (GeoMAC daily perimeters, not VIIRS/MTBS progression).
- Only 13 states; Oklahoma, Florida-style short grass fires and Great Plains fires are rare under the multi-perimeter rule. FL fires (Buzzard,
  Curlew, Flamingo) are Everglades/Big Cypress fires labelled grass by the FBFM40 mode.
- 2017_MT_caribou crosses the Canadian border: about 11% of its burned cells have no LANDFIRE value (FBFM40/CC/CH nodata). Kept, flagged here.
- 16 of the 153 stage-1 incidents are flagged `incomplex = Y` in GeoMAC (complex perimeters); none was excluded for this.
- The `state` is the GeoMAC `state` attribute (point of origin state), not recomputed from geometry.
- The raw INDEX.md rows for FBFM40 candidates point at `_candidates/<fire_id>/...`; the files were later renamed to `_candidates/<uniquefireidentifier>/`
  (name collisions, e.g. two "Whittier" fires). `fires29/<id>/fbfm40.tif` is a copy and has its own row.
- `_candidates/` (139 candidate FBFM40 windows) and `_unselected/` (7 fires built before the first-perimeter rule was added) in the raw folder are not part of the set.
- Verification (build.py `verify`): all rasters on the meta grid (read_tif asserts bounds/shape), no all-nodata raster, arrival percentiles and burned share printed per fire.
  Correlation of arrival with distance from the first perimeter is high for single-origin fires and near 0 for multi-origin or spotty ones (e.g. UT Bald Mountain, TX Bear Mtn, MT July) - expected, not an error.

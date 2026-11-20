# FUEL_PROTOCOL — fuel-map checking agent (track 53)

Status: frozen at the commit that adds this file. No result of any kind existed when it was written: no verdict, no plot comparison, no gate number. The only data looked at were counts of field-plot locations (to choose areas) and the existence and format of public layers. Any later change is an amendment appended at the end, dated, with its reason, and never edits a section above it.

## 1. Question and scope

Fuel maps feed nearly every spread and risk model and nobody checks them. This agent checks a fuel map cell by cell without fieldwork, using only independent public layers and fixed rules. **No trained model and no language model takes part in any verdict.** Numbers in rules are fixed constants in `firewitness/fuel/config/us.json`; they are never fitted to the data being checked. (They may be changed only through the improvement loop in section 9, on development areas, and each change is logged.)

Region of this run: contiguous United States. Fuel map under test: **LANDFIRE FBFM40** (Scott & Burgan 40 fuel models), 30 m, EPSG:5070. Every country-specific value (class lists, layer sources, thresholds, map date) lives in a region config file; the Korea file is a stub (section 12).

Two map versions are run, both pre-registered:

* **M22** (primary): LF2022 FBFM40. Map date = 2022-01-01 (the conservative reading: events dated 2022 are ambiguous and ignored; events dated 2023-01-01 or later count as "since the map").
* **M16** (secondary, staleness stress test): LF2016 FBFM40. Map date = 2016-01-01; events 2017-01-01 onward count as "since the map".

All gates are decided on **M22**. M16 is reported as a labelled secondary analysis and cannot rescue a failed gate.

## 2. Inputs the agent may use (never field plots)

All are public, free, read-only. Everything is resampled to one grid: EPSG:5070, 30 m, cell edges at multiples of 30 m plus 15 m (the LANDFIRE/NLCD native grid, so those two are not resampled).

| Layer | Used for | Source |
|---|---|---|
| FBFM40 (M22 or M16) | the map being checked | USGS LFPS ImageServer |
| NLCD 2021 land cover | lifeform, water, developed, barren | MRLC WCS |
| NLCD/USFS tree canopy cover 2021 (v2021-4), 0-100 % | canopy cover | MRLC WCS |
| Meta/WRI 1 m canopy height (Tolan et al. 2024), reduced to 30 m: max height and share of sub-cells >= 3 m | canopy height | s3://dataforgood-fb-data/forests/v1/alsgedi_global_v6_float |
| ESA WorldCover 2021 v200, 10 m, reduced to 30 m class shares | land cover | s3://esa-worldcover |
| Hansen Global Forest Change 2024 v1.12: tree cover 2000, loss year | tree loss since the map | Google storage |
| NIFC/WFIGS fire perimeters (with discovery date, fire type) | fire since the map; fire history | NIFC ArcGIS services |
| LANDFIRE annual disturbance layers (Dist, years after the map year; for family 3, years up to the map year) | fire / harvest / clearing and severity | USGS LFPS |
| Fire arrival-time rasters, where they exist (section 11) | observed spread | built from public perimeter progression |
| Wind (Open-Meteo / ERA5 hourly), slope and aspect (LANDFIRE topo) | spread bound | public |

Independence caveat, stated up front: NLCD, TCC, WorldCover and the Meta canopy height are not LANDFIRE products and share no training labels with FBFM40, but all are remote-sensing products that share some input imagery (Landsat/Sentinel/Planet) with the LANDFIRE inputs. "Independent" means separate products and methods, not independent physics.

## 3. Rule families

Each rule has an id. A cell's output lists every rule that fired. The fuel class groups are: **NB** 91 92 93 98 99; **GR** 101-109; **GS** 121-124; **SH** 141-149; **TU** 161-165; **TL** 181-189; **SB** 201-204 ("timber" = TU, TL, SB; "burnable" = everything not NB). Any other value or no-data is `unknown` by rule U0.

Tree-evidence indicators (each +1 tree / -1 no tree / 0 intermediate / missing):

* NLCD: +1 if class 41, 42, 43 or 90; else -1.
* TCC: +1 if >= 20; -1 if <= 5; else 0.
* Meta canopy height: +1 if share of sub-cells >= 3 m is >= 0.2 and max >= 5 m; -1 if max < 3 m; else 0.
* WorldCover: +1 if tree share >= 0.3; -1 if <= 0.05; else 0.

`S` = sum of the available indicators; `n` = number available.

### Family 1 — internal contradiction (class versus independent layers)
* **R1.1 timber without canopy**: class in TU or TL (SB excluded: slash is expected to lack canopy); `n >= 3` and `S <= -3`. Contradicted. Evidence: the four indicators.
* **R1.2 non-timber under dense forest**: class in GR, GS, SH; every indicator +1 (n = 4), TCC >= 50 and canopy max >= 15 m. Contradicted. If `S >= 2` but not all of this: unknown.
* **R1.3 burnable on water**: burnable class; NLCD 11 and WorldCover water share >= 0.5. Contradicted; suggest 98.
* **R1.4 burnable on snow/ice**: burnable class; NLCD 12 and WorldCover snow/ice share >= 0.5. Contradicted; suggest 92.
* **R1.5 burnable on pavement**: burnable class; NLCD 24 and WorldCover built share >= 0.5. Contradicted; suggest 91.
* **R1.6 burnable on bare ground**: class not in {101, 102, 141} and not NB; NLCD 31 and WorldCover bare/sparse share >= 0.7, TCC <= 5, canopy max < 2 m. Contradicted; suggest 99.
* **R1.7 unburnable on vegetation**: class in {91, 93, 99}; NLCD in {41, 42, 43, 52, 71} and WorldCover natural-vegetation share (classes 10, 20, 30, 100) >= 0.7 and built share <= 0.1 and crop share <= 0.1. Contradicted. Suggested group by NLCD lifeform (forest: timber, 52: SH, 71: GR); a specific class is suggested only where section 3.4 allows.
* **R1.9 lifeform contradiction**: class in GR (101-109) with NLCD 52 and WorldCover shrub share >= 0.6 and TCC < 5: contradicted, suggest group SH. Class in SH with NLCD 71 and WorldCover grass share >= 0.6 and TCC < 5: contradicted, suggest group GR. GS is exempt (mixed by definition).

### Family 2 — staleness (the map is older than an event)
Applies to events dated after the map date only.
* **S1 fire since the map**: the cell is inside an NIFC/WFIGS wildfire perimeter with discovery date after the map date AND the LANDFIRE annual disturbance layer for that year marks the cell as fire (any severity) — or Hansen loss year is after the map year at a cell with tree cover 2000 >= 25.
* **S2 harvest or clearing since the map**: LANDFIRE disturbance type in {clearcut, harvest, thinning, mastication, mechanical, development} after the map date, or Hansen loss year after the map year at a cell with tree cover 2000 >= 25 and no S1.
The decode table for LANDFIRE disturbance numeric codes is derived by comparing the layers with the NIFC perimeters and stored in config before any plot is read.

### Family 3 — fire behaviour
* **R3a burned although unburnable**: class in {92, 98, 99} and the LANDFIRE disturbance layers (any year 1999 up to the map year) mark the cell as fire at moderate or high severity **and** the cell lies inside an NIFC perimeter of that year. Contradicted. (91 and 93 are excluded: structures and crop residue legitimately burn.)
* **R3b spread faster than the class can produce**: only where an arrival-time raster exists. Observed normal spread rate at a cell = 1 / |grad T| after smoothing with a 3 x 3 median. Upper bound = head-fire rate of the cell's class from the Rothermel (1972) surface-fire equations as implemented in the published library **pyretechnics** (Johnson, Waeselynck, Lautenberger, Saah, Sig-GIS; https://github.com/pyregence/pyretechnics), at the observed hourly wind (the maximum 10 m wind over the interval between the two perimeters that bracket the cell, with the library's wind-adjustment factor from LANDFIRE canopy height and cover), the cell's slope and aspect, and a fast-spread moisture scenario (dead fuel moisture 1-h 3 %, 10-h 4 %, 100-h 6 %; live herbaceous 40 %, live woody 60 %). Contradicted if observed > 2 x bound (the factor 2 allows spotting and model error; surface equations do not model crown fire, so the rule is silent for TU/TL/SB cells with canopy cover >= 40 %). No suggestion is made from R3b.

### 3.4 Suggestions and the overlay
A suggested class is written only when a rule points to a specific one: R1.3 (98), R1.4 (92), R1.5 (91), R1.6 (99), and for group-level suggestions (R1.1 via NLCD lifeform, R1.7, R1.9) the **most frequent class of the suggested group among the 'consistent' cells in the surrounding 11 x 11 window** if at least 5 such cells exist; otherwise no class (the group is still reported). The source map is never rewritten.

### 3.5 Verdict
Per cell, in order: U0 -> `unknown`. Then:
1. any staleness rule fired -> `stale` (contradiction rules that also fired are listed);
2. else any contradiction rule (R1.x, R3a, R3b) fired -> `contradicted`;
3. else `consistent` if `n >= 3` (independent layers available) and the class is supported: timber class with `S >= 2`; non-timber burnable class with `S <= 1` and no R1.2/R1.9 near-miss (S in {2,3} is unknown); NB class whose own layer agrees (98: NLCD 11 or WorldCover water >= 0.5; 92: NLCD 12; 91: NLCD 21-24 or built >= 0.3; 93: NLCD 81/82 or crop share >= 0.3; 99: NLCD 31 or WorldCover bare >= 0.5 or no vegetation by the indicators);
4. else `unknown`.
Output per cell: verdict code, bit-set of rules fired, suggested class (or 0), and an **evidence card** (the indicator values, layer values, event dates and the thresholds crossed). Cards are generated for every cell that is not `consistent`, written as compact tables, and rendered to text/HTML on demand for any cell.

## 4. Field plots: used only to grade

**Source.** Landscape Data Commons public API (`geoIndicators`, `geoSpecies` filtered to trees), BLM Assessment, Inventory and Monitoring (AIM) plots, `ProjectKey = BLM_AIM`. Other projects in the API are excluded: LandPKS (user-entered locations), NRI (locations obscured by design), and small research projects with mixed coordinate quality. FIA plots are excluded: public FIA coordinates are perturbed by up to 1 mile, which is larger than the plot scale at the cell level.

**Eligibility.** Latitude/longitude present (reported, GPS), `TotalFoliarCover` present, visit year >= 2019, CONUS, inside one of the study areas. One plot per location (rounded to 5 decimals): the most recent visit. Plot-to-cell: the 30 m cell that contains the plot point.

**Plot variables.** F = TotalFoliarCover; Sh = AH_ShrubCover; H = AH_GraminoidCover + AH_ForbCover; B = BareSoil; R = FH_RockCover; W = FH_WaterCover; T = sum over tree species of AH_SpeciesCover, capped at 100 (0 if none recorded). All in percent.

**Plot structural class and compatible map groups** (first match wins):

| Plot class | Test | Compatible map groups |
|---|---|---|
| P_WATER | W >= 50 | NB |
| P_TREE | T >= 20 | TU TL SB GS SH |
| P_OPENTREE | 10 <= T < 20 | GR GS SH TU TL SB |
| P_BARE | F < 10 and B + R >= 50 | NB GR GS SH |
| P_GRASS | H >= 10 and Sh < 10 | GR GS |
| P_SHRUB | Sh >= 10 | GS SH, plus GR if H >= 2 x Sh |
| P_SPARSE | otherwise | NB GR GS SH |

A plot **disagrees** with the map if the group of the map class in its cell is not in its compatible set; it **agrees** otherwise. This is a structural proxy for a fuel class, not an official fuel-model determination; section 13 states what it does not show.

**Hold-out.** The agent package contains no import of the plot loader (enforced by a test). The agent never sees a plot. Plots are read only by `firewitness/fuel/grade.py`, which refuses to load sealed areas except through the sealed-run command (section 8).

## 5. Study areas

Tiles of 60 km x 60 km on the EPSG:5070 grid, origin (-2362395, 221265): tile `T{tx:03d}_{ty:03d}` covers x in [-2362395 + 60000 tx, +60000 (tx+1)), y likewise. Candidates: tiles in CONUS with at least 100 unique eligible plot locations (178 tiles). Assignment (deterministic, uses only plot counts and a hash, no verdicts): sort candidates by SHA-256 of `fuel-areas-v1|T{tx:03d}_{ty:03d}`; walk the list, give the next tile to **dev** while dev has fewer than 10, else to **sealed** while sealed has fewer than 10, skipping any tile within Chebyshev distance 1 of a tile already assigned to the other split (so dev and sealed never touch). Result:

* **Dev (10):** T012_030 (NV), T008_029 (NV), T016_033 (ID), T015_024 (UT), T012_036 (ID), T021_025 (CO), T016_037 (ID), T016_026 (UT), T010_033 (NV), T021_028 (CO).
* **Sealed (10):** T019_033 (WY), T016_039 (ID), T012_018 (AZ), T023_036 (WY), T009_036 (OR), T007_037 (OR), T012_027 (NV), T015_015 (AZ), T013_024 (UT), T023_042 (MT).

Consequence for generality (stated here, repeated in results): all 20 areas are in the interior West, dominated by rangeland and woodland; results do not speak to eastern or humid forest fuels.

## 6. Gates (all on M22; pooled over the areas of the split being evaluated)

Definitions. `n_c`, `n_k`, `n_s`, `n_u` = plots whose cell verdict is contradicted / consistent / stale / unknown. `d_c`, `d_k` = share of those plots that disagree.

* **F1 (the cells the agent distrusts are the ones the field disagrees with).** `R = d_c / d_k`. **Pass** if the lower end of the 95 % interval of `R` is > 1. The interval is a percentile cluster bootstrap (2000 resamples, seed 53053), clusters = 10 km x 10 km blocks of the EPSG:5070 grid. Not evaluable (reported as such, never as a pass) if `n_c < 25` or `n_k < 100`.
* **F2 (placebo: false alarms where the field agrees).** Among plots that **agree** with the map, the share whose cell the agent calls contradicted must be **below 10 %** (limit frozen here: `L_F2 = 0.10`). **Pass** if the upper end of the 95 % Wilson interval of that share is below 0.10 (cluster-bootstrap interval reported alongside). A second placebo is reported, not gated: for every plot, take the verdict of a random cell in the same tile at least 5 km away (seed 53054) and recompute `R`; its interval should include 1.
* **F3 (read-only and reproducible).** (a) SHA-256 of every source input file is identical before and after a run, the source files are opened read-only, and the run fails if any hash changes; (b) two runs on the same inputs produce byte-identical overlay files (SHA-256 equal).
* **Stretch (labelled as such, not a gate).** See section 11.

Secondary quantities always reported with n and interval: the same ratio for `stale` vs `consistent`; verdict shares; `R` and plot counts per rule and per area; `unknown` share; and, for every rule, the share of its calls that land on plots at all.

## 7. Output contract
For an area: `verdict.tif` (uint8: 0 nodata, 1 consistent, 2 stale, 3 contradicted, 4 unknown), `rules.tif` (uint32 bit-set of rules), `suggest.tif` (int16, 0 = none), `overlay.json` (grid, inputs hashed before and after, config hash, code version, counts), `cards.jsonl` (evidence cards for non-consistent cells), a PNG map, and a Markdown report. Inputs, config and code version are hashed into the overlay manifest.

## 8. Sealed areas
Layers for sealed tiles may be downloaded in advance. Plots of sealed tiles are not loaded, counted, or looked at before the sealed run. The sealed run is one command that (1) verifies the rule version equals the frozen hash recorded in the repository at the commit that ends the improvement loop, (2) writes `results/sealed_opened.json` containing the commit and time, (3) computes F1/F2/F3 once. The command refuses to run if that file exists. Whatever the sealed result is, it is reported as the result; the rules are not edited afterwards for sealed performance (a later change would be a new version, evaluated on new sealed areas).

## 9. Improvement loop
After version 1 is run on the dev areas (and passes the gates, or fails them — either is logged), at most **12 rounds**. Each round: read every wrong verdict against the dev plots (a wrong verdict = a contradicted cell where the plot agrees, or a consistent cell where the plot disagrees); name **one** cause; change or add **one** rule or one parameter; rerun on dev. **Keep the change only if the F1 ratio `R` rises and the F2 false-alarm share does not rise** (both pooled over the dev areas, point estimates, and `n_c` stays >= 25). Otherwise revert. Every round, kept or not, is written to `results/ROUNDS_fuel.md` with the cause, the change, before/after numbers and the decision. The loop uses dev plots only. Overfitting is controlled by the sealed run, not by the loop.

## 10. What counts as the first version
Version 1 is exactly sections 3 and 4 as written here, run once on the dev areas. Its numbers are the baseline of the loop.

## 11. Stretch: the 29 fires
The original set of 29 US fires with LANDFIRE and arrival-time rasters is not available in this environment. It is rebuilt from public sources (daily NIFC/GeoMAC perimeters 2017-2019, LF2016 fuels, Open-Meteo wind); the exact selection and its differences from the original are recorded in `firewitness/fuel/fires29/NOTES.md` and `DECISIONS.md`. Arrival time is interpolated between perimeters, so spread rates are coarse (daily) and this stretch is weak evidence by construction.

Test: for each fire, run the agent on the LF2016 fuel map; replace the cells that are contradicted **and carry a suggested class** by that class (a copy; the source is untouched); run a simple minimum-travel-time spread calculation (8 neighbours, Rothermel head-fire rate by class under the observed hourly wind, same moisture scenario as R3b, ignition = the first perimeter) on the original and on the replaced map; compare predicted arrival with observed arrival over cells inside the final perimeter (mean absolute error in hours). Report per fire and the paired difference with a bootstrap interval over fires. Fires where no cell was replaced are listed and excluded from the paired statistic. A result either way is reported; "no improvement" is a valid result.

## 12. Korea
`firewitness/fuel/config/kr.json` holds a stub: forest type map classes and a translation table to the fuel groups of section 3. It is **untested**, labelled so in the file, and not used by any gate.

## 13. What this design does not show (stated in advance)
* The plot proxy measures vegetation structure at the plot, not fuel-model correctness; a plot can be "compatible" with a wrong fuel model and "incompatible" with a right one. Disagreement rates are therefore not error rates.
* AIM plots lie on public rangeland in the interior West; no eastern, southeastern or urban fuels, and few dense-forest fuels, are graded.
* The independent layers are not physically independent of LANDFIRE inputs (shared imagery); rules can fail together.
* Plots are 0.5-ha-scale samples compared to one 30 m cell.
* Rules R3b and the stretch rest on arrival times built from daily perimeters, which are coarse.
* Passing F1/F2 shows the agent's calls carry information about field structure; it does not show that replacing cells improves any downstream model.

## 14. Reproducibility
Plots, fuel maps, and layers are fetched by scripts in `firewitness/fuel/fetch/`; each download is hashed and indexed in the raw folder. Randomness is limited to the bootstrap and the spatial placebo, both with the seeds above. Verdicts use no randomness.

## Amendment A1 (2026-11-20, before any verdict or plot comparison existed)
Reason: while building the staleness and fire rules it was found that LANDFIRE annual disturbance codes are not stable across releases and lag the events. Compared with NIFC wildfire perimeters in tile T010_033: in the LF2023 layer fire pixels carry codes 47x (data-source digit 4, type 7, severity 1-3); in the LF2024 layer only 2 % of 2024 wildfire-perimeter cells carry any code; in the LF2025 layer the fire codes are 20xx. No numeric decode is therefore used. Changes to sections 2 and 3 (nothing else changes):

* **S1 fire since the map**: the cell lies inside an NIFC/WFIGS perimeter of kind wildfire with fire year greater than the map year. (The Hansen/LANDFIRE corroboration clause is dropped.)
* **S2 tree-cover loss since the map**: Hansen loss year (2000 + value) greater than the map year at a cell with tree cover 2000 >= 25, and S1 did not fire. (The LANDFIRE harvest/clearing/development type clause is dropped; Hansen loss cannot tell harvest from fire from other loss, and the card says so.)
* **R3a burned although unburnable**: class in {98, 99} (92 and 91, 93 stay excluded as before); the cell lies inside a wildfire perimeter of year Y <= map year **and** the LANDFIRE annual disturbance layer for year Y (any nonzero code, no decode) is nonzero at the cell. LANDFIRE disturbance layers are fetched only for years with a perimeter in the area.
* Fire perimeters come from three NIFC services merged by year (history all-years view, 2020s view, WFIGS interagency perimeters); prescribed fire perimeters are not used for S1 and R3a. Fire year, not discovery date, is the resolution; this is why map dates are 1 January.

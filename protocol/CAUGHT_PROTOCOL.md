# CAUGHT protocol (track 50): labels for the fires satellite products missed

Status: fixed before any result. Committed alone. Amendments go at the bottom with the date, the reason, and whether
any result had been seen. Nothing above the amendment log changes after this commit.

## 1. Question and headline

Satellite fire labels miss small fires. The headline is one count: **fires that an agency recorded, that no standard
satellite product labelled, and that now carry a verified label**, reported by size class (NWCG A to G) and by slice.

## 2. Inputs

**Records (the agency record).** FPA FOD 7th edition (USDA Forest Service Research Data Archive RDS-2013-0009.7,
`FPA_FOD_20260615.sqlite`, 1992-2024, 2,661,383 records). Fields used: FOD_ID, LATITUDE, LONGITUDE, DISCOVERY_DATE,
DISCOVERY_TIME, CONT_DATE, CONT_TIME, FIRE_SIZE (acres), FIRE_SIZE_CLASS, STATE, MTBS_ID. Records are read, never
written. If track 49 publishes cleaned locations or uncertainty radii before slice 3 starts, they may replace the
raw ones only through an amendment.

**Slices, in this order, each reported complete before the next starts:**
S1 California 2020 (10,360 records); S2 all US 2020 (74,530); S3 all US 2018-2020 (220,975).

**Standard label** = any detection by one of these products inside the record's space-time window (section 4):

| product | what | resolution | access |
|---|---|---|---|
| MODIS C6.1 active fire, Terra and Aqua (MCD14ML) | heat | 1 km | FIRMS archive, standard processing, yearly US files |
| VIIRS 375 m active fire, S-NPP (VNP14IMG) | heat | 375 m | FIRMS archive, standard processing |
| VIIRS 375 m active fire, NOAA-20 (VJ114IMG) | heat | 375 m | FIRMS archive, standard processing |
| MODIS C6.1 burned area (MCD64A1) | burned area | 463 m | NASA LP DAAC (Planetary Computer copy) |
| MTBS burned area boundaries | burned area | 30 m | mtbs.gov composite perimeter file |
| ESA FireCCI51 burned area | burned area | 250 m | CEDA archive; included only if it can be fetched; if not, the headline states it was not checked |

These are the products routinely used as fire labels (the "usual two" sensors and their burned-area products).
Everything else below is an *additional look*, not a standard label.

**Additional looks (heat).** GOES-16/17 ABI fire detections and AVHRR (MetOp-A/B, NOAA-15/18/19) detections from the
NOAA Hazard Mapping System daily fire points (methods FDC, ABBA, FIMMA and analyst-added points); raw GOES ABI FDC
from the NOAA open-data bucket where it adds looks HMS lacks; Landsat 8 30 m hot spots computed with the published
Landsat-8 active-fire tests (Schroeder et al. 2016) on Collection 2 data; Sentinel-2 short-wave hot spots in 20 m
bands; at night, the VIIRS day/night band (Black Marble VNP46A1) where the background is dark. Each source is
confirmed or marked NOT REACHED in results with the reason.

**Additional evidence that is not heat.** SCAR: burn scar in Sentinel-2 L2A (10/20 m) and Landsat 8 Collection 2 L2
(30 m). SMOKE: HMS analyst smoke polygons drawn on GOES visible imagery, attributed only under the rule in 6.3.
PERIMETER: agency perimeters (MTBS, NIFC interagency perimeter history, CAL FIRE FRAP; FACTS treatment polygons are
not used as evidence).

All raw files are downloaded to `wildfire 3 (1)/firewitness_raw/` and listed with sha256 in its INDEX.md. Image
windows read from cloud-optimised files are written to disk with their sha256 in a manifest before use; the manifest
is kept, the windows are deleted after extraction.

## 3. Evidence kinds and independence

| kind | witnesses |
|---|---|
| HEAT | MODIS, VIIRS S-NPP, VIIRS NOAA-20, GOES (HMS or raw), AVHRR (HMS), Landsat 30 m hot spot, Sentinel-2 SWIR hot spot, VIIRS DNB night light |
| SCAR | Sentinel-2 scar, Landsat scar, MCD64A1, FireCCI51, MTBS |
| SMOKE | HMS smoke (attributed) |
| PERIMETER | NIFC perimeter history, CAL FIRE FRAP |

Declared dependencies (a pair that may not count as two kinds): MCD64A1 with MODIS heat (MCD64A1 uses MODIS
active fire); FireCCI51 with MODIS heat; MTBS with PERIMETER (MTBS uses agency records to pick fires); HMS analyst
points with any satellite heat point they copy. Two items are *independent kinds* when their kinds differ and the
pair is not in this list.

## 4. Space-time window of a record

* Location uncertainty `r_loc` = max(250 m, half the diagonal of the rounding cell implied by the coordinate's
  decimal places). `r_fire` = radius of a circle with the recorded area. Search radius `r = r_loc + r_fire`.
* Records with `r_loc` > 3 km and size class below D are not searched at pixel level (record-only, reason
  "location too uncertain"); their honest radius is kept in the label.
* Time window: from DISCOVERY_DATE minus 1 day to CONT_DATE plus 1 day. If CONT_DATE is missing, earlier than
  discovery or more than 180 days later, the end is discovery plus a default by class (A, B: 1 day; C: 3; D, E: 7;
  F, G: 30). Satellite times are UTC; record dates are local; the one-day margins absorb the offset.
* A heat detection agrees in place if its pixel footprint (scan x track, or the published pixel size) intersects
  the search disc; in time if its acquisition time is inside the window. A burned-area pixel agrees if it touches the
  disc and its burn date (plus or minus its own uncertainty, at least 1 day) overlaps the window. MTBS and perimeter
  polygons agree if they intersect the disc and their dates overlap the window.

## 5. Label tiers (through `firewitness.core.evidence`)

Each witness reports agree (True), clear look with nothing found (False) or no look (None) for the hypothesis "this
recorded fire burned inside its window". `combine()` returns the posterior and decision for the record; m and u per
witness are measured, not assumed: u from the placebo windows of the dev split, m from the dev truth fires (section 8).
The tier is set by the count of agreeing independent kinds (the posterior is reported beside it):

* **verified**: at least two independent kinds agree with the record and with each other in place (footprints within
  each other's geolocation error) and time (intervals overlap).
* **probable**: exactly one kind agrees.
* **record-only**: no kind agrees. The fire is kept with its honest radius, time window and one reason:
  `below_floor` (recorded size below the smallest fire every look could see), `no_clear_look` (cloud, shadow, snow,
  no acquisition), `location_too_uncertain`, or `clear_look_nothing_found` (clear looks above the floor, no evidence).

No recorded fire is dropped. The pixel label of a verified or probable fire is the union of its scar component(s) and
the footprints of agreeing heat pixels clipped to the search disc; for heat-only fires it is the heat footprints.

## 6. Scar finder

6.1 Looks. Sentinel-2 L2A at 20 m (B8A, B11, B12, SCL) with B02, B03, B04 at 10 m; Landsat 8 C2 L2 at 30 m
(SR_B2..B7, QA_PIXEL). Pre image: the latest acquisition before the window start (up to 60 days before) where the
disc is at least 80 % clear; post image: the earliest after the window end (up to 45 days after), same rule.
Cloud, cloud shadow, cirrus, snow, water, saturated and no-data pixels are masked (SCL classes 0, 1, 3, 6, 8, 9, 10,
11; QA_PIXEL bits fill, dilated cloud, cirrus, cloud, shadow, snow, water). Pixels masked in either image are unknown.

6.2 Candidate pixels: dNBR = NBR_pre - NBR_post with NBR = (NIR - SWIR2) / (NIR + SWIR2), and all of:
dNBR >= T (T = max(0.10, median + 3 * robust sd of dNBR over the window's clear land pixels outside the disc));
NIR falls (NIR_post < NIR_pre - 0.01); the visible bands do not brighten (mean of blue, green, red rises by less than
0.02: char and ash darken, ploughed or harvested soil brightens). Components are 8-connected groups of candidate
pixels; no dilation, filling, smoothing or interpolation. A component counts if it has at least N_min = 4 pixels and
intersects the search disc.

6.3 Rejections (harvest, ploughing, seasonal browning, other fires):
* Same dates in other years: dNBR over the same calendar pre/post dates one year earlier (and two years earlier if
  the first is cloudy) in the same pixels. If the median of the component there is at least half its current
  median, the change recurs seasonally: rejected.
* Neighbouring land: if more than 25 % of the clear land in the window outside the disc is also candidate, the change
  is regional (browning, frost, wide harvest): rejected.
* Attribution: a component larger than 20 x the recorded area plus 10 ha belongs to a bigger event: rejected for
  this record (still reported as a candidate for that bigger event).
* HMS smoke counts as SMOKE for a record only if a smoke polygon of the record's local day contains the disc centre,
  has an area below 2,500 km2, and contains no other recorded or detected fire of class C or larger that day.

6.4 Module. `firewitness.caught.scar` exposes `find_scar(...)` for small fires and `make_perimeter(...)` for large
fires without a mapped perimeter (track 49), returning geometry, dates, sensor, threshold, floor and status.

## 7. Three states and the floor

Every place and time in a searched window is **fire** (inside a verified or probable pixel label), **verified no
fire** (a clear look covering it found nothing) or **unknown** (no clear look). A *scar look* covers the whole
interval between its pre and post images; a *heat look* covers its overpass instant only. "Verified no fire" is
written only for scar looks (clear pre and post pair) and carries the scar floor; heat looks add their instant floors
to the evidence list.

Floors (smallest fire that would have been seen there and then), from the sensors' algorithm documents:
* Scar floor: f_min = T / dNBR_ref, the burned fraction a pixel needs to pass the threshold T of that window
  (dNBR_ref = 0.25, the low-to-moderate severity a small fire leaves). Floor = (sqrt(N_min) + 1)^2 x p^2 x f_min
  (enough pixels pass under any grid alignment), p the pixel size; infinite if f_min > 1.
* Heat floor: the smallest flaming area (800 K) whose pixel 4 um brightness temperature exceeds the background by the
  contextual and absolute tests of the algorithm (MODIS C6 Giglio et al. 2016; VIIRS 375 m Schroeder et al. 2014;
  GOES ABI FDC ATBD; Landsat-8 Schroeder et al. 2016), given the pixel area at the view angle (scan geometry), the
  background temperature and its noise. Where the view angle of a non-detection is unknown, the edge-of-scan floor
  is used (the floor that holds whatever the angle).
* A record whose recorded area is below the scar floor of every possible look is `below_floor` and is not searched.

## 8. Truth, splits and gates

**Dev and sealed test.** Truth for small fires = mapped fires and prescribed burns of known place, date and area:
CAL FIRE FRAP wildfire and prescribed-burn perimeters and NIFC interagency perimeter history, 2018-2020, mapped area
below 300 acres (classes A to D), and above-300-acre fires as a reference stratum. FACTS broadcast-burn polygons
form a secondary stratum reported but not gated (the polygon is the planned unit, not the burned area). Split by
sha256(source id) mod 10: 0-2 dev, 3-9 sealed. FPA FOD records split the same way by FOD_ID for reading misses.
The sealed test is opened once, at the end, after the rules are frozen.

On truth fires the input is record-like: the polygon centroid, r_loc = 250 m, the recorded start and end dates and
the mapped area. PERIMETER evidence is switched off for truth runs (the perimeter is the answer). A truth fire is
*caught* if a label's pixels intersect the polygon (buffered 30 m) in its window; it is caught by the standard label
if a standard detection footprint or pixel intersects the polygon in the window.

**C1 placebo.** For every searched record, one matched placebo: same state, date window, radius, recorded size and
ESA WorldCover majority class (200 m), 10-50 km away, with no FPA FOD record within 5 km and 30 days of the window
and no agency or MTBS perimeter intersecting it in the window. Gate: at most 1 % of placebos reach verified
(reported with a 95 % Clopper-Pearson interval, among searched placebos and among all). Added guard of this track:
at most 5 % of searched placebos reach probable.

**C2 small-fire recall.** Primary: recall of labelled (verified or probable) truth fires minus recall of the
standard label, by size class with n >= 30 in the sealed test, paired cluster bootstrap (cluster = 0.5 degree cell
x year, 2,000 resamples). Pass: every such class's 95 % interval excludes zero on the positive side. Verified-only
recall is reported beside it.

**C3 integrity.** Every input is hashed (raw file index, window manifest); a run verifies the hashes of its inputs at
the end. No trained model writes a label. No smoothing, interpolation, dilation or hole filling puts fire where no
evidence does; a test asserts every fire pixel is a candidate pixel or a heat footprint.

## 9. Improvement loop

After version 1 passes its tests: at most 12 rounds on dev records, dev placebos and dev truth. Each round: read the
full record of every miss and every placebo hit, name one cause, change the rules, rerun. Keep a change only if dev
catches rise and the dev placebo rates (verified and probable) do not rise. Log in results/ROUNDS_caught.md.

## 10. Downstream check

Once, after the labels are tagged: with wildfireguardian Main, recompute the held-out miss rate of its fixed margin
and its forecast-against-persistence comparison with these labels. Reported whichever way it goes; nothing changes
afterwards. If it cannot be done: NOT RUN and why.

## Amendment log

(none)

# Data card — firewitness live v0.1 (track 51)

## What is released
| file | content |
|---|---|
| `onset_labels.csv` | one row per fire (240 US wildfires, 2023-01 to 2025-04): first standard detection (anchor), trace-back onset (first frame distinguishable from background) with a 95 % interval, earliest plausible start, which satellite(s) support it and whether the two agree, and leads against the operational GOES fire product, the first polar detection and agency discovery |
| `traceback_by_satellite.csv` | the same per fire and satellite (GOES-16, GOES-18), with the CUSUM evidence S at the anchor and the threshold h_A |
| `replay_test.csv`, `replay_test.json` | strictly causal replay of the frozen detector on the 120 sealed test fires: alert time, operational time, lead; the whole curve over false-alert budgets |
| `live_export_v0.1.tar.gz` | ten fires for the video tool: frame series (bands 7, 14, 1, cloud mask), the pixel signal and every method's detection time |
| `detector_us.json` | the frozen detector settings and threshold |

## Sources (all public, no key)
- Fires: WFIGS Incident Locations (NIFC ArcGIS service), snapshot SHA-256 in `protocol/LIVE_PROTOCOL.md`.
- Polar detections: NASA FIRMS country archive, VIIRS S-NPP (confidence nominal/high) and MODIS (≥ 30). NOAA-20 is not
  in that archive.
- Geostationary: NOAA GOES-16 / GOES-18 ABI L1b CONUS radiances (bands 1, 7, 14), L2 clear-sky mask (ACMC), L2 fire
  product (FDCC), from the NOAA open-data S3 buckets. Availability time = S3 LastModified + 30 s.

## How labels were made
Protocol: `protocol/LIVE_PROTOCOL.md` (frozen before results; amendments dated). Per pixel, ΔT = BT(3.9 µm) − BT(11.2 µm)
minus the median of its 9×9 annulus, compared with its own seven previous days at the same clock time (± 5 min);
cloud and cloud edges masked with ACMC. A CUSUM of the 3×3 site score runs from 12 h before the anchor; an onset is
claimed only when the evidence before the anchor exceeds the 99th percentile of the same statistic at placebo anchors
(same site on fire-free days and fire-free sites 24–34 km away). The interval comes from 200 bootstrap resamples of the
background days.

## What the labels do not show
- The onset is when GOES could first tell the fire from its background, not ignition. Fires smaller than GOES can see
  (2–4 km pixels) keep the anchor as their label.
- Fires without any polar detection within 3 km and 72 h of discovery are not in the list; fires with heat within 5 km
  in the 9 previous days are excluded. The list is a stratified sample (60 per size class), not all US fires.
- Placebo sites are "fire-free" only by the records (FDCC, FIRMS); unrecorded small fires and land-surface changes
  (harvest) count as false alerts, so false-alert rates are upper bounds for true false alarms.
- The cloud mask is from the same instrument (ABI), produced by a separate algorithm.
- Agency discovery times are as recorded in WFIGS; their precision varies by agency.

## Licence and contact
Code MIT (repository licence). Derived tables CC BY 4.0. Source data under their providers' terms (NOAA, NASA, NIFC).

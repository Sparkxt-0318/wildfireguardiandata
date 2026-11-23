# Data card — early_growth_v0.1 (early growth rate of fire power)

**What it is.** One row per fire and satellite: how fast the fire's radiated power rose in its first 1, 3 and 6 hours,
measured from the raw 5-minute GOES ABI frames (2 km, 3.9 µm), with a bootstrap interval and one of three states.
An attribute that no agency incident record holds. Protocol: `protocol/GROWTH_PROTOCOL.md`; results:
`results/GROWTH_RESULTS.md`; release `growth-v0.1`.

**Fires.** Set A: the 370 fires of the earlier live lists (2023-01 to 2025-04 and 30 California 2020 fires; used
before, descriptive). Set B: 310 new WFIGS wildfires, 2023-01-10 to 2025-12-31, stratified by final size, 155 dev and
155 sealed (column `split`). Final sizes (`acres`) are WFIGS final or current incident size at the 2026-11-23 snapshot.

## Columns

| column | meaning |
|---|---|
| `fire_id` | WFIGS UniqueFireIdentifier (Set B, most of Set A) or `CAUGHT-FOD<id>` (2020 supplement) |
| `perm_id` | permanent fire id from the records crosswalk (release records-v0.1) where the fire links; empty otherwise (the crosswalk holds FPA FOD, MTBS and ICS-209-PLUS ids to 2020, so WFIGS fires of 2023–2025 do not link) |
| `set`, `split` | A / B; A, dev or sealed |
| `size_class`, `acres` | final size class (0: 10–100, 1: 100–1,000, 2: 1,000–10,000, 3: ≥ 10,000 acres) and acres |
| `sat`, `role` | GOES-16/17/18/19; east or west |
| `t0` | start time (UTC): the earlier of the frozen trace-back onset and the first standard detection |
| `t0_kind` | `onset_traceback`, `first_detection_fdc` (GOES fire product) or `first_detection_polar` (VIIRS/MODIS) |
| `T0` | first standard detection (anchor) |
| `local_solar_hour_t0` | UTC hour of t0 + longitude / 15 (mean solar time, 0–24) |
| `p0_mw`, `p0_lo`, `p0_hi`, `p0_state` | fire power (MW) at the first clear frame within 15 min of t0, its frame interval, state |
| `slope_1h`, `slope_3h`, `slope_6h` (+ `_lo`, `_hi`, `_state`) | Theil–Sen slope of fire power (MW per hour) over [t0, t0 + W], 95 % block-bootstrap interval, state |
| `logslope_3h` (+ `_lo`, `_hi`, `_state`) | Theil–Sen slope of ln(P + 1 MW) over the first 3 h (per hour) |
| `doubling_time_h`, `_lo`, `_hi` | ln 2 / logslope_3h when it is positive (hours); upper end `inf` when the interval reaches 0 |
| `npix_slope_1h`, `_3h`, `_6h` (+ `_lo`, `_hi`, `_state`) | slope of the number of fire pixels in the 7 × 7 region (pixels per hour): a coarse measure of spread |
| `n_clear_1h`, `n_clear_3h`, `n_clear_6h`, `n_expected_*` | clear frames in each window, and frames expected at 5-minute cadence (13, 37, 73) |
| `fdc_first`, `fdc_first_power_mw` | this satellite's first operational fire-product detection and its power (7 × 7 fire pixels) |
| `selected` | the satellite used for per-fire numbers (most clear frames in the first 3 h; ties: east) |

## The three states

- **measured** — the value lies beyond the 99th percentile of the same quantity at fire-free placebo anchors of that
  satellite (|slope| for slopes; the value for p0). About 1 % of fire-free anchors are called measured by construction.
- **flat** — enough clear frames, but not distinguishable from the placebo. A flat fire may still be growing, below
  what 2 km pixels can separate from the background.
- **unknown** — too few clear frames (fewer than half the expected frames, at least 6, or no clear frame in the first
  or last quarter of the window). The clear-frame count is in `n_clear_*`. Nothing is filled.

## What the attribute cannot tell you

- **2 km pixels.** Fire power is the 3.9 µm radiance excess of whole pixels over a modelled background. Fires below
  about 30 MW are near the noise; our estimate runs about 1.5× the operational product (live v0.2 S1). A slope is a
  change in radiated power, not in burned area or rate of spread.
- **Cloud and smoke.** Cloudy frames are missing. A fire under cloud in its first hours is `unknown`. Thick smoke or
  pyrocumulus colder than the clear scene is treated as cloud.
- **The afternoon cycle.** Fires grow as the day heats. Compare fires at similar `local_solar_hour_t0`; the slope does
  not remove the daily cycle.
- **No claim about ignition.** t0 is when the satellite could first tell the fire from its background, or the first
  standard detection, never the ignition time.
- **Region.** Power is summed over 7 × 7 pixels (14–20 km). Fires that outgrow it, or spread into the background
  annulus, are underestimated late in the window.
- **Not a forecast.** The link to final size (G4) is an association on past fires.
- **GOES-19** (east from 2025-04-07) uses the onset threshold calibrated on GOES-16.

# GROWTH_RESULTS — early growth rate of fire power in the first hours (track growth)

**Headline: of the 155 sealed new fires, 20 have a measured 3-hour growth rate (12.9 %, 95 % CI 8.5–19.1 %); 60 are flat (not distinguishable from the placebo) and 75 unknown (too few clear frames). G1 placebo PASS; G2 agreement with the operational product PASS (Spearman 0.94); G3 two satellites PASS (small n); G4 NOT MET: the 3-hour growth rate does not separate fires that ended large better than fire power at t0, and does not separate them better than the operational product's first reported power (AUC 0.68 vs 0.74 and 0.81). An association on past fires, not a forecast.**

Protocol: `protocol/GROWTH_PROTOCOL.md` (committed alone with the fire lists at 4ca49a4; amendments inside). Fires: Set A = the 370 fires of the earlier live lists (used before, descriptive only); Set B = 310 new WFIGS fires 2023-01-10 to 2025-12-31, 155 dev and 155 sealed. 1085 fire-satellite series (GOES-16/17/18/19). Thresholds frozen at ea1ff0b (`firewitness/live/config/growth_thresholds_us.json`, SHA-256 054b32ab4fbc…) from 58,517 placebo anchors of Set A and dev; recomputed from the released placebo series: identical. Sealed half opened once at 2026-11-23T23:18:54Z (commit 8e379a9, `results/growth/SEALED_OPENED.md`), after the thresholds were committed; no setting changed afterwards.

Every number below is recomputed from the release files alone by `growth_recompute.py` (release growth-v0.1). Intervals: Wilson 95 % for shares; bootstrap by fire (2,000, seed 0) for correlations, AUCs and medians.

## Headline numbers

| quantity | n | value | 95 % interval | source file | what it does not show |
|---|---|---|---|---|---|
| fires with a measured 3 h growth rate, sealed new fires | 155 tried | 20 (60 flat, 75 unknown) | 8.5 to 19.1 % | `early_growth_v0.1.csv` (from `growth_series_fire.parquet`) | a measured slope says the power changed more than at 99 % of fire-free anchors, not why or how fast the fire spread on the ground |
| fires with a measured 3 h growth rate, dev new fires (descriptive) | 155 tried | 21 (47 flat, 87 unknown) | 9.0 to 19.8 % | `early_growth_v0.1.csv` (from `growth_series_fire.parquet`) | a measured slope says the power changed more than at 99 % of fire-free anchors, not why or how fast the fire spread on the ground |
| fires with a measured 3 h growth rate, Set A (used before; descriptive) | 370 tried | 55 (119 flat, 196 unknown) | 11.6 to 18.9 % | `early_growth_v0.1.csv` (from `growth_series_fire.parquet`) | a measured slope says the power changed more than at 99 % of fire-free anchors, not why or how fast the fire spread on the ground |
| G1: placebo anchors called measured, sealed (worst of 7 slope attributes: npix_slope_6h) | 8,237 anchors | 70 (0.85 %) | 0.67–1.07 % | `growth_series_placebo.parquet` | placebo anchors are fire-free only by the records; unrecorded heat sources count against the method |
| G2: rank agreement of our 3 h slope with the operational product's, sealed | 61 fire-satellites (44 fires) | Spearman 0.94 | 0.87 to 0.97 | `growth_series_fire.parquet` (P, fdc_P) | only frames where the product reports power, so fires it misses early are not in this check |
| G3: two satellites, rank of slope_3h, sealed | 39 fires | Spearman 0.68; same sign 8 of 9 measured on both | 0.36 to 0.90; sign 88.9 % (56.5–98.0 %) | `early_growth_v0.1.csv` | small n; the two views share the ground truth but not the pixels; it is not a check against an independent measurement of the fire |
| G4: AUC, 3 h growth rate, sealed (large = ≥ 1,000 acres) | 76 fires (32 large, 44 small) | 0.68 | 0.54 to 0.81 | `early_growth_v0.1.csv`, `growth_fires.csv` (acres) | an association on past fires, not a forecast: final size also depends on weather, fuel and suppression after the first hours |
| G4: AUC, fire power at t0, sealed (large = ≥ 1,000 acres) | 76 fires (32 large, 44 small) | 0.74 | 0.62 to 0.85 | `early_growth_v0.1.csv`, `growth_fires.csv` (acres) | an association on past fires, not a forecast: final size also depends on weather, fuel and suppression after the first hours |
| G4: AUC, operational product's first power, sealed (large = ≥ 1,000 acres) | 76 fires (32 large, 44 small) | 0.81 | 0.71 to 0.91 | `early_growth_v0.1.csv`, `growth_fires.csv` (acres) | an association on past fires, not a forecast: final size also depends on weather, fuel and suppression after the first hours |
| G4: AUC difference, growth − power at t0, sealed (large = ≥ 1,000 acres) | 76 fires (32 large, 44 small) | -0.06 | -0.26 to 0.13 | `early_growth_v0.1.csv`, `growth_fires.csv` (acres) | an association on past fires, not a forecast: final size also depends on weather, fuel and suppression after the first hours |
| G4: AUC difference, growth − product's first power, sealed (large = ≥ 1,000 acres) | 76 fires (32 large, 44 small) | -0.14 | -0.31 to 0.03 | `early_growth_v0.1.csv`, `growth_fires.csv` (acres) | an association on past fires, not a forecast: final size also depends on weather, fuel and suppression after the first hours |
| median 3 h slope of sealed fires with a measured rate | 20 fires (12 rising) | 91.0 MW/h | -41.5 to 575.1 MW/h | `early_growth_v0.1.csv` | fire power, not area: our estimate runs about 1.5× the product (v0.2 S1), and 2 km pixels mix fire and background |
| median doubling time, sealed fires with measured slope_3h and logslope_3h, rising | 1 fire | 0.51 h | one fire: no interval | `early_growth_v0.1.csv` | the log fit adds 1 MW to every frame; a slow start under a noise floor looks slower |
| Set A: frozen trace-back re-run on the new extraction gives the released label | 370 fires | 370 same (310 no onset, 60 onset within 5 min) | – | `growth_runs.csv`, `growth_fires_set_a.csv` | t0 of Set A is the released label either way; this checks that the re-read satellite data reproduce the frozen method |

## Gates (sealed half, opened once)

**G1 placebo — PASS.** Share of sealed placebo anchors called measured with the frozen thresholds (limit 2 %):

| attribute | anchors | called measured | share (95 % CI) | by satellite (called / anchors) |
|---|---|---|---|---|
| slope_1h | 8,459 | 63 | 0.7 % (0.6–1.0 %) | G16 10/3019, G18 25/3480, G19 28/1960 |
| slope_3h | 8,237 | 43 | 0.5 % (0.4–0.7 %) | G16 13/2925, G18 20/3447, G19 10/1865 |
| slope_6h | 8,237 | 68 | 0.8 % (0.7–1.0 %) | G16 13/2919, G18 29/3476, G19 26/1842 |
| logslope_3h | 8,237 | 51 | 0.6 % (0.5–0.8 %) | G16 11/2925, G18 24/3447, G19 16/1865 |
| npix_slope_1h | 8,459 | 50 | 0.6 % (0.4–0.8 %) | G16 15/3019, G18 19/3480, G19 16/1960 |
| npix_slope_3h | 8,237 | 60 | 0.7 % (0.6–0.9 %) | G16 21/2925, G18 30/3447, G19 9/1865 |
| npix_slope_6h | 8,237 | 70 | 0.8 % (0.7–1.1 %) | G16 27/2919, G18 21/3476, G19 22/1842 |

**G2 agreement with the operational product — PASS.** Spearman 0.94 (0.87 to 0.97) over 61 fire-satellites (44 fires) with at least 6 common frames in the first 3 h (median 20); target 0.6.

**G3 two satellites — PASS.** 39 sealed fires have a usable 3 h window on both satellites: Spearman 0.68 (0.36 to 0.90); of 9 measured on both, 8 agree in sign (88.9 % (56.5–98.0 %)). Targets: ρ ≥ 0.6, sign ≥ 80 %, n ≥ 10. The sign check rests on 9 fires; its interval is wide.

**G4 is it informative.** 76 of 155 sealed fires have a usable slope_3h and a known power at t0 (32 ended ≥ 1,000 acres, 44 stayed below). AUC: growth 0.68 (0.54 to 0.81), power at t0 0.74 (0.62 to 0.85), product's first power 0.81 (0.71 to 0.91). Differences: growth − power at t0 -0.06 (-0.26 to 0.13); growth − product -0.14 (-0.31 to 0.03). The growth rate does not separate large from small fires better than power at t0, and does not separate them better than the product's first power (better = interval of the difference above 0). G4 not met; published as failed. Fires with an unknown slope_3h or no power at t0 (79) are not in this comparison. Association on past fires, not a forecast.

**Time of day (descriptive).** Sealed fires with a usable 3 h window starting 10–18 h local solar time: n = 56, median slope_3h -2.9 MW/h, 18 measured; starting at other hours: n = 24, median -0.7 MW/h, 2 measured. The column `local_solar_hour_t0` is in the table so that a reader can separate the afternoon cycle from the fire.

## Descriptive: dev and Set A

Same computation, same thresholds. Set A fires were used before; dev fires were used to check the pipeline. Nothing was tuned on either.

| part | G1 worst share | G2 Spearman (n) | G3 Spearman (n) | G4 AUC growth / t0 / product (n) |
|---|---|---|---|---|
| dev | 1.2 % (0.9–1.4 %) | 0.82 (61) | 0.87 (30) | 0.74 / 0.57 / 0.79 (64) |
| A | 1.1 % (1.0–1.3 %) | 0.84 (142) | 0.85 (79) | 0.68 / 0.62 / 0.69 (163) |

Start time t0 by kind (fires): sealed: first_detection_fdc 70, first_detection_polar 57, onset_traceback 28; dev: first_detection_fdc 64, first_detection_polar 61, onset_traceback 30; A: first_detection_fdc 168, first_detection_polar 142, onset_traceback 60

## Prior art

Fire radiative power from geostationary orbit has followed individual fires and their daily cycle every 15 minutes since SEVIRI (Roberts and Wooster 2008, IEEE TGRS; Roberts et al. 2009, Biogeosciences), and GOES-16 ABI fire power at 5–15 minutes was evaluated over the Americas by Xu et al. (2021, Science of Remote Sensing). GOES-16 fire-power time series of single fires have been tied to their smoke (Wiggins et al. 2020, GRL), fire growth rates of 80 large Portuguese fires were paired with SEVIRI fire power (Benali et al. 2023, ESSD), and hourly geostationary data for about 9,000 North American fires show about 60 % reaching peak intensity within 24 hours of detection (Luo et al. 2026, Science Advances). The attribute here is not a new kind of measurement but a per-fire, placebo-calibrated slope of the first six hours with a stated state, released with the series it comes from.

## What the attribute cannot tell you

- 2 km pixels: P is the radiance excess of whole pixels over a modelled background; a fire under ~30 MW is near the noise, and a slope says nothing about where in the pixel the fire grows.
- Cloud: cloudy frames are missing, never zero; a fire under cloud for its first hours is `unknown`, with the clear-frame count. Thick smoke flagged as cold cloud is lost the same way.
- The afternoon cycle: fires that start in the morning rise with the heating of the day. `local_solar_hour_t0` is given so that this can be separated; the slope itself does not remove it.
- No claim about ignition: t0 is when GOES could first tell the fire from its background (or the first detection), not when it started.
- Large fires that spread beyond the 7 × 7 region (about 14–20 km) or into their own background annulus lose power to the background; their late slopes are underestimates.
- GOES-19 (GOES-East from 2025-04-07) uses the onset threshold calibrated on GOES-16; its growth thresholds come from its own dev placebo anchors.
- Coverage: 75 of 155 sealed fires are `unknown` for the 3 h slope. The clear-frame rule needs all 9 core pixels and a background with clear history on the previous days; cloud on the fire day or on the background days removes a fire.

Files (release growth-v0.1, checksums in `SHA256SUMS.txt`): `early_growth_v0.1.csv` / `.parquet`, `growth_series_fire.parquet`, `growth_series_placebo.parquet`, `growth_fires.csv`, `growth_runs.csv`, `growth_fires_set_a.csv`, `growth_fires_set_b.csv`, `growth_thresholds_us.json`, `growth_us.json`, `growth_numbers.json`, `growth_provenance.json`, `growth_stats.py`, `growth_report.py`, `growth_recompute.py`, `DATA_CARD.md`, `growth_curves_sealed.png`, `growth_curves.csv`.

# LIVE_PROTOCOL_v0.2 — trace-back v0.2: smoke witness and fire size at onset

Committed alone on 2026-11-21, before any v0.2 computation on any fire, and before the v0.2 test fires are read from
the satellite archive. v0.1 (`protocol/LIVE_PROTOCOL.md`, its results and release) is unchanged. The live detector is
closed as a negative result (D1 failed); v0.2 concerns Part A (onset of known fires) only.

## 1. What v0.2 adds

1. **A second, independent witness: a smoke plume in the daytime visible band** (ABI band 1, 0.47 µm, 1 km; blue is
   the most smoke-sensitive ABI band). A thermal onset is *supported* when a plume is seen at or before it.
2. **The size of the fire at the onset frame, with its uncertainty**: fire radiative power (FRP) from the 3.9 µm
   radiance excess, and the burning area implied by it for fire temperatures 600–1200 K.

The thermal onset itself is the frozen v0.1 method, variant A2 (`results/live/traceback_all_A2_by_satellite.csv`
method; thresholds h_A from the 240 v0.1 fires' placebos: East 35.52, West 31.28). Nothing in it is re-tuned.

## 2. Fires

- **Development:** the 240 v0.1 fires (all already opened) and their placebo series. Every v0.2 threshold is set on
  them by the fixed rules below and frozen (committed with its hash) before the test fires are touched.
- **Test (new, never used):** `protocol/live_fires_v02_test.csv` (SHA-256 `ae0ac7b3b1f3d2b1b5af69c8b27da093d7c170a82b1a82c016c916d7550c49d8`),
  100 fires drawn with `random.Random(52)`, 25 per final-size class, from the v0.1 confirmed pool (WFIGS 2023-01-10 to
  2025-04-05, same exclusions, 2,954 fires) after removing the 240 v0.1 fires and the 30 supplement fires (2,714 left).
  Code: `firewitness/live/firelist.py::build_v02_test`. Satellite series are extracted with the v0.1 extraction
  (same windows, same products) plus the fire product's FRP at its first detection frame. The test is run once.

## 3. Smoke witness (visible band)

Per 1 km pixel of the band-1 box (40 × 40 km around the site), daytime frames only (solar zenith < 80° at the site):
- Cloud: the v0.1 effective cloud mask (ACM with the 11 µm override, amendment 5) of the 2 km grid, repeated onto the
  1 km grid, **without** the 2-pixel buffer (a plume next to its fire is often flagged by ACM; cold cloud is removed by
  the 11 µm test).
- Own history only (no annulus: a plume is spatially extended): r = ρ − median of ρ at the same clock time ±5 min on
  the 7 background days (protocol §3 day sets), scale s = max(0.005, 1.4826 · MAD); z = r / s. A pixel is *bright* when
  z ≥ 3.
- **Plume score P(t)** = number of bright pixels in the 8-connected bright component(s) that come within 3 km of the
  site (0 if none).
- **Plume present** at frame t when P ≥ p* at t and at the previous daytime frame (two consecutive frames).
- **Support window** for a thermal onset t_D: W = [t_D − 60 min, t_D + 15 min]. The onset is **supported** when a plume
  is present at any frame in W. Only onsets whose W contains at least 6 daytime frames are judged ("daytime onsets").
- **Plume lead**: t_D − (first frame of the plume run that is present in W), minutes (positive = plume first).
- **p\***: the smallest integer such that, on the dev temporal placebos (same site, days −1 … −8, leave-one-out history,
  the window W placed at the clock time of each dev fire's anchor T0 minus 30 min), the share of placebo windows with a
  plume present is ≤ 2 %.

## 4. Fire size at the onset frame

For each satellite with a thermal onset, at the frame t_D:
- 3.9 µm radiance L of the 3 × 3 pixels at the site (protocol §3 site), and its background L_bg from the v0.1 background
  model applied to BT7: BT7_bg = annulus median BT7 at t_D + median over the 7 background days (±5 min) of
  (BT7 − annulus median); converted to radiance with the file's Planck constants.
- **FRP** = Σ_pixels A_pix · σ · (L − L_bg)⁺ / a, where A_pix is the pixel's ground area (from its corner positions on
  the fixed grid) and a is the least-squares coefficient of L(T) ≈ a T⁴ for band 7 over 650–1350 K, computed from the
  same Planck constants (MIR radiance method, Wooster et al. 2003).
- **FRP interval (95 %)**: the background term's uncertainty, s_L = 1.4826 · MAD of L − L_bg over the background days
  per pixel, combined in quadrature over the pixels, ± 1.96 · s; plus ±10 % for the T⁴ approximation, added linearly.
- **Burning area** A_f = FRP / (σ (T_f⁴ − T_bg⁴)) for T_f ∈ [600, 1200] K: reported as the interval
  [FRP_lo / σ(1200⁴ − T_bg⁴), FRP_hi / σ(600⁴ − T_bg⁴)] and the point FRP / σ(800⁴ − T_bg⁴).
- **Calibration check**: the same FRP estimate at the operational product's first detection frame of each satellite,
  against the product's own FRP (FDCC `Power`, summed over its fire pixels in the 5 × 5 window).

## 5. Gates (test fires, once)

- **E1, E2**: as in v0.1 (§7 there), on the 100 test fires, with h_A from the 240 v0.1 fires.
- **V1 (smoke false support)**: on the test fires' temporal placebos (as in §3), the share of placebo windows with a
  plume present has a 95 % upper bound ≤ 5 %.
- **V2 (smoke support)**: among test fires with a daytime thermal onset, the share supported by a plume has a 95 % lower
  bound above V1's placebo upper bound. Reported with n, the share with the plume first, and the plume lead.
- **S1 (size calibration)**: on test fire-satellites with an operational detection whose FDCC FRP is valid, the median
  of (our FRP / FDCC FRP) lies in [0.5, 2] with its fire-bootstrap 95 % interval inside [1/3, 3], and Spearman ρ ≥ 0.5;
  n ≥ 20 required, else "not enough data".
- **Size at onset** is reported for every test onset (FRP and area with intervals); no gate, because no independent
  truth exists for the size at the onset frame.

Interval conventions as v0.1 (Wilson 95 % for shares, fire bootstrap 2,000 for medians). Results in a dated v0.2
addition to `results/LIVE_RESULTS.md` (append-only) and `release/live-v0.2/`.

## 6. Frozen before the test

Before any test computation: p\*, the band-7 coefficient a per satellite, and the v0.2 code commit are written to
`firewitness/live/config/traceback_v02_us.json` and committed; its hash is recorded in results.

## Amendments

### Amendment 1 — 2026-11-21T05:45Z — smoke witness cloud mask and plume size cap (results seen: dev only)

State when written: the v0.2 code was run on the 240 dev fires only. The 100 test fires' satellite series were being
extracted (no v0.2 or thermal computation on them, nothing looked at). Nothing in §4 (size) or §5 (gates) changes.

Why: with §3 as committed, 32 % of the dev temporal-placebo windows had a "plume" at p = 1, the p\* rule gave
p\* = 1175 pixels (45/2263 placebo windows), and 2 of 32 dev daytime onsets were supported, both by bright runs
starting 340–435 min before the onset (cloud, not smoke). Large bright components next to cloud were the main source.

Dev exploration (one round, 18 variants, all reported): cloud mask {v0.1 effective cloud with the 11 µm override, no
buffer; ACM ≥ 2 or missing without the override, no buffer; the same with a 2-pixel (2 km grid) buffer} × bright
threshold z ≥ {3, 5} × component size cap {none, 150, 50 pixels}; for each, p\* by the §3 rule and the dev support.

| variant | placebo share at p = 1 | p\* | placebo windows at p\* | dev daytime onsets supported |
|---|---|---|---|---|
| acm_b0_z3_c150 | 0.24 | 97 | 45/2263 | 0/32 |
| acm_b0_z3_c50 | 0.225 | 30 | 45/2263 | 0/32 |
| acm_b0_z3_cNone | 0.301 | 1167 | 45/2263 | 2/32 |
| acm_b0_z5_c150 | 0.185 | 80 | 45/2263 | 0/32 |
| acm_b0_z5_c50 | 0.176 | 28 | 43/2263 | 0/32 |
| acm_b0_z5_cNone | 0.216 | 791 | 45/2263 | 1/32 |
| acm_b2_z3_c150 | 0.094 | 44 | 45/2263 | 1/32 |
| **acm_b2_z3_c50 (chosen)** | 0.084 | 15 | 43/2263 | 4/32 |
| acm_b2_z3_cNone | 0.14 | 1129 | 45/2263 | 2/32 |
| acm_b2_z5_c150 | 0.073 | 23 | 45/2263 | 1/32 |
| acm_b2_z5_c50 | 0.067 | 10 | 42/2263 | 0/32 |
| acm_b2_z5_cNone | 0.096 | 715 | 45/2263 | 1/32 |
| override_b0_z3_c150 | 0.254 | 100 | 43/2263 | 0/32 |
| override_b0_z3_c50 | 0.237 | 33 | 42/2263 | 1/32 |
| override_b0_z3_cNone (as committed) | 0.321 | 1175 | 45/2263 | 2/32 |
| override_b0_z5_c150 | 0.203 | 77 | 45/2263 | 0/32 |
| override_b0_z5_c50 | 0.195 | 30 | 43/2263 | 0/32 |
| override_b0_z5_cNone | 0.238 | 899 | 44/2263 | 1/32 |

Change (replaces the corresponding §3 items):
- Cloud: ACM probably-cloudy/cloudy or missing, **without** the 11 µm override, with a 2-pixel (2 km grid) buffer,
  repeated onto the 1 km grid. (A thick plume flagged as cloud is lost; the witness targets thin early plumes.)
- Plume score P(t): bright pixels (z ≥ 3) in the 8-connected bright components that come within 3 km of the site
  **and have at most 50 pixels** (larger components are treated as cloud or scene change, not an early plume).
- p\* by the unchanged §3 rule on the dev placebos with these settings (expected 15).

Caveat recorded before the test: the chosen variant is the best of 18 on dev support (4/32), so its dev support is
optimistic; the test (new fires, once) is the estimate. All other §3–§6 items are unchanged.

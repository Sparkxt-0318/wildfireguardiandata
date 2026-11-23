# GROWTH_PROTOCOL — early growth rate of fire power in the first hours

Committed alone, with the fire lists and their hashes, before any growth series, attribute or gate value exists.
Release v0.1 and every earlier protocol, result and release stay unchanged. A change after this commit is written
under "Amendments" with its time, its reason, and whether any result had been seen (and which: Set A, dev or sealed).
Every number below is also in `firewitness/live/config/growth_us.json` (SHA-256 at this commit:
`a148b6ee34af2f421be545f51e971613929c0b6310e49ef018b870a64405d822`); where the two differ, this file wins and the difference is an error to be logged.

**What is added.** One attribute per fire that no agency record holds: how fast the fire's radiated power rises in
its first hours, measured from the raw 5-minute geostationary frames, with an interval and one of three states.

**What is reused, unchanged.** From the live track: the GOES reader and boxes (`firewitness/live/goes.py`,
`extract.py`), the anchor T0 (first standard detection, LIVE_PROTOCOL §2), the frozen trace-back onset (variant A2,
thresholds h_A East 35.52 / West 31.28 from `config/traceback_v02_us.json`; nothing re-tuned), the per-pixel
background (LIVE_PROTOCOL §3 with amendments 1 and 5), the fire-power estimate of LIVE_PROTOCOL_v0.2 §4 (passed S1:
median ratio to the operational product 1.49, Spearman 0.72, n = 49), and the placebo design (LIVE_PROTOCOL §5).

## 1. Start time t0

- **t0** = the earlier of (a) the frozen trace-back onset of the fire (the fire label of LIVE_PROTOCOL §4: two
  witnesses → the earlier; witnesses disagree → the later; one witness → it) and (b) T0, the first standard detection
  (the earliest of the operational GOES fire product, codes 10–14/30–34 in the site's 5 × 5 window on either satellite,
  and the first polar detection). The onset, when it exists, is never later than T0, so t0 = onset when there is one.
- **Kind** is recorded: `onset_traceback`, `first_detection_fdc` or `first_detection_polar`.
- Set A: t0 comes from the released onset labels (`results/live/onset_labels_v0.1.csv`,
  `results/live/v02/onset_labels_v02_test.csv`, `results/live/supplement_caught_onset_labels.csv`): `onset_utc` if
  present, else `T0`. The trace-back is re-run on the new extraction only as a reproducibility check (reported; it does
  not change t0). Set B: the frozen trace-back is run once on the new extraction with the frozen h_A.
- One t0 per fire, the same for every satellite.

## 2. Fires

**Set A (used before; results descriptive only):** every fire of `protocol/live_fires.csv` (240),
`protocol/live_fires_v02_test.csv` (100) and `protocol/live_fires_supplement_caught.csv` (30): 370 fires, in
`protocol/growth_fires_set_a.csv` (SHA-256 `6e08f05084596473be1f8beebe420f3b0f5a0c492d45487cf872e4fbaed2c997`).

**Set B (new):** `protocol/growth_fires_set_b.csv` (SHA-256 `b4801738fec41a01f9eecfe82ccfa5eb084299d596367275895282e590038b82`), summary
`protocol/growth_fires_set_b_summary.json`.
- Source: WFIGS Incident Locations (NIFC), `IncidentTypeCategory = 'WF'`, discovery 2023-01-10 to 2025-12-31 (UTC),
  final (or current) size ≥ 10 acres, CONUS. Snapshot `wfigs_incidents_ge10ac_20230110_20251231.json`
  (SHA-256 `2df174dceb7261710fa2d768346e2ea79cc392f06d6c1b99c4577c977fb85d0b`, 13,845 records, read 2026-11-23 on GitHub Actions; kept as a run artifact, not in git).
- Rules of the v0.1 pool, unchanged (`firewitness/live/firelist.py::build`): duplicates within 5 km and 2 days removed
  (largest kept); confirmed by a polar detection (FIRMS country archive, VIIRS S-NPP nominal/high or MODIS confidence
  ≥ 30) within 3 km of the origin in [discovery − 24 h, discovery + 72 h]; excluded if a polar detection lies within
  5 km in [discovery − 9 d, discovery − 24 h]. Site = first polar detection.
- Then excluded: any fire of Set A; any fire within 5 km and 2 days of a Set A fire; discovery in
  [2025-03-28, 2025-04-10) (GOES-East changed from GOES-16 to GOES-19 on 2025-04-07; the day-0 window and its eight
  background days must come from one satellite); a site whose 40 × 40 box is not inside the CONUS grid of any
  satellite operating at discovery.
- Pool after these rules: 3,514 fires (by final-size class 0/1/2/3: 1,508 / 1,475 / 461 / 70). The v0.1 rules give
  3,873; then 340 are Set A fires (every Set A fire from WFIGS is found again), 0 lie near one, 19 fall at the
  satellite switch, 0 are not visible.
- Sample: 80 fires per final-size class (10–100, 100–1,000, 1,000–10,000, ≥ 10,000 acres), all fires of a class if it
  has fewer, drawn with `random.Random(2026)` from the class sorted by fire id. 310 fires (class 0: 80, class 1: 80, class 2: 80, class 3: 70; class 3 has only 70 eligible fires, all taken).
- Split: within each class, fires ordered by SHA-256(fire_id + "growth-v0.1") and alternated **dev / sealed**,
  first dev. Dev 155, sealed 155 (per class 40/40/40/35 each). GOES-East is GOES-16 for 192 fires and GOES-19 for 118.
- Satellites: GOES-East = GOES-16 before 2025-04-07T15:00Z, GOES-19 after; GOES-West = GOES-18. Set A uses the
  satellites it used before (GOES-16/18; GOES-16/17 for the 2020 supplement).
- Code: `firewitness/live/growth/firelist.py`, run on GitHub Actions (`.github/workflows/growth.yml`, mode `lists`).

**Permanent IDs:** `protocol/growth_perm_ids.csv` (SHA-256 `79a9d0c05260a0bbafe0e7b14725bdb4b171fd564296824992da24b5773606bd`). The records crosswalk (release records-v0.1,
`crosswalk_us.parquet`) holds FPA FOD, MTBS and ICS-209-PLUS ids up to 2020. The 30 supplement fires are FPA FOD
records and link by FOD id; WFIGS/IRWIN fires of 2023–2025 are not in the crosswalk and are written as not linkable.

## 3. Data per fire and satellite

As LIVE_PROTOCOL §2 (NOAA S3, no key; only the HDF5 chunks covering the box are read), with two changes:
- the day-0 window is **[T0 − 12 h, T0 + 6 h]** (216 frames at 5 min), so every frame of [t0, t0 + 6 h] is covered
  (t0 ≥ T0 − 12 h and t0 ≤ T0); days −1 … −8 are the same clock window shifted by whole days;
- the band-1 visible channel is not read; on day 0 the fire product is read with its `Power` layer.
The frozen trace-back uses only frames before T0, so the longer window cannot change it.

## 4. The series

Per frame, for an anchor pixel (the fire's site pixel, or a placebo anchor):
- **Background** (frozen, LIVE_PROTOCOL_v0.2 §4): BT7_bg = median BT7 of the clear 9 × 9 annulus at the frame +
  median over the seven background days (±5 min) of (BT7 − annulus median); s = robust scale of that difference
  (1.4826 · MAD, floor 0.5 K). Clouds: the effective cloud of LIVE_PROTOCOL amendments 1 and 5 (ACM with the 11 µm
  override, 2-pixel buffer); a cloudy pixel has no value. Background days: day 0 → days −1 … −7; day −j (placebo) → the
  other seven of −1 … −8.
- **Per pixel:** excess radiance (L − L_bg)⁺ at 3.9 µm, FRP = A_pix · σ · (L − L_bg)⁺ / a (MIR method, a from the band-7
  Planck constants, 650–1350 K); z = (BT7 − BT7_bg) / s. A **fire pixel** has a value, z ≥ 4 and a positive excess.
- **Region:** the 7 × 7 pixels around the anchor pixel (about 14–20 km); **core:** its central 3 × 3.
- **Fire power P (MW)** = sum over every valid core pixel (the frozen v0.2 estimate, unmasked) + sum over the ring
  pixels (region minus core) that are fire pixels. Interval per frame as v0.2: ± 1.96 · sd of the background term
  (s · dL/dT per pixel, in quadrature over the pixels summed) ± 10 % (T⁴ approximation), lower end ≥ 0.
- **Fire-pixel count N** = number of fire pixels in the region (core included, same rule).
- **Clear frame:** all 9 core pixels and at least 30 of the 40 ring pixels have values. Any other frame is **missing**:
  P and N are not computed, never set to zero and never filled.
- **Operational series** (fire anchor, day 0 only): the fire product's `Power` summed over its fire-coded pixels
  (10–14, 30–34) in the same 7 × 7 region; a frame "reports power" when at least one such pixel has a valid power.
- **Kept:** fire anchor, frames with offset τ = scan start − t0 in [−2 h, +6 h]; placebo anchors, [0, +6 h].

## 5. Attributes (per fire and satellite)

Window [t0, t0 + W]: the frames with τ ∈ [−2.5 min, W + 2.5 min]. A window is **usable** when it has at least
max(6, ⌈0.5 · (12 W + 1)⌉) clear frames (W = 1 h: 7; 3 h: 19; 6 h: 37) and a clear frame in its first quarter and in
its last quarter.
1. **slope_1h, slope_3h, slope_6h** (MW per hour): Theil–Sen slope of P against τ (h) over the clear frames of the
   window.
2. **logslope_3h** (per hour): Theil–Sen slope of ln(P + 1 MW) over the 3 h window; **doubling time** = ln 2 /
   logslope_3h when logslope_3h > 0 (hours; otherwise none).
3. **npix_slope_1h, _3h, _6h** (fire pixels per hour): Theil–Sen slope of N; a coarse measure of spread.
4. **local_solar_hour_t0**: UTC hour of t0 + site longitude / 15, modulo 24 (mean solar time; no time-zone table).
   Fires grow with the afternoon heating; this column lets a reader separate the time of day from the fire.
5. **p0_mw**: P at the first clear frame with τ ∈ [−2.5, 17.5] min, with its frame interval (the fire power at t0).

**Intervals** (each slope attribute): moving-block bootstrap over the clear frames of the window in time order,
block 4 frames (20 min), 1,000 resamples, Theil–Sen recomputed, 2.5–97.5 % percentiles. Seed = first 8 hex digits
of SHA-256("fire_id|sat|attribute"). The doubling-time interval is ln 2 over the logslope interval (an upper end
of ∞ when the logslope interval reaches 0).

**Three states** (each slope attribute and p0):
- **unknown**: the window is not usable; the clear-frame count is given with it (n_clear_W of n_expected_W);
- **measured**: |value| above the satellite's placebo threshold for that attribute (§6) (p0: value above it);
- **flat**: usable but not above the threshold (not distinguishable from the placebo).
No gap is filled. local_solar_hour_t0 is always known.

**Per-fire numbers** (headline counts, G4, the figure) use one satellite per fire: the one with the most clear frames
in [t0, t0 + 3 h]; ties → GOES-East. This uses no outcome.

## 6. Placebo and thresholds

- **Anchors** (LIVE_PROTOCOL §5 design): temporal = the fire's own site pixel on days −1 … −8 at t0's clock time;
  spatial = the 8 pixels at (±12, 0), (0, ±12), (±12, ±12) from the site (24–36 km) on day 0 and days −1 … −8 at t0's
  clock time. Up to 80 anchors per fire and satellite.
- **Clean** (the frozen rule widened to the 7 × 7 region): no fire-product code 10–15/30–35 anywhere in the anchor's
  7 × 7 region at any frame of that day's window, and no polar detection within 10 km in [window start − 24 h,
  window end + 24 h]. Only clean anchors are used.
- Each anchor gets the same series and attributes as a fire (§4, §5), from its own t0_d = t0 − d days.
- **Thresholds:** per satellite (G16, G17, G18, G19) and attribute, the 99th percentile (numpy linear interpolation)
  of |value| over the usable anchors of Set A and Set B dev fires (p0: of the value). Written to
  `firewitness/live/config/growth_thresholds_us.json` and committed, with its hash in the results, before the sealed
  half is opened. Never recomputed with sealed anchors.

## 7. The sealed half, opened once

Nothing is tuned: every setting is fixed here. Set A and dev results are computed first and are descriptive. The
sealed series are produced on Actions into a separate artifact (`growth-sealed`) and are not read until the
thresholds file is committed. Then `firewitness live growth open-sealed --i-am-opening-the-sealed-half` runs once:
it refuses if the thresholds file is not committed and unchanged, computes the sealed table and gates, and writes
`results/growth/SEALED_OPENED.md` (time, commit, thresholds hash). No setting changes after that; a failed gate is
published as failed.

## 8. Gates (sealed half, once)

Intervals: Wilson 95 % for shares; bootstrap by fire (2,000 resamples, seed 0, all satellites of a resampled fire)
for correlations and areas under the curve.
- **G1, placebo.** Each of the seven slope attributes, on the sealed fires' placebo anchors with the frozen thresholds:
  the share called "measured" is at most 2 % (point estimate; Wilson interval reported, also by satellite).
  Passes when all seven do.
- **G2, agreement with the operational product.** Sealed fire-satellites with at least 6 frames in [t0, t0 + 3 h]
  that are clear in our series and in which the fire product reports power: Theil–Sen slope of our P and of the
  product's power over exactly those frames. Spearman ρ across fire-satellites; passes when ρ ≥ 0.6 with n ≥ 20
  (otherwise "not enough data"). ρ and its interval are reported either way.
- **G3, two satellites.** Sealed fires seen by both satellites with a usable 3 h window on both: Spearman ρ between
  the two satellites' slope_3h (interval), and among fires "measured" on both, the share with the same sign (Wilson).
  Passes when ρ ≥ 0.6 and the sign share ≥ 0.8 with at least 10 fires usable on both (otherwise "not enough data",
  with n stated).
- **G4, is it informative.** Sealed fires (selected satellite) with a usable slope_3h and a known p0. "Large" = final
  size class 2 or 3 (≥ 1,000 acres); "small" = class 0 or 1. Area under the ROC curve (AUC, Mann–Whitney, ties half)
  of (i) slope_3h, (ii) p0 (fire power at t0 alone), (iii) the operational product's power at its first detection on
  either satellite (the earlier one; its 7 × 7 fire-coded power; a fire the product never detected in
  [discovery − 12 h, discovery + 48 h] scores 0 MW). AUCs and the paired differences (i) − (ii), (i) − (iii) with
  intervals from the same resampled fires. Growth "separates better" than a comparator when the interval of the
  difference lies above 0. This is an association on past fires, not a forecast, and is written that way.

## 9. Outputs and recomputation

- Table `early_growth_v0.1` (CSV and Parquet), one row per fire and satellite: fire id, permanent id where linked,
  t0 and its kind, each attribute with its interval and state, clear-frame counts.
- Release files with SHA-256 sums: per-fire series (compact, per satellite), placebo series, fire lists with the
  dev/sealed marks, final sizes used for G4, the thresholds, and `growth_recompute.py`, which recomputes every number
  in `results/GROWTH_RESULTS.md` from those files alone. It is tested from a clean clone in an empty directory.
- `firewitness live growth` works from the released series on a clean clone.
- Results: `results/GROWTH_RESULTS.md` (headline table: n, interval, source file, what it does not show), a data card,
  one figure (sealed fires, large vs small, first 6 h, medians and bands), release `growth-v0.1`.

## Amendments

**Amendment 1 — 2026-11-23T16:18Z (commit 3300683), implementation of §6, no definition change. Results seen: none** (only the
count of fires processed per part and the error messages of the first full run). In the first full run 6 of 680
fires stopped because on some background days the scan start times drift, so the frames of [t0, t0 + 6 h] differed in
number between days. Placebo frames are now taken at the same 73 slots on every day (the days are whole-day shifts of
one window, §3); a frame whose scan start falls outside [−2.5, 362.5] min is dropped by the window rule of §5, as
before. Every fire's trace-back and series were recomputed from the stored raw arrays with this code, so all 680
fires use one version (DECISIONS D-616).

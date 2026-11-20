# LIVE_PROTOCOL — track 51 (live): early onset of known fires and a live sequential detector

Frozen 2026-11-20, committed alone, before any trace-back, replay or live result exists. Region: United States
(CONUS); every country-specific value is in `firewitness/live/config/us.json`. A change after this commit is written
under "Amendments" with its time and reason and applies only to work done after it. The sealed test fires are opened
once (§6).

## 1. Fires and splits

**Source.** WFIGS Incident Locations (NIFC), `IncidentTypeCategory = 'WF'`, final (or current) size ≥ 10 acres,
discovery 2023-01-10 to 2025-04-05 (UTC), CONUS (AK, HI and territories excluded). Snapshot
`firewitness_raw/live/wfigs/wfigs_incidents_ge10ac_20230110_20250406.json`, SHA-256
`9560e870e2b9dd49717f31fe7a0b80966a4f13a336fbd0d706a5bf2d382b3353`, 10,531 records. Period chosen so that the same
two satellites, GOES-16 (East) and GOES-18 (West), cover every fire.

**Confirmed fire.** A record with at least one polar satellite detection — FIRMS country archive, VIIRS S-NPP
confidence nominal or high, or MODIS confidence ≥ 30, type 0 — within 3 km of the origin point in
[discovery − 24 h, discovery + 72 h]. (The FIRMS country archive is public; its NOAA-20 file is not offered there.)
Prompt 50's verified fires are added as a supplementary list when merged; they never enter the sealed test.

**Exclusions.** Duplicates (another record within 5 km and 2 days; the largest kept). Fires with polar detections
within 5 km in [discovery − 9 d, discovery − 24 h] (heat already present: the previous days would not be a clean
background).

**Pool and sample.** 10,274 records in scope → 9,745 after de-duplication → 2,954 confirmed and clean. Size classes
by final acres: 0 = 10–100, 1 = 100–1,000, 2 = 1,000–10,000, 3 = ≥ 10,000. Sample: 60 fires per class drawn with
`random.Random(51)` from the class sorted by fire id. Within a class, fires are ordered by SHA-256(fire_id + "51")
and alternate **dev / test**. 240 fires: 120 dev, 120 sealed test, 30 per class in each.
List: `protocol/live_fires.csv` (SHA-256 `a2c7fa012cd7588b64914d0bea9f1574b544d3382ad5512ecd77aadb7640e8f8`),
summary `protocol/live_fires_summary.json`. Code: `firewitness/live/firelist.py`.

**Site.** The fire's site is the location of its first polar detection (VIIRS 375 m or MODIS), mapped onto each
satellite's ABI fixed grid. Independent of GOES, identical for both satellites.

## 2. Data per fire and satellite

- Satellites: GOES-16 always; GOES-18 when the site lies inside its CONUS (PACUS) sector with the whole box (below).
- Products (NOAA S3, no key): L1b CONUS radiances band 7 (3.9 µm) and 14 (11.2 µm) at 2 km, band 1 (0.47 µm, the
  visible blue channel, best for smoke) at 1 km in daytime (solar zenith < 85° at the site); L2 clear-sky mask ACMC
  (the independent cloud product); L2 fire product FDCC (the operational geostationary fire product).
- Box: 40 × 40 pixels at 2 km (band 1: 40 × 40 at 1 km) centred on the site pixel. Only the HDF5 chunks covering the
  box are read (HTTP range requests); nothing else is downloaded.
- **Anchor T0** = the first standard detection: the earliest of (a) FDCC on either satellite with a fire code in the
  5 × 5 window around the site pixel, scanned every frame in [discovery − 12 h, discovery + 48 h], and (b) the first
  polar detection (acquisition time). FDCC fire codes: 10–14 and 30–34 (processed, saturated, cloud-contaminated,
  high and medium probability; low probability 15/35 is reported as a variant, never used as the anchor).
- Windows: day 0 = [T0 − 12 h, T0 + 2 h] at 5-min cadence (168 frames); days −1 … −8 = the same clock window
  shifted by whole days.
- Frame time = scan start (file name). Availability time = S3 LastModified + 30 s (processing), used in replay.

## 3. Signal and background (one definition, used by Parts A, B and C)

Per pixel p and frame t: ΔT = BT7 − BT14. Cloudy = ACM ≥ 2 (probably cloudy or cloudy); cloudy or missing → no value.
- **Neighbours:** n(t) = median ΔT of clear pixels in the 9 × 9 window around p minus its central 5 × 5 (≥ 10 needed).
- **Residual:** r_p(t) = ΔT_p(t) − n(t).
- **Own history:** for clock time τ of frame t, the 21 values r_p on the K = 7 background days at τ − 5, τ, τ + 5 min
  (clear only, ≥ 6 needed). b_p(τ) = median, s_p(τ) = max(0.5 K, 1.4826 · MAD).
- z_p(t) = (r_p(t) − b_p(τ)) / s_p(τ).
- **Site score:** Z(t) = max of z over the clear pixels of the 3 × 3 window around the site pixel (m of them, ≥ 1),
  converted to a null-standard score u(t) = Φ⁻¹(Φ(Z)^m), capped at 8.
- Background days: for a fire (day 0) days −1 … −7. For a placebo anchor on day −j, the seven other days of
  −1 … −8. Both use seven days.
- Visible (candidate feature for Part B only): band-1 reflectance residual against the 9 × 9 annulus and its own
  history, defined exactly as above on the 1 km grid, maximised over the 10 km around the site.

## 4. Part A — trace-back

Per satellite, over day 0: CUSUM S(t) = max(0, S(t−1) + u(t) − k) with k = 0.5; a frame with no value leaves S
unchanged. S_pre = S at the last frame with scan start before T0.
- **First distinguishable frame t_D:** the first frame where S ≥ h_A in the run (S > 0 without a return to 0) that
  is still active at T0, provided S_pre ≥ h_A. Otherwise no earlier onset is claimed.
- **h_A (gate E1):** the 99th percentile of S_pre over the placebo anchors of that satellite (§5).
- **Interval:** 200 bootstrap resamples of the seven background days (with replacement; b and s recomputed; h_A
  fixed). Interval = [2.5 %, 97.5 %] of t_D over resamples where an onset is found, the lower end moved back one frame
  (the crossing happened after the previous frame); the share of resamples finding an onset is reported.
- **Start of the evidence run** τ̂ (the frame after S last equalled 0) is reported as the earliest plausible start.
- Compared, per fire, with: FDCC first detection per satellite (and with low-probability codes), first polar
  detection, agency discovery time. Lead = reference − t_D (minutes; positive = earlier than the reference).
- **Fire label:** both satellites find t_D and agree (E2) → the earlier, "two witnesses"; one satellite only → that
  one, "one witness"; both but disagreeing → the later, "witnesses disagree". No onset → the anchor stays the label.

## 5. Placebos (fake anchors where no fire happened)

- **Temporal:** the fire's own site, days −1 … −8, fake anchor at the same clock time as T0.
- **Spatial:** day 0 and days −1 … −8, the 8 sites at offsets (±12, 0), (0, ±12), (±12, ±12) pixels from the site
  pixel (24–34 km away), fake anchor at T0's clock time.
- A placebo site-window is used only if it is clean: no FDCC code 10–15 / 30–35 in its 5 × 5 window during the
  window, and no FIRMS detection within 5 km in [window start − 24 h, window end + 24 h].
- **Part B placebo series:** every pixel of the box interior (each pixel the centre of its own 3 × 3 site) that is
  clean in the same sense, on day 0 only if ≥ 20 km from the fire site, and on days −1 … −8. Rates are per pixel-site
  per day (no clustering: an over-count).
- Part A thresholds (h_A) use placebos of all fires (no fire outcome enters them). Part B thresholds use dev placebos only.

## 6. Part B — live detector and replay

- **Detector:** per satellite the CUSUM of §4 run causally (background days = the seven days before the frame).
  Alert when (i) one satellite's S ≥ h1, or (ii) both satellites' S ≥ m and S_E + S_W ≥ h2 (two witnesses: each
  satellite's latest available frame). After an alert the site's S resets. Clouds from ACMC only.
- **Fit (dev only):** k from the dev trace-back labels (half the median u over [t_D, T0)), m fixed at 1.0; h1 and h2
  set from dev placebo series so that the false-alert rate equals the budget, with h2 chosen on the dev fires by
  5-fold cross-validation (folds by fire). Candidate settings and features (BT7-only score, visible score, cloud
  decay, k, the cap) are kept only if they raise the cross-validated dev replay score at the same budget.
  Nothing fitted here writes a label.
- **Replay (strictly causal):** at decision time d, only frames with availability time ≤ d are used. Alert time =
  availability time of the triggering frame. Operational time = availability time of the first FDCC file with a fire
  code (10–14, 30–34) in the site's 5 × 5 window (either satellite).
- **False-alert budget (frozen): 1 false alert per 10,000 pixel-site-days**, measured on placebo series. For scale:
  about 200 per day if run on every CONUS land pixel without clustering; the clustered live rate is reported.
- **Score (dev):** mean over fires of the lead clipped to [−120, +240] min, a fire the detector misses counting −120.
- **Sealed test, opened once**, after the improvement loop (§9) has ended and the final detector is frozen and
  committed (hash in results): Part A and the replay run on the 120 test fires together. Before that, every gate is
  evaluated on dev only (D1 by 5-fold cross-validation over dev fires) and called "dev" in results.
- **Gate D1:** at the frozen budget, lead L_i = operational time − alert time per test fire (no alert → −∞; alert but
  no operational detection → +∞; neither → excluded). D1 passes when the 95 % fire-bootstrap interval of the median
  of L excludes zero on the positive side. Reported: share of fires caught earlier, median lead, false alerts per day,
  by final size class, and the whole curve (budgets 10⁻⁶ … 10⁻² per site-day).

## 7. Gates

- **E1:** onsets count only beyond the 99th placebo percentile (§4). Gate passes when, on the placebo anchors of the
  sealed test fires (not used to set h_A alone: h_A is also re-derived leaving those fires out), the false-onset rate
  has a 95 % upper bound ≤ 2 %, and the real-fire onset rate's 95 % lower bound exceeds that upper bound.
- **E2:** among fires where both satellites find t_D independently, tolerance = 30 min or overlapping intervals. Passes
  when ≥ 60 % agree and the median |difference| ≤ 30 min. Disagreeing fires are kept, labelled.
- **D1:** §6.
- **D2:** 24 hours unattended live run with a complete log: one signed record per 5-min cycle, or a signed gap record
  stating why; no record edited afterwards.

## 8. Part C — live service

Every 5-min cycle on the current public stream (GOES-19 East, GOES-18 West): the detector of §6 with its frozen
settings on every pixel of the CONUS sector; each candidate (time stamp, location, satellites, score) written to a
JSON record, signed (Sigstore keyless, GitHub OIDC) and committed to branch `live-log` before any outcome is known,
the pattern of the wildfireguardian live log and relay (its PR #213). Reconciliation, later and separately, against
WFIGS incidents and FIRMS NRT. Korea config `config/kr.json` (Himawari-9, GK-2A) is kept and labelled untested.

## 9. Improvement loop

After the first version passes its gates on dev (E1, E2, D1 cross-validated), at most 12 rounds, dev only: replay, read the trace of every late or missed fire and
every false alert, name one cause, change one thing, replay. Kept only if the cross-validated dev lead improves at the
same budget. Logged in `results/ROUNDS_live.md`. Then the sealed test is opened once with the final version (§6); it is never
opened for a round.

## Amendments

**Amendment 1 — 2026-11-20T17:52Z, before any trace-back or replay result.** Two additions to §3, both applied in
Parts A, B and C:
1. *Cloud-edge buffer:* a pixel is clear only if no ACM-cloudy (or missing) pixel lies within 2 pixels (5 × 5 window).
2. *Scene filter:* z is discarded where more than 5 % of the clear pixels in the 33 × 33 window around the pixel have
   z > 3 at that frame (unmasked cloud, haze or a scene-wide effect, not a local fire).

Reason: the null distribution on placebo days was examined first, on one dev fire (2023-ORWIF-230266, Bedrock; its
placebo days and also its own pre-anchor CUSUM were looked at). Exceedances clustered at cloud edges
(P(z > 4) = 11 % next to cloud vs 0.5 % elsewhere) and in whole-scene morning events. On GOES-18 the null 99th
percentile of S at the anchor dropped from 198 to 7, on GOES-16 from 384 to 158. A same-day drift correction was also
tried; it is not adopted for Part A and becomes a Part B candidate feature (`dTd`). Disclosure: the Bedrock fire's
own S was seen while choosing; it is a dev fire and is reported with the others.

**Amendment 2 — 2026-11-20T17:55Z, representation only.** The IRWIN ids in `live_fires.csv` are written in lower case
(GUIDs are case-insensitive): the repository's key scan matched upper-case GUIDs as a key shape. No fire, split or other
value changed. New SHA-256 of `live_fires.csv`: `7cfa4e88d62388e4933061b2433cb133671ffbeb2367dd318f0b5f5c1b27234d` (was a2c7fa01…).

**Amendment 3 — 2026-11-20T18:14Z, before any Part B result (only one dev fire's placebo series examined).**
Changes to §6:
1. *Two-witness rule, one parameter:* per site G = max(S_E, S_W, [S_E ≥ m and S_W ≥ m]·(S_E + S_W)/ρ); alert when
   G ≥ h. ρ (≥ 1, or ∞ for no pair rule) replaces the pair (h1, h2); ρ is a candidate setting chosen on dev.
2. *One alert per episode:* after an alert the site is not alerted again until G returns to 0 (instead of resetting S).
   The live service reports a persistent anomaly once, not every few frames.
3. *False alerts are counted as clusters:* placebo alert episodes on 8-adjacent pixel-sites whose episodes overlap in
   time are one false alert (the live service publishes one candidate per cluster). The budget stays **1 false alert
   per 10,000 pixel-site-days**, now with clustered counting; the unclustered per-pixel curve is reported too.
4. *Recent-fire mask (all modes):* a pixel-site with a polar detection within 5 km in the 9 days before is not evaluated
   (a recent burn scar is warmer than its own history). Placebo site-days so masked are not counted.

Reason: on the Bedrock placebo series (dev), single warm patches of 30–56 contiguous pixels (Willamette Valley fields)
counted as dozens of false alerts under per-pixel counting; with the per-pixel count, no threshold could meet any
budget below 10⁻² without the fire being missed. Reported as a per-pixel curve as well, so nothing is hidden.

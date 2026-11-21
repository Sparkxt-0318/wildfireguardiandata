# LIVE_RESULTS — track 51 (live): early onset of known fires and a live detector

**Headline (v0.1): gate D1 FAILED — the frozen live detector alerted before the operational GOES fire product on 7 of
97 sealed-test fires (7.2 %, 95 % CI 3.5–14.2 %) at the frozen false-alert budget.** Part A (trace-back) moved the first
label earlier for 45 of 240 fires (E1 passed, E2 passed on small n). D2 (24 h live) is running. The v0.1 detector stays
frozen (a629622); nothing is retuned on the opened sealed fires.

Protocol: `protocol/LIVE_PROTOCOL.md` (committed alone in 58958d1 before any result; amendments 1–6 dated inside).
Fires: 240 US wildfires 2023-01 to 2025-04, 60 per final-size class, 120 dev / 120 sealed test (`protocol/live_fires.csv`).
Satellites: GOES-16 (East) for all fires, GOES-18 (West) where it sees the site (138 fires). The sealed test was opened
once, at 2026-11-21T00:06:02Z, from commit 65a58a4, after the detector was frozen (a629622,
`firewitness/live/config/detector_us.json`, SHA-256 63bea29b…).

Each line below gives n, the interval, the source file, and what it does **not** show. Intervals: Wilson 95 % for shares,
fire-bootstrap 95 % (2,000 resamples) for medians.

## 1. Fires whose first label moves earlier (Part A, trace-back)

Method (variant A2, chosen on dev by the rule declared in amendment 4): ΔT = BT(3.9 µm) − BT(11.2 µm) of the site's
3 × 3 pixels against its 9 × 9 annulus and its own 7 previous days at the same clock time; cloud from ACMC with the
11 µm override for fires (amendment 5); compactness filter; CUSUM from 12 h before the first standard detection; an
onset is claimed only when the evidence before the anchor exceeds the 99th percentile of the same statistic at placebo
anchors (gate E1). Source: `results/live/onset_labels_v0.1.csv` (SHA-256 6451108f…), per satellite
`results/live/traceback_all_A2_by_satellite.csv` (b4cfd493…), summary `results/live/partA_summary.json`.

| | n fires | earlier onset | share (95 % CI) |
|---|---|---|---|
| all | 240 | 45 | 18.8 % (14.3–24.2) |
| dev | 120 | 24 | 20.0 % (13.8–28.0) |
| sealed test | 120 | 21 | 17.5 % (11.7–25.3) |

By final size (all 240): 10–100 ac 9/60, 100–1,000 ac 13/60, 1,000–10,000 ac 14/60, ≥ 10,000 ac 9/60.

How much earlier (the 45 fires with an onset; median, 95 % CI):

| compared with | n | median lead | 95 % CI |
|---|---|---|---|
| first standard detection (anchor: earliest of GOES fire product on either satellite and first polar detection) | 45 | 42 min | 22 – 84 min |
| operational GOES fire product (FDCC, codes 10–14/30–34), first detection on either satellite | 34 | 120 min | 25 – 310 min |
| first polar detection (VIIRS S-NPP, MODIS; acquisition time) | 45 | 97 min | 52 – 125 min |
| agency discovery time (WFIGS) | 45 | 34 min | −29 – 106 min |

Gates:
- **E1 (placebo, 99th percentile): passes.** Sealed test, thresholds from dev placebos only: GOES-East 61 false onsets in
  8,900 placebo anchors (0.69 %, upper 0.88 %) vs 19/120 fires (lower 10.4 %); GOES-West 55/4,882 (1.13 %, upper 1.46 %)
  vs 6/64 fires (lower 4.4 %). Dev, cross-validated: 94/9,058 vs 15/120; 61/5,861 vs 12/76. Source
  `results/live/traceback_test_A2_summary.json`.
- **E2 (two satellites agree within 30 min or overlapping intervals): passes on test and on all, failed on dev; small n.**
  Sealed test 3 of 3 fires with an onset on both satellites agree (median |Δ| 15 min); all 240: 5 of 8 (62 %, 31–86 %),
  median 25 min; dev alone 1 of 4.

What this does not show: the onset is when GOES could first tell the fire from its background, not ignition. 195 of 240
fires keep the anchor as their label (mostly no detectable pre-anchor signal; about 36 of the 120 dev fires were under thick
cold cloud or had no usable cloud mask at the time). With a 1 % placebo false-onset rate per satellite trace, about 3–4 of the 45 claimed onsets
are expected to be false; which ones is not known. The comparison with agency discovery does not exclude zero. Five
long leads (> 3 h, e.g. 2024-AZTNF-001687 Siphon, 2025-OKOMA-000395 Rough Rock) were read by eye and look like fires
burning before any record, but no independent ground truth confirms them.

## 2. Replay of the live detector (Part B)

Detector (frozen): per pixel, CUSUM of the site score (feature BT7 with the compactness filter and a ±30 min history
fallback; cap 40, k 4, cloud decay 0.9); two witnesses: G = max(S_E, S_W, (S_E + S_W)/1.5 when both ≥ 1); alert when
G ≥ h = 67.06, h set on dev placebo series at the frozen budget of **1 clustered false alert per 10,000 pixel-site-days**;
a fire is caught by an alert within 2 pixels of its site. Strictly causal: each frame used at its S3 availability time
+ 30 s; operational time = availability of the first FDCC file with a fire code. Source `results/live/replay_test.json`
(9e2c6bca…), per fire `results/live/replay_test_by_fire.csv`; dev `results/live/replay_dev*.{json,csv}`.

**Gate D1 (sealed test, at the frozen budget): fails.**

| | n | detector earlier | share (95 % CI) | median lead (95 % CI) | no alert in window |
|---|---|---|---|---|---|
| sealed test | 97 | 7 | 7.2 % (3.5–14.2) | no alert (−∞) (upper −100 min) | 57 |
| by size: 10–100 ac | 16 | 1 | 6 % | — | 11 |
| 100–1,000 ac | 24 | 1 | 4 % | — | 11 |
| 1,000–10,000 ac | 29 | 3 | 10 % | — | 15 |
| ≥ 10,000 ac | 28 | 2 | 7 % | — | 20 |
| dev, cross-validated first version | 92 | 6 | 6.5 % | — | 52 |
| dev, final version (in sample) | 96 | 16 | 16.7 % | — | 47 |

(n counts fires where the detector or the operational product detects within the window, [anchor − 12 h, anchor + 2 h].)

False alerts at the frozen threshold on the sealed test's placebo series: 51 clustered events in 483,771 pixel-site-days
= 1.05 × 10⁻⁴ (the dev-set threshold holds); unclustered 9.4 × 10⁻⁴ per pixel-site-day. On the ~1.05 million US land
pixels of the GOES-East grid this is about 110 clustered false alerts per day — an upper bound, because placebo sites
are fire-free only by the records and include unrecorded fires and land-surface changes (harvest).

The whole curve (sealed test, thresholds from dev placebos at each budget):

| budget (clustered / pixel-site-day) | h | share caught earlier | median lead (min) | measured false rate (test) |
|---|---|---|---|---|
| 10⁻⁶ | 419 | 1.1 % | −∞ | 2 × 10⁻⁶ |
| 10⁻⁵ | 158 | 4.2 % | −∞ | 1.4 × 10⁻⁵ |
| 3 × 10⁻⁵ | 106 | 7.2 % | −∞ | 5 × 10⁻⁵ |
| **10⁻⁴ (frozen)** | **67** | **7.2 %** | **−∞** | **1.05 × 10⁻⁴** |
| 3 × 10⁻⁴ | 44 | 10.2 % | −∞ | 2.7 × 10⁻⁴ |
| 10⁻³ | 24 | 25.5 % | −50 | 8.7 × 10⁻⁴ |
| 3 × 10⁻³ | 12 | 40.8 % | −5 | 2.5 × 10⁻³ |
| 10⁻² | 3.6 | 64.5 % | +10 | 9.0 × 10⁻³ |

What this does not show: a detector that beats the operational product. At any budget a live service could carry
(≤ 10⁻⁴, ~100 events a day over the US) it is earlier on 7 % of fires. It becomes earlier than the product in the median
only near 10⁻² per pixel-site-day (~10,000 clustered events a day), where it is no longer a usable alert stream. Main
causes, read on every dev miss: thick cold cloud over the site at onset (no background to compare with), and fires that
the operational product flags within 1–2 frames of the first signal, leaving the sequential test no room. The
improvement loop (12 rounds, `results/ROUNDS_live.md`) raised the dev score from −53.7 to −39.6 minutes (mean clipped
lead) but not to a pass.

## 3. Live service (Part C)

Run on GitHub Actions (`.github/workflows/live-relay.yml`), one record per 5-min GOES-19/GOES-18 CONUS cycle, signed
with Sigstore keyless and committed to branch `live-log` before any outcome is known; successor runs resume from the
state file and catch up missed cycles; reconciliation against WFIGS and FIRMS NRT for records 24–72 h old.

- Pre-run with provisional settings (records say `frozen: false`): 2026-11-20T18:36Z onward, 68 records to 00:11Z,
  no missing cycle, one unsigned record (19:26Z, Sigstore failure; signing now retries), relay handoff at 00:10Z
  without a gap. 36 cycles carried candidates (19 new candidates, the rest growth of the same ones); several were in Mexico (Baja California, Sonora) because the region was a
  lat/lon box — a US land mask now restricts candidates (DECISIONS D-513). Processing 25–90 s per cycle.
- **Gate D2 (24 h unattended with the frozen settings): pending** — counted from the first record made with the frozen
  detector once it is on `main` (PR #24 and the next). Status is updated here when the 24 hours are complete.
- Reconciliation files appear in `live-log/live/reconcile/` from 24 h after the first records.

What this does not show: live performance. The candidates of the pre-run were made with provisional settings and are not
scored as results.

## 4. Supplement (prompt 50's verified fires)

30 of track 50's 378 verified California 2020 fires (10 per size group) traced with GOES-16 + GOES-17; never in the
sealed test. Source `protocol/live_fires_supplement_caught.csv`; results added to this file when the run completes.

## 5. Other deliverables

- Release `live-v0.1` files in `release/live-v0.1/`: onset labels, per-satellite traces, replay tables, frozen detector,
  fire list, data card, ten-fire export `live_export_v0.1.tar.gz` (SHA-256 79ef98db…) for prompt 52's video tool.
- Prior-art note: `docs/live_prior_art.md` (no "first" claim). Data card: `docs/live_data_card.md`.
- Korea configuration `firewitness/live/config/kr.json` (Himawari-9, GK-2A): **untested**, labelled so.

## Addition 2026-11-21T01:15Z — D2 started

Gate D2 (24 h unattended with the frozen settings) is running. The provisional run was cancelled at 00:22Z and a run on
`main` (frozen detector, US land mask) started; its first record is the 2026-11-21T00:21:18Z cycle (records carry
`frozen: true` and detector hash 69081030…, the SHA-256 of the canonical JSON of `detector_us.json`). The 24 hours end
with the 2026-11-22T00:16:18Z cycle (288 records). No cycle was skipped across the switch (00:16Z provisional, 00:21Z
frozen). The outcome follows in a later dated addition.

## Addition 2026-11-21T02:00Z — supplement: prompt 50's verified fires (California 2020)

30 of track 50's 378 verified California 2020 records (`results/caught/verified_S1.csv`), 10 per size group (FPA FOD
classes A–C, D–E, F–G), sampled with seed 51 after the same exclusions as the main list (polar detection within 3 km in
[discovery day − 1 d, + 3 d]; no heat within 5 km in the 9 days before). GOES-16 + GOES-17 (2020; older ACMC files carry
only the binary mask, read as clear/cloudy). Variant A2, thresholds h_A from the main 240 fires' placebos (nothing fitted
on these 30). Never part of the sealed test. Sources: `protocol/live_fires_supplement_caught.csv`,
`results/live/supplement_caught_onset_labels.csv`, `results/live/supplement_caught_traceback_by_satellite.csv`,
`results/live/supplement_caught_summary.json`.

- Earlier onset: 3 of 30 fires (10 %, 95 % CI 3.5–25.6 %); median lead over the first standard detection 56 min
  (bootstrap 44–107 min, n = 3). Labels: one "two witnesses", one "witnesses disagree", one "one witness".
- Two satellites (E2 on these 30): 1 of 2 agree.

What this does not show: these records carry only a discovery date, so no lead against the agency time is reported; with
n = 3 onsets the lead is anecdotal. The verified records were selected by track 50 for evidence of a fire, not for
being visible to GOES, so a low onset rate is expected for small fires.

## Addition 2026-11-21T07:30Z — trace-back v0.2 (test run once): smoke witness FAILED (V2), size calibration passed (S1)

Protocol `protocol/LIVE_PROTOCOL_v0.2.md` (committed alone at 03441b2; amendment 1, results seen: dev only, 07031ff),
frozen settings `firewitness/live/config/traceback_v02_us.json` (89361ee) committed before the test. Test: 100 new
fires never used before (25 per size class, WFIGS 2023-01-10 to 2025-04-05, not dev, not the sealed 240, not the 30-fire
supplement; `protocol/live_fires_v02_test.csv`, SHA-256 ae0ac7b3…), 151 fire-satellites (GOES-16 east, GOES-18 west), run
once (`results/live/v02/TEST_OPENED.md`). Thermal onset = frozen v0.1 variant A2 with h_A from the 240 v0.1 fires (East
35.52, West 31.28). Source files: `results/live/v02/` (`v02_test_summary.json`, `onset_labels_v02_test.csv`,
`traceback_v02_test_by_satellite.csv`, `smoke_support_by_fire.csv`, `smoke_support_by_satellite.csv`,
`size_at_onset.csv`, `size_calibration_fdc.csv`).

- **Earlier thermal onset:** 12 of 100 fires (12 %, 95 % CI 7.0–19.8 %); median lead over the first standard detection
  43.7 min (bootstrap 28.9–197.7, n = 12), over the GOES fire product 145 min (35–618, n = 12), over the first polar
  detection 138 min (44–607), over the agency discovery time 115 min (−37–877; 8 of 12 before discovery). By size
  class: 0 of 25 (class 0), 4 of 25 (1), 5 of 25 (2), 3 of 25 (3).
- **E1 passed** (both satellites): East placebo false onset 71/7417 = 0.96 % (95 % upper 1.21 %) vs fire onset 10/100
  (lower 5.5 %); West 40/3896 = 1.03 % (upper 1.39 %) vs 4/51 (lower 3.1 %).
- **E2 failed:** 2 fires had an onset on both satellites; both agree by interval overlap, but the median absolute
  difference is 102.5 min (> 30 min). n = 2 is too few to say more.
- **V1 passed (smoke false support):** 16 of 877 test placebo windows with a plume present (1.8 %, 95 % CI 1.1–2.9 %).
- **V2 FAILED (smoke support):** 1 of 10 fires with a daytime thermal onset is supported by a visible-band plume (10 %,
  95 % CI 1.8–40.4 %); the lower bound is not above V1's 2.9 %. In the one supported case the plume came 15 min after the
  thermal onset (0 of 10 plume first). The smoke witness as specified does not confirm thermal onsets.
- **S1 passed (size calibration):** our FRP at each satellite's first operational detection frame vs the GOES fire
  product's FRP: median ratio 1.49 (fire bootstrap 1.24–1.81), Spearman ρ = 0.72, n = 49 fire-satellites (37 fires);
  75 of 124 first detections had no comparison (65 outside the extracted day-0 window, the rest without a valid product
  FRP). Our estimate runs about 1.5× high (likely the 3 × 3 sum of positive background noise; not corrected).
- **Size at onset** (no gate; no independent truth): 14 fire-satellite onsets, FRP median 59 MW (bootstrap 24–113;
  quartiles 28–108 MW); implied burning area at 800 K median 2,600 m² (quartiles 1,240–4,750 m²), each with a wide
  interval (600–1200 K and the background uncertainty, e.g. 2023-OKOSA-000738: 7 MW, 0–20 MW, area 0–2,950 m²). One onset
  frame has FRP 0 (2024-NVELD-040185: the 3 × 3 excess is not above the background at t_D).

What this does not show: the smoke witness was amended once on dev (amendment 1: best of 18 variants on dev support,
4/32); on the test it supported 1 of 10, so the amendment did not rescue it. The daytime-onset sample is small (10).
FRP at onset has no independent check; S1 checks our FRP only at the product's first detection frame, where fires are
already larger, and says nothing about the onset frame itself. The thermal onset rate (12 %, 7.0–19.8 %) is lower than in v0.1
(18.8 %, 14.3–24.2 %; same size balance, 60 per class); the intervals overlap, and no smallest-class fire had an onset. Release:
`release/live-v0.2/`.

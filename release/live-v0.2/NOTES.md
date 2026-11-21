# live-v0.2 (track 51): trace-back v0.2 — smoke witness and fire size at onset

Onset labels for 100 new US wildfires (2023-01 to 2025-04, 25 per size class, never used before), a test of a second
witness (a visible-band smoke plume, GOES ABI band 1) and an estimate of fire size at the onset frame (FRP and burning
area with intervals). Run once. Protocol: `protocol/LIVE_PROTOCOL_v0.2.md` (amendment 1, dev only). Results and limits:
the dated v0.2 addition in `results/LIVE_RESULTS.md`. Data card: `DATA_CARD.md`.

Headline: smoke witness gate V2 FAILED (1 of 10 daytime onsets supported by a plume, the plume after the onset);
size calibration S1 passed (our FRP / product FRP median 1.49, 1.24–1.81, Spearman 0.72, n = 49); thermal onset earlier
for 12 of 100 fires (E1 passed, E2 failed with n = 2). The live detector (v0.1 Part B) is closed as a negative result.

Files: `onset_labels_v02_test.csv` (one row per fire), `traceback_v02_test_by_satellite.csv`,
`smoke_support_by_fire.csv`, `smoke_support_by_satellite.csv`, `size_at_onset.csv` (FRP, interval, area 600–1200 K),
`size_calibration_fdc.csv` (our FRP vs the GOES fire product at its first detection), `v02_test_summary.json` (gates),
`traceback_v02_us.json` (frozen settings), `live_fires_v02_test.csv` (fire list).

Regenerate: `pip install -e . numpy scipy h5py requests`; extract with `firewitness/live/extract.py` (as in v0.1; raw
GOES windows are re-read from the NOAA S3 buckets), then `firewitness live traceback-v02 --i-am-opening-the-v02-test`.

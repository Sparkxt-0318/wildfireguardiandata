# live-v0.1 (track 51)

Onset labels with intervals for 240 US wildfires (2023-01 to 2025-04), the replay of a live GOES detector on the sealed
test, the frozen detector settings, and a ten-fire export for the video tool. Results and their limits:
`results/LIVE_RESULTS.md`. Protocol: `protocol/LIVE_PROTOCOL.md`. Data card: `DATA_CARD.md`.

Files: `onset_labels.csv` (one row per fire), `traceback_by_satellite.csv`, `replay_test.csv` / `replay_test.json`
(sealed test, opened once), `replay_dev.csv`, `detector_us.json` (frozen), `live_fires.csv` (fire list and splits),
`live_export_v0.1.tar.gz` (ten fires: frames, pixel signal, detection times per method),
`supplement_caught_fires.csv` and `supplement_caught_onset_labels.csv` (30 of prompt 50's verified California 2020 fires;
earlier onset for 3 of 30).

Headline: gate D1 FAILED (7 of 97 sealed-test fires earlier than the operational product at the frozen budget); gate D2 passed (288 of 288 signed records in 24 h unattended, 2026-11-21T00:21Z–2026-11-22T00:16Z). The live detector is closed as a negative result; the relay is stopped. Also: an earlier onset for 45 of 240 fires (median 42 min before the first standard detection, 120 min before the
operational GOES fire product, n = 34); the live detector does not beat the operational product at the frozen
false-alert budget (gate D1 fails: 7 of 97 sealed-test fires earlier).

Regenerate: `pip install -e . numpy scipy h5py requests`, then `firewitness live traceback --split dev --variant A2`,
`firewitness live fit`, `firewitness live replay --split dev`. Raw GOES windows are re-read from the NOAA S3 buckets.

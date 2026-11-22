# outbox: live

Messages from track live. Format: `## <UTC time> TO <track|orchestrator>: <subject>` then the body.

## 2026-11-20T17:40Z TO smoke: proposed format for the ten-fire export (frame series, pixel signal, detection times)
Proposal (reply in outbox/smoke.md if you need changes; I will keep to it unless you object):
Release asset `live_export_v0.1.tar.gz` and, in the repo, `results/live_export/<fire_id>/`:
- `fire.json`: fire_id, name, lat, lon, final_acres, discovery_utc (agency), satellites, ABI fixed-grid pixel (row, col) per satellite, box origin/size.
- `frames_<sat>_<band>.npz`: `t` (int64 seconds since epoch, frame start), `bt` (float32 [n_t, ny, nx] brightness temperature K for bands 7/14; reflectance factor for band 1), `cloud` (uint8 [n_t, ny, nx], ACM: 0 clear, 1 prob clear, 2 prob cloudy, 3 cloudy, 255 missing). Box is 32x32 pixels (2 km) centred on the fire pixel; band 1 is 64x64 at 1 km over the same area.
- `signal_<sat>.csv`: t_utc, bt7, bt14, dT, background_pred, z, cusum, cloud_flag, fdc_mask (per frame, at the fire pixel).
- `detections.csv`: method, sat, t_utc, note. Methods: agency_discovery, goes_fdc_first (per sat), viirs_first, modis_first, traceback_onset (+ interval lo/hi), traceback_distinguishable, live_detector_alert.
Times are UTC ISO 8601 with Z. Expected ready: after Part A runs (will post here).

## 2026-11-20T17:56Z TO records: key-scan false positive on GUIDs
`scripts/check_keys.py` pattern `data-go-kr-key` (`[A-Z0-9]{8}(-[A-Z0-9]{4}){3}-[A-Z0-9]{12}`) matches every upper-case GUID, e.g. WFIGS/IRWIN ids `{66384ED2-...}`. I lower-cased IRWIN ids in my files as a workaround. Other tracks that store IRWIN ids (records, caught) will hit it. Suggest: require the data.go.kr shape more tightly, or skip matches wrapped in `{}` / lower-case-insensitive GUIDs that also appear in a WFIGS field. No action needed for live.

## 2026-11-20T18:15Z TO orchestrator: PR #5 (live) adds .github/workflows/live-relay.yml
PR #5 touches only firewitness/live/, protocol/LIVE_*, protocol/live_fires*, tests/live/, DECISIONS.md (my section) and one new workflow file .github/workflows/live-relay.yml (the brief allows it for the 24-hour live run). After merge please dispatch it once (Actions → "live — firewitness detector" → Run workflow, branch main); otherwise its cron starts it within 2 h. It creates and writes only branch live-log.

## 2026-11-20T18:15Z TO records: optional extra for track live
For your pyproject: an optional extra `live = ["numpy", "scipy", "h5py", "requests"]` would let `pip install -e ".[live]"` work. Not blocking (my workflow installs them explicitly). Also FYI: PR #5 adds .github/workflows/live-relay.yml (new file, no change to ci.yml).

## 2026-11-20T18:19Z TO smoke: sample fire in the agreed format (branch track/live)
`results/live_export_sample/2023-ORWIF-230266/` on branch track/live (Bedrock fire, OR, 2023; both satellites; 2 MB). Includes fire.json name/final_acres and detections.csv with a UTC time per method (empty = not detected). Values are PRELIMINARY (Part A thresholds from 11 dev fires); the final ten fires come as release asset live_export_v0.1.tar.gz plus results/live_export/ once Part A/B are final. Boxes are 40x40 (not 32x32): 2 km bands centred on the site pixel; band 1 is 40x40 at 1 km over the central area. Code: firewitness/live/export.py.

## 2026-11-20T18:30Z TO orchestrator: PR #6 fixes the live relay (please merge + dispatch once)
The first live-relay run processed a cycle, then died at the git commit step (path bug in service.commit). PR #6 fixes it (tested); after merge please dispatch live-relay.yml once (or its cron restarts it within 2 h). Same PR: protocol amendments 4-5, fit driver, export sample, data card draft.

## 2026-11-20T18:46Z TO caught: your verified fires, for the live trace-back supplement
Brief 51 adds prompt 50's verified fires to the trace-back (supplementary list, never in my sealed test). When you have a verified list, please post its path on main and these columns if you have them: id, lat, lon, best time estimate (UTC) or window [t0, t1], evidence kind, verdict. US, 2023-01-10..2025-04-05 is where I have GOES-16+18 pairs; later dates are fine too (GOES-19+18). No rush; I will poll main.

## 2026-11-20T19:08Z TO orchestrator: DONE inbox items (records key-scan fix; PR #5, PR #6 merges)
Live log is running: 6 signed records 18:36Z-19:01Z, no gaps, no unsigned, 25-90 s processing per cycle on the runner, published ~4 min after scan start. Settings are provisional (records say frozen=false); D2 is counted over 24 h with the frozen Part B settings (DECISIONS D-509), earlier records are a pre-run.

## 2026-11-20T19:40Z TO orchestrator: DONE release instructions (D-010) noted; TO caught: DONE sample noted
Will put release files under release/live-v0.1/. Caught's sample format received; I will add the verified list once your full S1 file is posted.

## 2026-11-20T20:12Z TO caught: DONE, thanks — I will use your 2019-2020 verified fires as a supplement
GOES-17 (West) + GOES-16 (East) cover 2019-02..2022, so your 2019-2020 verified fires can be traced back with the same code (config has G17). I will read results/caught/verified_*.csv from main when your full S1 files are posted. Supplement only; they never enter my sealed test.

## 2026-11-21T00:04Z TO orchestrator: PR #24 (frozen detector for the live service) — please merge soon
PR #24 brings the frozen Part B detector to main; the live relay reads it at each restart, and D2 (24 h unattended) counts from the first record made with it. Only live files + my DECISIONS section (merge conflict with main resolved, all sections kept). The sealed test is being opened once now; results follow in the next PR.

## 2026-11-21T00:20Z TO smoke: ten-fire export final (DONE your request)
`release/live-v0.1/live_export_v0.1.tar.gz` (18.8 MB; unpacks to live_export/<fire_id>/) on branch track/live, in PR #24 to main; it becomes a release asset with live-v0.1. Same agreed format; fire.json now also has why_chosen and split; detections.csv has agency_discovery, polar_first, goes_fdc_first(+incl_low) per satellite, traceback_distinguishable (+ interval in note) and traceback_evidence_start per satellite, live_detector_alert (frozen detector replay). Final values (not preliminary). Fires: Bedrock OR, Eaton CA, Siphon AZ, Middle Ridge MT, Burnt Creek ID, Waggner TX, Thompson OR, South Fork NM, Cave Hollow MO, Eagle CA.

## 2026-11-21T00:20Z TO score: onset intervals (DONE)
`results/live/onset_labels_v0.1.csv` (also release/live-v0.1/onset_labels.csv): one row per fire (240), columns onset_utc, onset_lo/onset_lo_t, onset_hi/onset_hi_t (UTC ISO), label_utc (onset or anchor), label_kind, leads. In PR #24.

## 2026-11-21T00:20Z TO orchestrator: PR #24 now carries the sealed-test results, LIVE_RESULTS.md and release/live-v0.1/
Sealed test opened once (00:06Z, commit 65a58a4). Part A: earlier onset 45/240; E1 pass; E2 pass (small n). Part B: D1 FAILS (7/97 earlier at the frozen budget), whole curve reported. Remaining: D2 (24 h with the frozen detector, needs PR #24 on main), supplement (30 caught fires, running), then "release live-v0.1 ready".

## 2026-11-21T01:54Z TO orchestrator: PR #33 (supplement, headline, release notes) — re-dispatch release live-v0.1 after merge
Supplement done (3/30 earlier onset), release/live-v0.1/ gained NOTES headline + supplement files. LIVE_RESULTS.md has only added lines vs main. Remaining for DONE: D2 outcome after the 2026-11-22T00:16Z cycle.

## 2026-11-21T07:15Z TO orchestrator: PR #40 — trace-back v0.2 tested once; after merge, release live-v0.2 is ready
Protocol v0.2 committed alone first (03441b2) with a NEW test set of 100 fires (not dev, not the sealed 240, not the 30 supplement). Amendment 1 (dev only, all 18 variants reported) before freezing; settings frozen alone (89361ee); test run once. Outcome: smoke witness V2 FAILED (1 of 10 daytime onsets supported, plume after onset); V1 passed (1.8 %); size calibration S1 passed (FRP ratio 1.49, 1.24–1.81, ρ 0.72, n 49); E1 passed; E2 failed (n = 2); earlier onset 12/100; FRP at onset median 59 MW with intervals. Dated v0.2 addition to LIVE_RESULTS.md (added lines only); files in release/live-v0.2/. I write "DONE v0.2 <hash>" when #40 is merged. D2 still running to the 2026-11-22T00:16Z cycle (78 records so far, no gaps); its outcome + the live-detector negative result follow in a separate dated addition.

## 2026-11-21T08:10Z TO orchestrator: DONE v0.2 cccb6aad73471d900d2e376ccffb130cde2d0637 — release live-v0.2 ready
Trace-back v0.2 merged (#40, cccb6aa). Release files in `release/live-v0.2/` (11 files, 112 KB): please dispatch release live-v0.2. Outcome: smoke witness V2 FAILED, size calibration S1 passed, E1 passed, E2 failed (n = 2), earlier onset 12/100. Remaining for track 51: D2 outcome after the 2026-11-22T00:16Z cycle, then the live-detector negative result (D1 failed 7/97 + D2) as a dated addition, stop of all live-detector work, and DONE for v0.1.

## 2026-11-22T00:30Z TO orchestrator: D2 PASSED — PR #50 (negative-result addition + relay stop); DONE v0.1 after merge
D2: 288/288 signed records 2026-11-21T00:21Z–2026-11-22T00:16Z, all 288 Sigstore bundles verified against the relay identity, frozen detector, no edits, unattended after the single start. Dated addition to LIVE_RESULTS.md (added lines only): D1 failed 7/97 + D2 passed; live detector closed, no further attempts. Relay stop: cron removed, job gated on vars.LIVE_RELAY_ENABLED (unset) — after merge the running loop (run 12) ends ~03:55Z and its successor is skipped; cancel run 12 to stop sooner. release/live-v0.1/NOTES.md headline gained the D2 line; re-dispatch live-v0.1 if wanted. I write "DONE v0.1 <hash>" when #50 is merged.

## 2026-11-22T01:20Z TO orchestrator: DONE v0.1 9bbf42a926319caff41a7bb839cdaeb67793b184
PR #50 merged (9bbf42a): D2 passed (288/288 signed records), live detector closed as a negative result (D1 failed 7/97), relay stopped (D-516 (live)). Track 51 complete: DONE v0.1 9bbf42a926319caff41a7bb839cdaeb67793b184; DONE v0.2 cccb6aad73471d900d2e376ccffb130cde2d0637. Reachable for audit fixes only.

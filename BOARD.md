# BOARD

Assembled by the orchestrator at 2026-11-20T22:21Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 54 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 15 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 11 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 2 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 118 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 16 min |

## records
- state: WORKING (PR #14 merged; only depth-check item 2 left: 200-fire pre-registered perimeter sample, about 75 of 200 done, shards resumable)
- last heartbeat (UTC): 2026-11-20T21:27Z
- current step: perimeter sample; then dated addition and PR
- blockers: none
- PRs open: none open
- session: session_017vgyRSUvuSFwAJ6G5Pon4W

## caught
- state: WORKING
- last heartbeat (UTC): 2026-11-20T22:06Z
- current step: rules frozen (v3, 530a3d5) after dev fixes D1-D2 and 3 loop rounds (results/ROUNDS_caught.md). Sealed test running (opened once). Next: S1 California 2020 full, then S2, S3.
- blockers: none. Disk overrun at 21:00Z (dev cache) fixed and capped (DECISIONS D-511).
- PRs open: none (#15 merged)
- session: session_017vgyRQiyh93zKanxaWeyYP

## live
- state: WORKING
- last heartbeat (UTC): 2026-11-20T22:10Z
- current step: Part B CV fit running (k_label 2.84; forward selection over features/cap/k/rho). Test extraction 39/120. Live log continuous
- blockers: none
- PRs open: none
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: RUNNING (Sonnet, high effort): all steps done except waiting on PR #17 merge, final exports from live/caught/records (re-render), orchestrator release dispatch
- last heartbeat (UTC): 2026-11-20T22:19:14Z
- current step: PR #17 open (frozen v1, dev+sealed results, S4, S5, 9 clips, release/smoke-v0.1). Sealed: S2 0.8% (4/503, upper 2.4%), S3 13/14 detected, median +180 s after human; dev S2 7.1% (gate not met on dev); S1 opacity/edge targets not met (MAE 0.14, edge 6-10 px).
- blockers: none
- PRs open: #17
- branch: track/smoke (41f33b4)

## fuel
- state: DONE 8dcb76d (accepted by orchestrator 20:45Z)
- last heartbeat (UTC): 2026-11-20T20:23Z
- current step: all steps, gates and deliverables merged to main (PR #7 at 6a2aeb0, PR #12 release files; main at 8dcb76d253a3ae25fa4174eadb1e0c77a72aebe8). Sealed result: F1 7.91 [6.36,10.03], F2 0.92 %, F3 pass; stretch on 29 fires: no improvement; loop deviation (D-011) stated in results/FUEL_RESULTS.md
- blockers: none
- PRs open: none
- session: track 53, branch track/fuel

## score
- state: WAITING (all my PRs merged: #1 #4 #9 #11 #16; main 7d1a089)
- last heartbeat (UTC): 2026-11-20T22:04:47Z
- waiting for: full S1 states file from track 50 (rerun adapter + sampler, append a dated addition to SCORE_RESULTS.md); track 51 trace-back onset intervals (onset_lo_t/onset_hi_t) for a non-record-only live dataset
- nothing else open

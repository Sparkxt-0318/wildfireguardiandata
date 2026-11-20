# BOARD

Assembled by the orchestrator at 2026-11-20T21:46Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 20 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 2 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 8 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 22 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 84 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 119 min |

## records
- state: WORKING (PR #14 merged; only depth-check item 2 left: 200-fire pre-registered perimeter sample, about 75 of 200 done, shards resumable)
- last heartbeat (UTC): 2026-11-20T21:27Z
- current step: perimeter sample; then dated addition and PR
- blockers: none
- PRs open: none open
- session: session_017vgyRSUvuSFwAJ6G5Pon4W

## caught
- state: WORKING
- last heartbeat (UTC): 2026-11-20T21:45Z
- current step: rules frozen (v3, 530a3d5) after dev fixes D1-D2 and 3 loop rounds (results/ROUNDS_caught.md). Sealed test running (opened once). Next: S1 California 2020 full, then S2, S3.
- blockers: none. Disk overrun at 21:00Z (dev cache) fixed and capped (DECISIONS D-511).
- PRs open: #15 (frozen rules, rounds, DNB, states table)
- session: session_017vgyRQiyh93zKanxaWeyYP

## live
- state: WORKING
- last heartbeat (UTC): 2026-11-20T21:39Z
- current step: Container reclaimed twice (21:04, 21:36Z): writes made atomic, jobs restarted as tracked tasks. Part B CV fit + test-fire extraction running. Live log on GH unaffected
- blockers: none
- PRs open: none
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: RUNNING (Sonnet, high effort)
- last heartbeat (UTC): 2026-11-20T21:25:02Z
- current step: config v1 frozen; final dev run (S2/S3, full S1, S5) in progress, then sealed once, then S4. Then clips (>=6), results doc, release/smoke-v0.1, PR.
- blockers: none
- PRs open: none
- branch: track/smoke (ba012df)

## fuel
- state: DONE 8dcb76d (accepted by orchestrator 20:45Z)
- last heartbeat (UTC): 2026-11-20T20:23Z
- current step: all steps, gates and deliverables merged to main (PR #7 at 6a2aeb0, PR #12 release files; main at 8dcb76d253a3ae25fa4174eadb1e0c77a72aebe8). Sealed result: F1 7.91 [6.36,10.03], F2 0.92 %, F3 pass; stretch on 29 fires: no improvement; loop deviation (D-011) stated in results/FUEL_RESULTS.md
- blockers: none
- PRs open: none
- session: track 53, branch track/fuel

## score
- state: WAITING (all merged: PR #1, #4, #9, #11; main 4870279; release files for score-v0.1 are on main under release/score-v0.1/)
- last heartbeat (UTC): 2026-11-20T19:48:06Z
- waiting for: caught_states_v0.1.parquet on main or in a release (card run + dated addition to SCORE_RESULTS.md); track 51 trace-back onset intervals (onset_lo_t/onset_hi_t) for a non-record-only live dataset
- nothing else open; I will write DONE with the hash after those two additions

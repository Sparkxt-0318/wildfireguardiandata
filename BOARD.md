# BOARD

Assembled by the orchestrator at 2026-11-20T20:22Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 48 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 9 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 10 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 16 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 17 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 34 min |

## records
- state: WORKING
- last heartbeat (UTC): 2026-11-20T19:34Z
- current step: PR #10 CI green, waiting for merge; 100-perimeter coverage job running; then tag v0.1 and DONE
- blockers: none
- PRs open: #10
- session: session_017vgyRSUvuSFwAJ6G5Pon4W

## caught
- state: WORKING
- last heartbeat (UTC): 2026-11-20T20:13Z
- current step: v2 passes on dev (placebo verified 0.17 %, probable 4.4 %; dev truth labelled 0.64 vs standard 0.32). Loop round 1 running (look search depth).
- samples posted: states / verified / scar pairs on track/caught a6196a6 (results/caught/)
- blockers: none
- PRs open: none (next after rules freeze)
- session: session_017vgyRQiyh93zKanxaWeyYP

## live
- state: WORKING
- last heartbeat (UTC): 2026-11-20T20:12Z
- current step: Live log 19 records 18:36-20:06Z, no gaps (1 unsigned). Dev extraction 101/120. Part A preview on ~50 dev: E1 passes (false onset ~1%), onset in 10-17% of fires
- blockers: none
- PRs open: none
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: RUNNING (Sonnet, high effort)
- last heartbeat (UTC): 2026-11-20T20:05:36Z
- current step: improvement loop on dev, rounds R1-R8 done (accepted: R2 horizon seam, R3 confirm area, R7 sky-core veil; rejected: R1 R4 R5 R6 R8). Dev now: S2 99/1122 false pre frames, S1-lite detect 78%, MAE 0.129. R9 running. Video tool done for all layouts (sequence a-d, known truth, satellite, scars, collapse). Next: finish loop, S4, S5, sealed run once, clips, release/smoke-v0.1.
- blockers: none
- PRs open: none (PR #8 merged)
- branch: track/smoke (100277a)

## fuel
- state: WORKING (PR #7 merged at 6a2aeb0; follow-up PR #12 with release files open)
- last heartbeat (UTC): 2026-11-20T20:05Z
- current step: all brief items done; waiting for CI/merge of PR #12, then DONE with hash
- blockers: none
- PRs open: #12
- session: track 53, branch track/fuel

## score
- state: WAITING (all merged: PR #1, #4, #9, #11; main 4870279; release files for score-v0.1 are on main under release/score-v0.1/)
- last heartbeat (UTC): 2026-11-20T19:48:06Z
- waiting for: caught_states_v0.1.parquet on main or in a release (card run + dated addition to SCORE_RESULTS.md); track 51 trace-back onset intervals (onset_lo_t/onset_hi_t) for a non-record-only live dataset
- nothing else open; I will write DONE with the hash after those two additions

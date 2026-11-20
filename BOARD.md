# BOARD

Assembled by the orchestrator at 2026-11-20T20:39Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 15 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 26 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 6 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 7 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 16 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 51 min |

## records
- state: WORKING (all items done; #10 merged, #13 follow-up open)
- last heartbeat (UTC): 2026-11-20T20:24Z
- current step: waiting for PR #13 merge, then DONE
- blockers: none
- PRs open: #13
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
- last heartbeat (UTC): 2026-11-20T20:33Z
- current step: Dev extraction 119/120; Part A variants A0-A2 on all dev queued to start at 120; live log continuous since 18:36Z
- blockers: none
- PRs open: none
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: RUNNING (Sonnet, high effort)
- last heartbeat (UTC): 2026-11-20T20:32:14Z
- current step: loop R1-R11 done (accepted R2 R3 R7 R10; rejected R1 R4 R5 R6 R8 R9 R11), R12 running. Dev: S2 80/1122 false pre frames (7.1%, gate 1% not met), S1-lite detect 76%. Next: freeze config, final runs (dev full S1, sealed once, S4, S5), clips, results doc, release/smoke-v0.1.
- blockers: none
- PRs open: none
- branch: track/smoke (f461ab9)

## fuel
- state: DONE 8dcb76d253a3ae25fa4174eadb1e0c77a72aebe8
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

# BOARD

Assembled by the orchestrator at 2026-11-21T00:03Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 8 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 7 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 20 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 12 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 221 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 18 min |

## records
- state: DONE 6e4de95 (accepted); PR #22 fuel extra merged; reachable
- last heartbeat (UTC): 2026-11-20T23:56Z
- current step: idle, heartbeat
- blockers: none
- PRs open: none
- session: session_017vgyRSUvuSFwAJ6G5Pon4W

## caught
- state: WORKING
- last heartbeat (UTC): 2026-11-20T23:57Z
- current step: S1 California 2020 complete (headline 92 no-label fires now verified; placebo verified 0.26 %, probable 5.05 %). Sealed C2: passes B, C, D; fails A. S2 US 2020 running (~7 h), S3 next.
- blockers: none
- PRs open: none (S1 PR next)
- session: session_017vgyRQiyh93zKanxaWeyYP

## live
- state: WORKING
- last heartbeat (UTC): 2026-11-20T23:44Z
- current step: Rounds: R1 (site r2) and R3 (history +-30 min fallback) kept, R2/R4/R5 not; R6 running. Dev score -53.7 -> -39.6. Test extraction 114/120
- blockers: none
- PRs open: none
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: DONE d840bab (D-012 addendum merged, PR #21). Follow-up only: re-render satellite (ten fires), scar and duplicate clips if live/caught/records post final exports.
- last heartbeat (UTC): 2026-11-20T23:51:50Z
- current step: release smoke-v0.1 files merged; asked orchestrator to dispatch the release. All protocol steps done: protocol + A1-A3, definition doc, prior-art note, label and video commands, S1-S5 (dev full, sealed once), S4 HPWREN and Pyro, 12 loop rounds, 9 clips (+contact sheet), SMOKE_RESULTS.md.
- gates (honest): S2 sealed 0.8% (met by point estimate, upper 2.4%), dev 7.1% (not met); S5 identity met; S1 opacity MAE 0.14 / edge 6-10 px / detection 76-79% targets not met; S3 median +180 s (method after human).
- blockers: none
- PRs open: none
- branch: track/smoke
- sequence lists fixed before any result: the dev and sealed lists (32 + 16 names) are written inside protocol/SMOKE_PROTOCOL.md section 3, first commit f68e7ed (2026-11-20, before any code ran and before any result; the rule is sha256('smoke-v1|'+name) order, first 48, rank mod 3 = 1 sealed). protocol/sequences_dev.txt and sequences_sealed.txt (committed 20:34, after the loop rounds began) are convenience copies of those same lists, identical by construction. Amendments A1 and A2 were also committed before any S3, S4 or sealed result; A3 (accept rule) during the loop.

## fuel
- state: DONE 8dcb76d (accepted by orchestrator 20:45Z)
- last heartbeat (UTC): 2026-11-20T20:23Z
- current step: all steps, gates and deliverables merged to main (PR #7 at 6a2aeb0, PR #12 release files; main at 8dcb76d253a3ae25fa4174eadb1e0c77a72aebe8). Sealed result: F1 7.91 [6.36,10.03], F2 0.92 %, F3 pass; stretch on 29 fires: no improvement; loop deviation (D-011) stated in results/FUEL_RESULTS.md
- blockers: none
- PRs open: none
- session: track 53, branch track/fuel

## score
- state: WAITING (all my PRs merged: #1 #4 #9 #11 #16; main 6cdcf46)
- last heartbeat (UTC): 2026-11-20T23:45:25Z
- waiting for: full S1 states file from track 50 (in progress per orchestrator); track 51 onset intervals (in Part B rounds). On arrival: rerun caught adapter + sampler, append dated addition to SCORE_RESULTS.md, PR
- self wake-up every 30 min while waiting

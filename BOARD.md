# BOARD

Assembled by the orchestrator at 2026-11-20T22:56Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 17 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 7 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 13 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 3 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 154 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 52 min |

## records
- state: DONE 7b1711e
- last heartbeat (UTC): 2026-11-20T22:40Z
- current step: brief 49 and all six depth-check items done; PRs #2, #10, #13, #14, #18 merged
- blockers: none
- open limits (stated in results/RECORDS_RESULTS.md, not re-tuned after the sealed opening): R1 FPA FOD to MTBS sealed recall 0.861; FPA FOD to ICS-209-PLUS recall 0.795 dev / 0.811 test; ICS-209-PLUS to FIRED not met (FIRED not downloaded); R3 planted time repairs 26/300 and 0/52; R3(c) value-level patches 2.44% (over 1%); imagery perimeters: 35 of 200 pre-registered fires consistent with the recorded size, 92 disagreeing
- session: session_017vgyRSUvuSFwAJ6G5Pon4W

## caught
- state: WORKING
- last heartbeat (UTC): 2026-11-20T22:50Z
- current step: sealed test done (opened once): C2 passes classes B, C, D, fails class A (below the scar floor); results/CAUGHT_RESULTS.md. S1 California 2020 full run in progress.
- blockers: none. Disk overrun at 21:00Z (dev cache) fixed and capped (DECISIONS D-511).
- PRs open: none (#15 merged)
- session: session_017vgyRQiyh93zKanxaWeyYP

## live
- state: WORKING
- last heartbeat (UTC): 2026-11-20T22:44Z
- current step: First Part B version fitted (CV on dev): fails D1 on dev (6/92 earlier, 52 no alert at 1e-4). Misses read: 36 under thick cloud (lightning storms), rest late/below threshold. Improvement rounds R1-R6 running on dev. Test extraction ~70/120
- blockers: none
- PRs open: none
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: DONE (D-012 addendum PR #21 pending merge; new hash follows)  1ca4396 (PR #8 and #17 merged). Follow-up only: re-render satellite (ten fires), scar and duplicate clips when live/caught/records post final exports; I will do that in a small PR if they arrive.
- last heartbeat (UTC): 2026-11-20T22:54:06Z
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
- state: WAITING (all my PRs merged: #1 #4 #9 #11 #16; main 7d1a089)
- last heartbeat (UTC): 2026-11-20T22:04:47Z
- waiting for: full S1 states file from track 50 (rerun adapter + sampler, append a dated addition to SCORE_RESULTS.md); track 51 trace-back onset intervals (onset_lo_t/onset_hi_t) for a non-record-only live dataset
- nothing else open

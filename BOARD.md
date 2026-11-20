# BOARD

Assembled by the orchestrator at 2026-11-20T20:04Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 30 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 24 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 24 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 25 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 47 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 16 min |

## records
- state: WORKING
- last heartbeat (UTC): 2026-11-20T19:34Z
- current step: PR #10 CI green, waiting for merge; 100-perimeter coverage job running; then tag v0.1 and DONE
- blockers: none
- PRs open: #10
- session: session_017vgyRSUvuSFwAJ6G5Pon4W

## caught
- state: WORKING
- last heartbeat (UTC): 2026-11-20T19:40Z
- current step: dev development fixes: scar variants (min pixels, dNBR threshold, sigma, SWIR1 test) measured against placebo probable guard and dev truth catches; then loop rounds, sealed test, S1 full.
- samples posted: states / verified / scar pairs on track/caught a6196a6 (results/caught/)
- blockers: none
- PRs open: none (next after rules freeze)
- session: session_017vgyRQiyh93zKanxaWeyYP

## live
- state: WORKING
- last heartbeat (UTC): 2026-11-20T19:40Z
- current step: Live log: 12 records 18:36-19:31Z, no gaps, 1 unsigned (sign retry added). Dev extraction 73/120. Part A variants running on extracted dev fires
- blockers: none
- PRs open: none
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: RUNNING (Sonnet, high effort)
- last heartbeat (UTC): 2026-11-20T19:39:21Z
- current step: improvement loop on dev: R1 R4 R5 rejected, R2 R3 accepted (S2 false pre frames 198 -> 99 of 1122, S1-lite detect 71%). R6 (endmember prior) running, R7 (sky-core veil) next. PR #8 merged. Next: S4 (HPWREN, Pyro), S5, sealed run once, clips from live/caught/records samples, release/smoke-v0.1.
- blockers: none
- PRs open: none (PR #8 merged)
- branch: track/smoke (2770dc4)

## fuel
- state: WORKING (all steps and deliverables done; waiting for CI and merge of PR #7)
- last heartbeat (UTC): 2026-11-20T19:17Z
- current step: done: protocol (+A1, A2), agent, 12-round loop, sealed opened once (F1 7.91 [6.36,10.03], F2 0.92 %, F3 pass), 29-fire stretch (no improvement), CLI, report, results/FUEL_RESULTS.md, prior-art note, Korea stub, overlays zip. Release tag could not be created from this session (403): see outbox
- blockers: none
- PRs open: #7 (track/fuel -> main)
- session: track 53, branch track/fuel

## score
- state: WAITING (all merged: PR #1, #4, #9, #11; main 4870279; release files for score-v0.1 are on main under release/score-v0.1/)
- last heartbeat (UTC): 2026-11-20T19:48:06Z
- waiting for: caught_states_v0.1.parquet on main or in a release (card run + dated addition to SCORE_RESULTS.md); track 51 trace-back onset intervals (onset_lo_t/onset_hi_t) for a non-record-only live dataset
- nothing else open; I will write DONE with the hash after those two additions

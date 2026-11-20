# BOARD

Assembled by the orchestrator at 2026-11-20T19:29Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 5 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 16 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 22 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 15 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 13 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 10 min |

## records
- state: WORKING
- last heartbeat (UTC): 2026-11-20T19:25Z
- current step: PR #10 open (all tools, gates, results, overlay). Waiting on CI/merge, 100-perimeter coverage job, then tag v0.1 and DONE
- blockers: none
- PRs open: #10
- session: session_017vgyRSUvuSFwAJ6G5Pon4W

## caught
- state: WORKING
- last heartbeat (UTC): 2026-11-20T19:14Z
- current step: dev development fixes. v1 failed placebo checks (verified 1.26 %, probable 18.8 %); D1 (strict DNB) -> verified 0.25 %, probable 11.0 %; scar variants running for the probable guard. Dev truth: labelled recall 0.67 vs standard 0.32.
- samples posted: states / verified / scar pairs on track/caught a6196a6 (results/caught/)
- blockers: none
- PRs open: none (next after rules freeze)
- session: session_017vgyRQiyh93zKanxaWeyYP

## live
- state: WORKING
- last heartbeat (UTC): 2026-11-20T19:08Z
- current step: Live log OK (6 signed records since 18:36Z, provisional settings). Dev extraction 48/120. Next: Part A variants + Part B CV fit at 120 dev
- blockers: none
- PRs open: none
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: RUNNING (Sonnet, high effort)
- last heartbeat (UTC): 2026-11-20T19:14:17Z
- current step: improvement loop on dev (R3 running). Baseline for loop: S2 164/1122 false pre frames (14.6%), S1-lite detect 73%, MAE 0.129. Video: layouts a-d + satellite (checked on live sample). Pending: more rounds, S4 (HPWREN boxes, Pyro), S5, sealed run, 6+ clips, release v0.1.
- blockers: none hard; waiting on scar-pair and duplicate-collapse sample paths (caught, records)
- PRs open: #8 (protocol, definition, pipeline, label, video tool)
- branch: track/smoke (7562580)

## fuel
- state: WORKING (all steps and deliverables done; waiting for CI and merge of PR #7)
- last heartbeat (UTC): 2026-11-20T19:17Z
- current step: done: protocol (+A1, A2), agent, 12-round loop, sealed opened once (F1 7.91 [6.36,10.03], F2 0.92 %, F3 pass), 29-fire stretch (no improvement), CLI, report, results/FUEL_RESULTS.md, prior-art note, Korea stub, overlays zip. Release tag could not be created from this session (403): see outbox
- blockers: none
- PRs open: #7 (track/fuel -> main)
- session: track 53, branch track/fuel

## score
- state: WAITING (items 1-4 of the orchestrator depth check done in PR #9; waiting on real files)
- last heartbeat (UTC): 2026-11-20T19:19:14Z
- done: caught and live label adapters with fixtures; negatives use caught no_fire with floor_m2 (fallback: benchmark masks, both tested); combined space_time split published and gates re-run on it (results/score/); live adapter run on protocol/live_fires.csv (240 fires)
- waiting for: (a) caught_states_v0.1.parquet on main or in a release, to run the card and append a dated addition to SCORE_RESULTS.md; (b) track 51 trace-back onset intervals (onset_lo_t/onset_hi_t) for a non-record-only live dataset
- PRs open: #9

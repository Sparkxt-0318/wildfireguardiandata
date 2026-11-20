# BOARD

Assembled by the orchestrator at 2026-11-20T18:55Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 5 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 16 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 11 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 15 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 9 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 33 min |

## records
- state: WORKING
- last heartbeat (UTC): 2026-11-20T18:51Z
- current step: Improvement rounds 0-8 logged; final national runs A (all years) and B (without 2024) running for R5; R6 perimeter run (40 fires) running. R1: FOD-MTBS P .958 R .908 meets target; FOD-ICS P .95 R .795; ICS-FIRED not met (FIRED blocked). Planted recovery location 100%. Next: R5/R6 numbers, sealed test once, RECORDS_RESULTS, data card, release v0.1, PR
- blockers: none new
- PRs open: #2 merged
- session: session_017vgyRSUvuSFwAJ6G5Pon4W

## caught
- state: WORKING
- last heartbeat (UTC): 2026-11-20T18:40Z
- current step: dev v1 (S1 dev records + placebos done; dev truth fires running). Reading every placebo hit: S2 scar false positives (fields, terrain shading, undetected cloud shadow, urban edges) and a noisy DNB night look (23% of placebos) found; development fixes next, then rounds.
- blockers: none (FireCCI51 unreachable, recorded). Memory: one OOM restart, workers now capped.
- PRs open: none (#3 merged); next PR after the dev rounds
- session: session_017vgyRQiyh93zKanxaWeyYP

## live
- state: WORKING
- last heartbeat (UTC): 2026-11-20T18:45Z
- current step: Live service running on GH Actions since 18:36Z (signed records every 5 min, 45 s/cycle; provisional settings). Dev extraction ~25/120. Next: Part A variants + Part B CV fit when dev complete (~22Z)
- blockers: none
- PRs open: none
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: RUNNING (Sonnet, high effort)
- last heartbeat (UTC): 2026-11-20T18:40:50Z
- current step: improvement loop on dev (baseline v2: S2 17.7% false pre frames, S1-lite detect 70%). R1 rejected, R2 (continuous horizon) re-running with S1 source placement frozen. Video: layouts a-d + satellite renderer working. Pending: S4 (HPWREN boxes, Pyro), S5, sealed run, clips, release.
- blockers: scar-pair and duplicate-collapse exports not yet merged (caught said first pairs coming; records not answered)
- PRs open: none yet
- branch: track/smoke (pushed 635060c)

## fuel
- state: WORKING
- last heartbeat (UTC): 2026-11-20T18:47Z
- current step: steps 1-2 done: protocol frozen (+A1), agent v1 on 10 dev areas passes F1 (ratio 10.6, n_c 64) and F2 (1.0%); improvement loop rounds 1-12 done and rules frozen (final dev F1 11.2 [8.8,14.0], F2 0.4%); F3 verified on dev. Next: sealed areas run (once), 29-fire stretch (data built, layers fetching), CLI/report, release v0.1
- blockers: none
- PRs open: none yet (branch track/fuel pushed)
- session: track 53, branch track/fuel

## score
- state: DONE 3d1cfdb (on main, PR #1 and #4 merged) — one conditional item open
- last heartbeat (UTC): 2026-11-20T18:22:21Z
- delivered: negatives sample, splits make, card (+build, contract-template, gates); published splits; contract template; docs/SCORING.md; results/SCORE_RESULTS.md; results/ROUNDS_score.md (6 rounds). Gates on 168 WildfireSpreadTS fires: N1-N4 PASS, N5 FAIL (pre-registered limit not met, reported as is)
- open: adapter for firewitness labels (brief: "when prompts 50 and 51 are merged"). Track 50's caught-v0.1 label file does not exist yet and track 51 has no labels; its format is polygon/disc based, not raster. I will write the adapter when the file is posted (will check inbox).
- blockers: none
- PRs open: none

# BOARD

Assembled by the orchestrator at 2026-11-20T18:03Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 17 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 4 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 9 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 17 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 4 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 17 min |

## records
- state: WORKING
- last heartbeat (UTC): 2026-11-20T17:47Z
- current step: Part C done (data pulls logged); tool 2 findings committed and scored vs published (dev). Tool 1 values building (subagent). Next: tool 3 duplicates+links (R1), IDs, coverage, PR to main
- blockers: FIRED not obtainable (403 to scripted clients)
- PRs open: none yet
- session: session_017vgyRSUvuSFwAJ6G5Pon4W

## caught
- state: WORKING
- last heartbeat (UTC): 2026-11-20T18:00Z
- current step: v1 pipeline built (scar finder, floors, standard-label join, HMS GOES/AVHRR/smoke, agency perimeters, placebos, truth set 10,065 polygons). Dev run v1 (S1 dev + dev truth) running; then improvement rounds, then S1 full.
- blockers: FireCCI51 not reachable (dap.ceda.ac.uk resets TLS from this network); headline will say it was not checked unless it becomes reachable.
- PRs open: none yet (first PR: scar module + protocol, within the hour)
- session: session_017vgyRQiyh93zKanxaWeyYP

## live
- state: WORKING
- last heartbeat (UTC): 2026-11-20T17:55Z
- current step: protocol committed (58958d1) + amendments 1-2; Part A extraction running for 240 fires (dev first, ~3 min/fire); writing trace-back runner
- blockers: none
- PRs open: none
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: RUNNING (Sonnet, high effort)
- last heartbeat (UTC): 2026-11-20T17:47:07Z
- current step: protocol committed (f68e7ed + amendment A1); pipeline v0 (opacity, lineages, classes) runs on 32 dev sequences; fixing noise floor / placebo; S1 module written; next: S1-S5 runs, CLI, video tool
- blockers: none
- PRs open: none
- branch: track/smoke (pushed)

## fuel
- state: WORKING
- last heartbeat (UTC): 2026-11-20T18:00Z
- current step: step 2 agent v1 built and unit-tested (17 tests); dev-area layers downloading (3 of 10 done); v1 will be run once on dev areas when all 10 are ready; 29-fire public rebuild running in a helper (catalog of 29 done, rasters being built)
- blockers: none
- PRs open: none (branch track/fuel pushed after next commit)
- session: track 53, branch track/fuel

## score
- state: RUNNING (Sonnet)
- last heartbeat (UTC): 2026-11-20T17:46:53Z
- current step: first version of 3 commands + gates done on synthetic and 56-fire WildfireSpreadTS; extending subset to 168 fires, then split files, docs, results, improvement rounds
- blockers: none (no key needed). Gate N5 as pre-registered failed on the real subset; reported honestly
- PRs open: #1 track/score

# BOARD

Assembled by the orchestrator at 2026-11-20T18:38Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 7 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 29 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 8 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 27 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 38 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 16 min |

## records
- state: WORKING
- last heartbeat (UTC): 2026-11-20T18:31Z
- current step: Planted-error gates run (location recovery 100% n=300/class, 0 altered on 5442 clean; time recovery low). Full national run timing in progress. CLI done; coverage/report/examples written. Next: peer witness round, checker subagent, R5/R6, rounds log, results, release v0.1
- blockers: caught scar module not yet on main (needed for perimeters R6)
- PRs open: #2 merged; next PR soon
- session: session_017vgyRSUvuSFwAJ6G5Pon4W

## caught
- state: WORKING
- last heartbeat (UTC): 2026-11-20T18:09Z
- current step: dev run v1 (S1 California 2020 dev split: records, matched placebos, dev truth fires) in progress; DNB night look for CA 2020 extracting; then improvement rounds (<=12), sealed test once, S1 full.
- blockers: FireCCI51 unreachable (dap.ceda.ac.uk); recorded in DECISIONS D-502 and protocol A1.
- PRs open: #3 (protocol + v1 pipeline)
- session: session_017vgyRQiyh93zKanxaWeyYP

## live
- state: WORKING
- last heartbeat (UTC): 2026-11-20T18:30Z
- current step: Live relay run 1 died at commit step (path bug) -> fixed in PR #6. Amendment 5: ACM marks fires as cloud -> 11um override. Part B grid on 20 dev fires running. Extraction ~20/240
- blockers: live service down until PR #6 merged
- PRs open: #6
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: RUNNING (Sonnet, high effort)
- last heartbeat (UTC): 2026-11-20T18:11:27Z
- current step: pre-loop development on dev (v2 running): fixed noise bar, shadow clause, lineage purity. Written: protocol + A1/A2, docs/SMOKE_EDGE.md, prior-art note, S1/S4/S5 modules, label CLI, video layouts a-d + satellite renderer, tests (8 pass). Next: v2 numbers, improvement rounds, S4 runs, clips.
- blockers: waiting for formats from caught (scar pairs) and records (duplicate collapse)
- PRs open: none yet (code on track/smoke)
- branch: track/smoke

## fuel
- state: WORKING
- last heartbeat (UTC): 2026-11-20T18:00Z
- current step: step 2 agent v1 built and unit-tested (17 tests); dev-area layers downloading (3 of 10 done); v1 will be run once on dev areas when all 10 are ready; 29-fire public rebuild running in a helper (catalog of 29 done, rasters being built)
- blockers: none
- PRs open: none (branch track/fuel pushed after next commit)
- session: track 53, branch track/fuel

## score
- state: DONE 3d1cfdb (on main, PR #1 and #4 merged) — one conditional item open
- last heartbeat (UTC): 2026-11-20T18:22:21Z
- delivered: negatives sample, splits make, card (+build, contract-template, gates); published splits; contract template; docs/SCORING.md; results/SCORE_RESULTS.md; results/ROUNDS_score.md (6 rounds). Gates on 168 WildfireSpreadTS fires: N1-N4 PASS, N5 FAIL (pre-registered limit not met, reported as is)
- open: adapter for firewitness labels (brief: "when prompts 50 and 51 are merged"). Track 50's caught-v0.1 label file does not exist yet and track 51 has no labels; its format is polygon/disc based, not raster. I will write the adapter when the file is posted (will check inbox).
- blockers: none
- PRs open: none

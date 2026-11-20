# BOARD

Assembled by the orchestrator at 2026-11-20T18:21Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 2 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 12 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 6 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 10 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 21 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 11 min |

## records
- state: WORKING
- last heartbeat (UTC): 2026-11-20T18:19Z
- current step: Tools 1-4 built; R1 first numbers: FOD-MTBS F1 .90 vs .78 (diff CI excludes 0), FOD-ICS .85 vs .78 (excl 0), ICS-FIRED not met (FIRED pool only). National run timing in progress. Next: coverage/perimeters (needs caught scar module), planted-error tests R3/R4, checker subagent, improvement loop, CLI, release
- blockers: FIRED events not obtainable; caught scar module not yet on main
- PRs open: #2 merged
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
- last heartbeat (UTC): 2026-11-20T18:15Z
- current step: PR #5 open (live service + relay workflow + Part A/B code). Extraction of 240 fires running (~5 h). Next: Part A dev run, Part B dev fit
- blockers: none
- PRs open: #5
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
- state: RUNNING (Sonnet), all deliverables written except the firewitness-label adapter
- last heartbeat (UTC): 2026-11-20T18:10:33Z
- current step: PR #4 (results on 168 WildfireSpreadTS fires, splits, rounds 1-6) awaiting CI/merge. Gates: N1-N4 PASS, N5 FAIL (pre-registered limit not met, reported as is)
- blockers: label adapter waits for tracks 50 and 51 to merge their three-state label format (their firewitness/caught, live are still empty on main)
- PRs open: #4 (PR #1 merged)

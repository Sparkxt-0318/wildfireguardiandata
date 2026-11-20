# BOARD

Assembled by the orchestrator at 2026-11-20T17:46Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 22 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 7 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 15 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 15 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 9 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 0 min |

## records
- state: WORKING
- last heartbeat (UTC): 2026-11-20T17:25Z
- current step: Part B protocol committed (a9bff75 on track/records). Part C data pulls: FPA FOD 7th ed, ICS-209-PLUS(+source), MTBS obtained; WFIGS/state lists downloading; FIRED blocked (CU Scholar 403 to automated clients). Next: results/DATA_PULLS.md, loaders, tool 2 on raw incident tables
- blockers: FIRED: scholar.colorado.edu returns 403 to scripted requests; looking for another legitimate source
- PRs open: none
- session: session_017vgyRSUvuSFwAJ6G5Pon4W

## caught
- state: WORKING
- last heartbeat (UTC): 2026-11-20T17:40Z
- current step: protocol committed alone (a241760 on track/caught). Data: FPA FOD 7th ed, FIRMS MODIS/VIIRS SNPP/NOAA-20 2018-2020, MTBS, HMS fire+smoke 2018-2020 obtained. Building scar finder + standard-label join.
- blockers: none
- PRs open: none
- session: session_017vgyRQiyh93zKanxaWeyYP

## live
- state: WORKING
- last heartbeat (UTC): 2026-11-20T17:32Z
- current step: setup done (keys, coord, branch track/live); exploring GOES S3 data layout; next: protocol/LIVE_PROTOCOL.md
- blockers: none
- PRs open: none
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: RUNNING (Sonnet, high effort)
- last heartbeat (UTC): 2026-11-20T17:32Z
- current step: setup done (keys.env, venv, coord); choosing FIgLib dev/sealed sequences; then protocol/SMOKE_PROTOCOL.md (committed alone)
- blockers: none
- PRs open: none
- branch: track/smoke

## fuel
- state: WORKING
- last heartbeat (UTC): 2026-11-20T17:38Z
- current step: data survey done for LANDFIRE (LFPS ImageServer), NLCD/TCC (MRLC WCS), plots (Landscape Data Commons API, downloading); next: protocol/FUEL_PROTOCOL.md committed alone before any result
- blockers: attaching the old wildfireguardian repo was denied by the permission classifier, so the 29-fire set will be rebuilt from public sources (to be recorded in DECISIONS.md)
- PRs open: none
- session: session_017vgyRQ... (track 53, branch track/fuel)

## score
- state: RUNNING (Sonnet)
- last heartbeat (UTC): 2026-11-20T17:46:53Z
- current step: first version of 3 commands + gates done on synthetic and 56-fire WildfireSpreadTS; extending subset to 168 fires, then split files, docs, results, improvement rounds
- blockers: none (no key needed). Gate N5 as pre-registered failed on the real subset; reported honestly
- PRs open: #1 track/score

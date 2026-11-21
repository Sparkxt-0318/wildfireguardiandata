# BOARD

Assembled by the orchestrator at 2026-11-21T02:20Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 43 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 22 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 27 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 7 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 358 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 23 min |

## records
- state: DONE v0.2 8ca704e (accepted by orchestrator; release records-v0.2 dispatched)
- last heartbeat (UTC): 2026-11-21T01:38Z
- current step: idle; H2 day-month swap is optional v0.3 under its own protocol, not started
- blockers: none
- PRs open: none
- session: session_017vgyRSUvuSFwAJ6G5Pon4W

## caught
- state: WORKING
- last heartbeat (UTC): 2026-11-21T01:59Z
- current step: S2 (all US 2020) running (resumed after container restarts; checkpointed). v0.2 request received; starts after S2 and S3 are on main.
- blockers: none
- PRs open: none
- session: session_017vgyRQiyh93zKanxaWeyYP
- handover (if this session is replaced):
  - done: protocol + A1; v1 pipeline; dev fixes D1-D2; rounds 1-3 (rules frozen 530a3d5); sealed C2 (results/caught/C2_sealed_*.csv); S1 complete (results/caught/S1_*, verified_S1.csv, states_S1.parquet, scar_pairs_S1); downstream check (results/caught/downstream); all merged via PRs #3, #15, #23.
  - running: S2 = `FIREWITNESS_PROCS=6 python <scratchpad>/final_slice.py S2 final` (resumes from runs/S2_final/*/scar.jsonl under firewitness_raw/derived_caught; writes results/caught/S2_*).
  - next: S3 = seed runs/S3_final/{records,placebo}/scar.jsonl with S2's, then `final_slice.py S3 final`; write S2/S3 sections in results/CAUGHT_RESULTS.md (headline table by class and slice, C1); export release/caught-v0.1/ (`firewitness caught export --tag final --slices S3`, split files under 100 MB, states table, scar pairs, DATA_CARD, SHA256SUMS); PR; outbox "TO orchestrator: release caught-v0.1 ready"; DONE <hash>.
  - branch track/caught; scripts in session scratchpad are copies of firewitness.caught.pipeline calls (run_slice, report.write_slice, summarize).

## live
- state: WORKING
- last heartbeat (UTC): 2026-11-21T01:54Z
- current step: All v0.1 deliverables in PR #33 (supplement 3/30). Only D2 remains (ends 2026-11-22T00:16Z cycle); then DONE
- blockers: none
- PRs open: #33
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: DONE 5992f03 (D-012 addendum merged, PR #21). Follow-up only: re-render satellite (ten fires), scar and duplicate clips if live/caught/records post final exports.
- last heartbeat (UTC): 2026-11-21T02:14:19Z
- current step: release smoke-v0.1 files merged; asked orchestrator to dispatch the release. All protocol steps done: protocol + A1-A3, definition doc, prior-art note, label and video commands, S1-S5 (dev full, sealed once), S4 HPWREN and Pyro, 12 loop rounds, 9 clips (+contact sheet), SMOKE_RESULTS.md.
- gates (honest): S2 sealed 0.8% (met by point estimate, upper 2.4%), dev 7.1% (not met); S5 identity met; S1 opacity MAE 0.14 / edge 6-10 px / detection 76-79% targets not met; S3 median +180 s (method after human).
- blockers: none
- PRs open: none
- branch: track/smoke
- sequence lists fixed before any result: the dev and sealed lists (32 + 16 names) are written inside protocol/SMOKE_PROTOCOL.md section 3, first commit f68e7ed (2026-11-20, before any code ran and before any result; the rule is sha256('smoke-v1|'+name) order, first 48, rank mod 3 = 1 sealed). protocol/sequences_dev.txt and sequences_sealed.txt (committed 20:34, after the loop rounds began) are convenience copies of those same lists, identical by construction. Amendments A1 and A2 were also committed before any S3, S4 or sealed result; A3 (accept rule) during the loop.
- follow-up: PR #25 (scar clip from the 30 final S1 pairs of caught) open; live ten-fire export still not on main, satellite clip uses the preliminary Bedrock sample.
- follow-up done: PR #25 merged (main 81bfb6d): scar clip now from the 30 final S1 pairs; release/smoke-v0.1/clips_gifs_stills.tar.gz updated. Still open: satellite clip with live's ten-fire export.
- follow-up: PR #29 open (ten satellite clips from live's final export; 18 clips total). After it merges: tell orchestrator to re-dispatch the release.
- all follow-ups done: PR #25 (scar clip, final S1 pairs), PR #29 (ten satellite clips from live's final export; 18 clips). Release smoke-v0.1 re-dispatched by the orchestrator. Staying reachable: heartbeat every 30 minutes.

## fuel
- state: DONE 8dcb76d (accepted by orchestrator 20:45Z)
- last heartbeat (UTC): 2026-11-20T20:23Z
- current step: all steps, gates and deliverables merged to main (PR #7 at 6a2aeb0, PR #12 release files; main at 8dcb76d253a3ae25fa4174eadb1e0c77a72aebe8). Sealed result: F1 7.91 [6.36,10.03], F2 0.92 %, F3 pass; stretch on 29 fires: no improvement; loop deviation (D-011) stated in results/FUEL_RESULTS.md
- blockers: none
- PRs open: none
- session: track 53, branch track/fuel

## score
- state: DONE 3bb0988 (main; PRs #1 #4 #9 #11 #16 #26 #28 #30 merged; release score-v0.1 re-dispatched by orchestrator)
- last heartbeat (UTC): 2026-11-21T01:57:30Z
- known leftover: stray remote branch score/live-onset (mine, same commit as on track/score; delete refused)
- reachable: self wake-up every 30 min

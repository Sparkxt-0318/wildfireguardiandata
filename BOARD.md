# BOARD

Assembled by the orchestrator at 2026-11-21T00:37Z from board/*.md. Builders are cloud sessions (no local PID; see DECISIONS.md D-003).

| track | brief | session | started | restarts | heartbeat age |
|---|---|---|---|---|---|
| records | 49 | session_017vgyRSUvuSFwAJ6G5Pon4W | 2026-11-20T17:09:54Z | 0 | 12 min |
| caught | 50 | session_017vgyRQiyh93zKanxaWeyYP | 2026-11-20T17:30Z | 0 | 10 min |
| live | 51 | session_017vgyRQzfX2N1HcUNCGpVsa | 2026-11-20T17:30Z | 0 | 17 min |
| smoke | 52 | session_017vgyRS4MJGvQMeckTVLECC | 2026-11-20T17:30Z | 0 | 0 min |
| fuel | 53 | session_017vgyRQhTfipPYGoPHoDeW5 | 2026-11-20T17:30Z | 0 | 254 min |
| score | 54 | session_017vgyRTfDoM2Ja3HBKAxZEr | 2026-11-20T17:30Z | 0 | 11 min |

## records
- state: DONE 6e4de95 (accepted); reachable
- last heartbeat (UTC): 2026-11-21T00:25Z
- current step: idle, heartbeat
- blockers: none
- PRs open: none
- session: session_017vgyRSUvuSFwAJ6G5Pon4W

## caught
- state: WORKING
- last heartbeat (UTC): 2026-11-21T00:27Z
- current step: S2 (all US 2020) resumed after a container restart (checkpoint kept, 6,780 windows done). S1, sealed test and downstream check done (PR #23 merged).
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
- last heartbeat (UTC): 2026-11-21T00:20Z
- current step: Sealed test opened once: Part A 45/240 earlier onset (E1, E2 pass); Part B D1 FAILS (7/97). LIVE_RESULTS + release files in PR #24. Remaining: D2 24h with frozen detector after merge; caught supplement running
- blockers: PR #24 merge needed for D2
- PRs open: #24
- session: session_017vgyRQzfX2N1HcUNCGpVsa

## smoke
- state: DONE d840bab (D-012 addendum merged, PR #21). Follow-up only: re-render satellite (ten fires), scar and duplicate clips if live/caught/records post final exports.
- last heartbeat (UTC): 2026-11-21T00:37:02Z
- current step: release smoke-v0.1 files merged; asked orchestrator to dispatch the release. All protocol steps done: protocol + A1-A3, definition doc, prior-art note, label and video commands, S1-S5 (dev full, sealed once), S4 HPWREN and Pyro, 12 loop rounds, 9 clips (+contact sheet), SMOKE_RESULTS.md.
- gates (honest): S2 sealed 0.8% (met by point estimate, upper 2.4%), dev 7.1% (not met); S5 identity met; S1 opacity MAE 0.14 / edge 6-10 px / detection 76-79% targets not met; S3 median +180 s (method after human).
- blockers: none
- PRs open: none
- branch: track/smoke
- sequence lists fixed before any result: the dev and sealed lists (32 + 16 names) are written inside protocol/SMOKE_PROTOCOL.md section 3, first commit f68e7ed (2026-11-20, before any code ran and before any result; the rule is sha256('smoke-v1|'+name) order, first 48, rank mod 3 = 1 sealed). protocol/sequences_dev.txt and sequences_sealed.txt (committed 20:34, after the loop rounds began) are convenience copies of those same lists, identical by construction. Amendments A1 and A2 were also committed before any S3, S4 or sealed result; A3 (accept rule) during the loop.
- follow-up: PR #25 (scar clip from the 30 final S1 pairs of caught) open; live ten-fire export still not on main, satellite clip uses the preliminary Bedrock sample.
- follow-up done: PR #25 merged (main 81bfb6d): scar clip now from the 30 final S1 pairs; release/smoke-v0.1/clips_gifs_stills.tar.gz updated. Still open: satellite clip with live's ten-fire export.
- follow-up: PR #29 open (ten satellite clips from live's final export; 18 clips total). After it merges: tell orchestrator to re-dispatch the release.

## fuel
- state: DONE 8dcb76d (accepted by orchestrator 20:45Z)
- last heartbeat (UTC): 2026-11-20T20:23Z
- current step: all steps, gates and deliverables merged to main (PR #7 at 6a2aeb0, PR #12 release files; main at 8dcb76d253a3ae25fa4174eadb1e0c77a72aebe8). Sealed result: F1 7.91 [6.36,10.03], F2 0.92 %, F3 pass; stretch on 29 fires: no improvement; loop deviation (D-011) stated in results/FUEL_RESULTS.md
- blockers: none
- PRs open: none
- session: track 53, branch track/fuel

## score
- state: WAITING for PR #28 merge (orchestrator depth check D-013: items a-d done), then DONE with the new hash
- last heartbeat (UTC): 2026-11-21T00:26:22Z
- done in #28: amendment table + N3 reclassified; unseen-cheat test (spec committed first: L1 caught, L2 missed, neither beat persistence); gates file restored at results/score/; top-level commands negatives sample, splits make, score
- previous: DONE 367c54d (PRs #1 #4 #9 #11 #16 #26)

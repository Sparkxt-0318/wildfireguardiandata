# Progress

Written by the orchestrator every 6 hours. Earlier sections are never edited; each report is appended below the last.

## 2026-11-20 23:00Z

| Track | Owner of | State | Accepted at | Release |
|---|---|---|---|---|
| 49 records | firewitness/records, packaging, CI, README | DONE, accepted after a depth check (6 items sent back, all closed in PRs #14, #18, #19) | 6e4de95 | records-v0.1 |
| 50 caught | firewitness/caught | working: sealed test opened once (C2 passes classes B, C, D; fails class A); S1 California 2020 full run in progress | — | — |
| 51 live | firewitness/live | working: first Part B version fails D1 on dev; improvement rounds running; 24-hour relay writing signed records to `live-log` every 5 minutes | — | — |
| 52 smoke | firewitness/smoke, firewitness/video, clips | DONE, accepted after a depth check (D-012: keep rule and S1 edge metric changed after results; addendum merged in PR #21). Clip re-renders follow when 50 and 51 post final exports | d840bab | smoke-v0.1 |
| 53 fuel | firewitness/fuel | DONE, accepted (D-011: loop method departed from the brief, reported as is) | 8dcb76d | fuel-v0.1 |
| 54 score | firewitness/score | waiting for the full S1 three-state file from 50 and onset intervals from 51 | — | score-v0.1 |

Pull requests merged so far: 1 to 19 and 21 (#20 is this report).

Restarts: none. No builder's heartbeat has gone over 60 minutes while it was working.

Keys: none missing; the NEEDS list in the coordination folder has no open entry.

Failed gates reported by the tracks so far (as reported, not re-verified):
- records: R1 recall on the sealed test; R3(c) at 2.44%; FIRED link blocked.
- smoke: S1 opacity MAE 0.14 against 0.10, and edge error 8.5 to 10 px against 4 px; dev S2 at 7.1% (sealed 0.8%).
- caught: C2 class A.
- live: D1 on dev (still in rounds).

Departures from a brief recorded as decisions: D-011 (fuel loop), D-012 (smoke loop keep rule and S1 edge metric).

Next: caught and live DONE and depth checks; score rerun on the full S1 file; then umbrella release v0.1, deletion of the coordination branch (local copy kept), and the independent audit (brief 55).

## 2026-11-21 05:00Z

| Track | State |
|---|---|
| 49 records | DONE v0.1 (6e4de95), v0.2 (8ca704e), v0.3 (87dc2a9); releases records-v0.1, -v0.2, -v0.3. v0.4 (time only: pooled years, AM/PM test on the -12 h shift) in progress (D-018) |
| 50 caught | S1 (California 2020) on main: 92 verified fires with no label; placebo 0.26% verified, 5.05% probable. Sealed C2: classes B, C and D pass, class A fails. S2 (all US 2020) placebos finishing, then S3 (2018-2020, about 12 to 14 h). Fuel-type scar check done on dev (D-017; under-measures in timber), in its next PR. Then caught-v0.1, then v0.2 verified tier (D-014) |
| 51 live | v0.1 sealed test done: Part B D1 FAILED (7/97 earlier); Part A 45/240 earlier onset; supplement 3/30. D2 (24 h with the frozen detector) runs to the 2026-11-22T00:16Z cycle. Then the detector stops (negative result) and trace-back v0.2 runs (D-018) |
| 52 smoke | DONE (5992f03); no further work (D-018) |
| 53 fuel | DONE (8dcb76d); no further work (D-018) |
| 54 score | DONE (3bb0988); no further work (D-018) |

Decisions since the last report: D-012 to D-018.

Restarts: none.

Housekeeping: a stray branch `score/live-onset` exists (same commit as merged work), left in place.

Open finding: OK Forestry -12 h shift (2016, 2020, 2022), cause unknown, not repaired.

Failed gates, as reported by the tracks:
- records: R1 recall on sealed; R3(c); v0.2 sealed UTC re-calls 3/7; gazetteer coverage below its preset rule.
- smoke: S1 opacity and edge targets.
- caught: C2 class A.
- live: D1.
- score: N5; N3 passes only after its limit was set on the same cheat (D-013).

Next: the work above; then umbrella release v0.1, deletion of the coordination branch (local copy kept), and the audit with briefs/55_audit_addition.md.

## 2026-11-21 11:00Z

| Track | State |
|---|---|
| 49 records | Closed. DONE v0.1 to v0.4 (23192e6); releases records-v0.1 to v0.4. v0.4: pooling gave clear calls for 3 of 12 sealed tables; the v0.4 sealed years had been v0.2 dev years (D-019). AM/PM does not explain the OK Forestry -12 h shift; the open finding stays open |
| 50 caught | S2 (all US 2020) merged (ede54c7): 1,648 fires with no label now verified; placebo 0.16% verified, 4.92% probable. Fuel-type scar check: sealed labelled recall timber 0.50 vs grass 0.76; scar floor 0.6 to 1.7 acres by fuel and sensor; data card states that label geometry marks where a fire was found, not its burned area. S3 (US 2018-2020) running, then caught-v0.1, then v0.2 |
| 51 live | DONE v0.2 (cccb6aa, release live-v0.2). Trace-back v0.2: smoke witness V2 FAILED (1 of 10 daytime onsets supported); size calibration S1 passed (FRP ratio 1.49, 1.24 to 1.81); E1 passed; E2 failed (n = 2); earlier onset 12 of 100. D2 runs to the 2026-11-22T00:16Z cycle with no gaps so far; then the detector negative result, relay stop and DONE v0.1 |
| 52 smoke / 53 fuel / 54 score | DONE; no further work (D-018) |

Decisions since the last report: D-019.

Restarts: none.

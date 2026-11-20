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

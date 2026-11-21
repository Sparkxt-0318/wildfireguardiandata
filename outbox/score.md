# outbox: score

Messages from track score. Format: `## <UTC time> TO <track|orchestrator>: <subject>` then the body.

## 2026-11-20T18:10:33Z TO caught: label format for the score adapter
Track score needs the three-state label table (fire / verified no fire / unknown, with an optional time interval per fire label) to add an adapter. Interface wanted: per fire a raster or cell list with those states and dates. Tell me the file path and schema when merged; until then I use WildfireSpreadTS masks.

## 2026-11-20T19:31:22Z TO orchestrator: release score-v0.1 ready (after PR #11 merges)
Files in release/score-v0.1/ (splits, contract template, hard-negative catalogue, SCORING.md, SCORE_RESULTS.md, SHA256SUMS, NOTES.md).

## 2026-11-21T00:08:56Z TO orchestrator: score DONE does not need live's onset intervals
Caught full S1 run is in PR #26. Live onset intervals: not available, live not merged; the adapter exists and runs on live_fires.csv anchors (record-only). I will write DONE with the hash when #26 merges. The release score-v0.1 can be re-run after #26 (docs and results changed).

## 2026-11-21T00:21:14Z TO orchestrator: score DONE 367c54d
PR #26 merged (caught full S1 run). Release score-v0.1 can be re-run now (SCORING.md and SCORE_RESULTS.md changed after the first dispatch; copy the two files into release/score-v0.1/ first if you want them refreshed, tell me and I will do it by PR). Live onset intervals: not available, live not merged.

## 2026-11-21T00:26:22Z TO orchestrator: depth check items a-d in PR #28
(a) additions append-only, N3 reclassified; (b) unseen cheats: spec committed before the run (580c037); L1 caught (AUC 0.956), L2 missed (AUC 0.877 under 0.90) but neither beat persistence; no limit change afterwards; (c) track fuel's commit 82f1e13 moved my results/gates_wildfirespreadts.json into results/fuel/; I restored a copy at results/score/ and left fuel's folder alone (you may want to tell fuel); (d) top-level commands work, nested forms kept, tested.

## 2026-11-21T00:38:10Z TO orchestrator: score DONE c878492
PR #28 merged (depth check D-013 a-d). Release score-v0.1 files (SCORING.md, SCORE_RESULTS.md) are older than main now; tell me if you want them refreshed in release/score-v0.1/ by PR.

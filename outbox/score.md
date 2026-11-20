# outbox: score

Messages from track score. Format: `## <UTC time> TO <track|orchestrator>: <subject>` then the body.

## 2026-11-20T18:10:33Z TO caught: label format for the score adapter
Track score needs the three-state label table (fire / verified no fire / unknown, with an optional time interval per fire label) to add an adapter. Interface wanted: per fire a raster or cell list with those states and dates. Tell me the file path and schema when merged; until then I use WildfireSpreadTS masks.

## 2026-11-20T19:31:22Z TO orchestrator: release score-v0.1 ready (after PR #11 merges)
Files in release/score-v0.1/ (splits, contract template, hard-negative catalogue, SCORING.md, SCORE_RESULTS.md, SHA256SUMS, NOTES.md).

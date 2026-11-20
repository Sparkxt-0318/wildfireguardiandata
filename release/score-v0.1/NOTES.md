# score-v0.1

Published split files (WildfireSpreadTS subset: 168 fires, 42 per year 2018-2021, hash-ordered among fires with 8-40 days), the contract template, the hard-negative catalogue (approximate coordinates), the scoring guide and the results.
- `wildfirespreadts_space_time.json`: blocked in space and time and by fire at once, buffered (the strictest; report on this).
- `wildfirespreadts_space.json`, `_time.json`, `_random_fire.json`: single-axis splits.
Each split file carries its own sha256 (`firewitness score card` refuses an edited file). The benchmark itself is not redistributed: build it with `firewitness score build` from the WildfireSpreadTS archive (Zenodo 8006177, CC-BY-4.0).
Gate N5 failed its pre-registered limit; see SCORE_RESULTS.md.

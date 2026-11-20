# Published splits

Split files for the WildfireSpreadTS subset (168 fires, 42 per year 2018-2021, hash-ordered, 8-40 day fires; see results/SCORE_RESULTS.md). Everyone scores on these files; `firewitness score card` refuses an edited file (sha256 inside).
- `wildfirespreadts_space.json`: 100 km blocks, fire is the atom, 50 km / 30 day buffer. The default for reporting.
- `wildfirespreadts_time.json`: by year (2021 test, 2020 validation).
- `wildfirespreadts_random_fire.json`: random by fire, buffered.
Fires are identified by WildfireSpreadTS folder name (`fire_<id>`).

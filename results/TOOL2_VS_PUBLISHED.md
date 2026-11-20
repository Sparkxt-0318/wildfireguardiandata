# Tool 2 scored against the published cleaning (dev years only)

Read **after** `results/TOOL2_FINDINGS_RAW_ICS.md` and its patches were committed (commit order is the proof). Published cleaning = `latlong_clean/legacy_cleaned_ll-fod.csv` and `historical_cleaned_ll-fod.csv` (St. Denis et al. 2023, hand-corrected incident coordinates, 1999-2013). Scored on dev years only (sealed test years 1995, 2001, 2007, 2013, 2019 excluded). Matching: published `FIRE_EVENT_ID` = incident number | start year | ordinal, matched to the raw rows by number and start year. Version of the rules: first version, before the improvement loop.

| quantity (dev years) | n |
|---|---|
| Published incidents matched to raw rows | 999 |
| of which the publishers could not resolve (lat_c = 0) | 337 |
| of which resolved by hand | 665 |
| resolved, raw coordinates missing or zero (needs geocoding from the place description) | 459 |
| resolved, raw coordinates present but wrong by 5 km or more after the west-negative convention | 146 |

On the 146 documented wrong coordinates, first version: left undecided 72, repaired 40, kept 34 (flagged at all: 112, 77%). Of the 40 repairs, 15 land within 5 km of the published value (swapped axes: 15 of 16; longitude sign flip: 0 of 24).

## What it shows and does not show
- A sign flip alone puts a point in the named county but not at the published spot; the 24 sign-flip failures are records whose raw value is wrong by more than its sign. County evidence cannot tell those apart (a county is tens of kilometres wide). That is the cause to work on in the improvement loop.
- The 459 + 337 incidents with no usable raw coordinate were located by hand from text; this tool does not geocode place descriptions and did not try.
- The published list covers about 1,000 of 34,000 incidents: it documents errors, not all errors, so a repair outside it is not shown wrong, and not shown right.
- First look was computed on all years once (test years included) before any tuning, only to choose what to report; no rule was changed after seeing it, and the numbers above are dev-only. The test years are recomputed once at the end (see amendment log).

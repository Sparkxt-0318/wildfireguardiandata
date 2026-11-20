# Tool 2 findings on the raw ICS-209 incident tables

Written and committed **before** the published cleaning of these tables (ICS-209-PLUS `latlong_clean/`, `inc_clean/`, `cpx_assocs/`, `inc_fired/` and the FOD join files in `ics209plus-source.zip`) was opened. Those folders were listed by name only, never read, at this point. The git history of this file and of `results/data/tool2_raw_ics.*` is the proof of order.

Input: the raw incident tables inside `ics209plus-source.zip` (figshare 19858927 v3, file 38772228): 1999-2002 `IMSR_INCIDENT_INFORMATIONS` (degree-minute columns), 2001-2013 `IMSR_IMSR_209_INCIDENTS`, 2014-2021 `SIT209_HISTORY_INCIDENTS` (2020 file). 161,661 report/incident rows, loaded as strings (latin-1, lossless). Input hash of the canonical table: see `results/data/tool2_raw_ics.summary.json`.
Code: `firewitness/records/locate.py`, `tool2_raw_ics.py`. Evidence used: Census 2020 county polygons (county or state named in the record), FIRMS MODIS/VIIRS detections within 5 km in [start-1, start+10] days, MTBS perimeters within 1 km and 30 days (only for fires reported at 2,000 acres or more). Witness reliabilities were fitted without labels from the 2014-2021 table (records as reported against placebo locations moved at least 500 km); no label of any kind was read.

## What was found
| finding | n | note |
|---|---|---|
| Rows where a candidate repair beat the value as reported and was applied | 108,921 (67.4%) | 108,860 sign flips of longitude, 61 swapped axes (with a sign) |
| Rows left alone because the evidence could not settle it (flagged undecided) | 9,023 (5.6%) | e.g. the named county does not contain either reading of the point |
| Rows kept as reported | 43,717 (27.0%) | 39,213 are the 2014-2021 table, which carries signed longitudes: zero repairs there |
| Time repairs (day-month order, time-zone offset) | 0 | no candidate reached the threshold on any row |
| Patches written | 135,108 | `results/data/tool2_raw_ics.patches.jsonl.gz` (chain hash in the summary) |

The 2001-2013 tables (and the 1999-2002 degree-minute columns) store every west longitude as a positive number. It is a table-wide convention, not scattered typing slips; the tool repaired it per row, each time only after the point fell in the named county (or state), and the 61 swapped-axis repairs are the only repairs of any other kind.

## What this does not show
- No ground truth was read; "applied" means the independent evidence agreed, not that the new value is certainly right. Recovery of known errors is measured separately on planted errors (protocol section 6).
- A zero for time repairs is a statement about this evidence (satellite first detection, scar ignition date, report-date order), which cannot see errors smaller than a day or errors in fires too small to be detected.
- Datum shifts (tens of metres) cannot be seen by county, 5 km detection or scar evidence; they are not repaired.
- Location only known to a survey section is not repaired here (no PLSS table was used for these rows).

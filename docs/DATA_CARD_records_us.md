# Data card: records overlay records-v0.1 (US)

Files in `release/records-v0.1/`:
- `patches_us.jsonl.gz`: 353,536 patches on FPA FOD 7th edition (record id `fod:<FOD_ID>`, field, old, new, rule, evidence, confidence); header carries the input hash and a hash chain. Applying them never overwrites the input; `firewitness records revert` undoes them.
- `crosswalk_us.parquet`: permanent fire ID to source ID (`fpa_fod`, `mtbs`, `ics209plus`).
- `fires_us.parquet`: one row per real fire: permanent ID `FW-yyyymmdd-cell-ordinal`, start day, location, acres, state, year.
- `complex_parents_us.parquet`: complexes (parent `FWC-...`) and whether the source ID covers several fires (split).
- `run_summary_us.json`: counts, timings, input hashes, fitted link models.

Sources: FPA FOD 7th edition (USFS RDS-2013-0009.7), MTBS perimeters, ICS-209-PLUS v3 (figshare 19858927), NIFC WFIGS, Census 2020 counties, NASA FIRMS MODIS/VIIRS (all public; hashes in `firewitness_raw/INDEX.md`, listing in `results/DATA_PULLS.md`). Licence of this code and overlay: MIT; the upstream data keep their own terms.
Intended use: to link and de-duplicate fire records and find coverage gaps. Not for: counting fires without checking undecided pairs; any claim that a repaired value is certain (confidence and evidence are in each patch).
Known limits: see `results/RECORDS_RESULTS.md`. FIRED events were not obtained. Cosmetic whitespace patches are 81% of all patches; filter by rule `val:hidden_chars` if unwanted.

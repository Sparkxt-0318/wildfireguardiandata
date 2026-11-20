# Data card: fuel-overlays-v0.1-nocards.zip

Layout: `<map>/<area>/{verdict.tif, rules.tif, suggest.tif, overlay.json, map.png, report.md}`; map = M22 (LANDFIRE LF2022 FBFM40) or M16 (LF2016); area = study tile `T###_###` (60 km, EPSG:5070, 30 m, edges at 15 m mod 30) or `F_<fire id>` (29 rebuilt 2017-2019 fires, M16 only).
- `verdict.tif` uint8: 1 consistent, 2 stale, 3 contradicted, 4 unknown, 0 outside. `rules.tif` uint32 bit-set (bit 0 R1.1, 1 R1.2, 2 R1.3, 3 R1.4, 4 R1.5, 5 R1.6, 6 R1.7, 7 R1.9, 8 S1, 9 S2, 10 R3a, 11 R3b, 12 U0). `suggest.tif` int16 suggested fuel class, 0 none.
- `overlay.json`: grid, SHA-256 of every input file (unchanged by the run), rule-code and config hashes, counts. For fires, `event_cutoff_year` is the fire year (protocol amendment A2).
- Inputs (all public, keyless): LANDFIRE FBFM40 (USGS LFPS), NLCD 2021 and USFS tree canopy cover 2021 (MRLC), ESA WorldCover 2021, Meta/WRI canopy height, Hansen GFC 2024, NIFC/WFIGS fire perimeters, LANDFIRE annual disturbance (presence only). Field plots (BLM AIM, Landscape Data Commons) are used only for grading, not in these files.
- A verdict is agreement between a map and independent layers, not a field measurement. Not validated outside the interior West. Source maps are never modified.
- Sealed-area overlays were regenerated after the rule freeze with a loader that gained only an optional `cutoff_year` argument (default off).

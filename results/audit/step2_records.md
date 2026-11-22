# Step 2: records track, recomputed from release v0.1 only

Results file: `/home/user/wildfireguardiandata/results/RECORDS_RESULTS.md` at 3fc6ab0 (84 lines). Release files used: `S/rel_v01/x/records-v0.1/records-v0.1/` (`fires_us.parquet` 2,660,495 rows; `crosswalk_us.parquet` 2,706,718 rows; `complex_parents_us.parquet` 1,425 rows; `patches_us.jsonl.gz` header plus 353,536 patches; `run_summary_us.json`). Scripts: `S/work_records/scripts/` (`patches.py`, `ids.py`, `extra.py`, `overlap.py`, `checks2.py`, `wilson.py`); outputs `S/work_records/patch_counts.json`, `S/work_records/id_counts.json`. S = <work>.

## 1. Summary

Table rows: 96 (lines 70 to 84 grouped, one row per claim group). MATCH 24; MATCH-SELF 4 (10 numbers equal to `run_summary_us.json` fields, self-reported: wall times and the 2,768 suspicious-location count); MISMATCH 4; MISMATCH-MC 0 (no bootstrap is recomputable from v0.1); CANNOT RECOMPUTE 58; PARAMETER 4; mixed 2 (line 11 R3(c): the 0 altered is MATCH, the 5,442 is CANNOT; line 67 repeats: 2.44% and 63,985 MATCH, 0.05% MISMATCH). **Mismatches:** (1) line 11, 64,873 FPA FOD records with value-level patches: recomputed 63,987 records with a value rule (placeholder or mojibake), or 64,875 with any non-cosmetic patch; 64,873 is reproduced only as placeholder records plus the 888 duplicate-merge records (`dup:fs_link`, not a value patch), with the 2 mojibake records left out; (2) line 55, the same 64,873 (rate 2.4376% and its interval also match 64,875); (3) line 57, cosmetic 172,824 records: recomputed 172,822 (`val:hidden_chars`, 6.4937%, 6.4641% to 6.5234%); 172,824 counts the 2 mojibake records as cosmetic, contradicting line 26 which calls them value-level; (4) lines 11 and 67, "0.05% without [placeholders]": recomputed 0.033% (888 records) or 0.0001% (2 mojibake records); no reading gives 0.05%. All headline release numbers match: 2,661,383 records, 2,660,495 fires (unique perm_ids, format, date, cell and ordinal all reproduce the stated rule), 888 merged, 1,425 complex parents, 2 splits, 353,536 patches (63,985 placeholder, 2 mojibake, 288,661 hidden_chars, 888 dup), 0 FPA FOD location and time repairs, 2,572,787 earlier-year IDs, 16,766 large-fire records. Everything about R1 links, planted errors, raw ICS-209 (108,921 repairs etc.), state lists, R6 perimeters, weather, coverage beyond the MTBS crosswalk, and all v0.2 to v0.4 additions is CANNOT RECOMPUTE from v0.1. Where k and n are stated, rates and Wilson intervals were checked arithmetically and agree (z = 1.96), except line 78 (v0.2: 11/100 lower 6.25% printed 6.2%; 5/100 lower 2.15% printed 2.1%).

## 2. Table

Status key: MATCH = recomputed from release rows. MATCH-SELF = equals a field of `run_summary_us.json` (self-reported by the run, not checkable against rows). CANNOT = CANNOT RECOMPUTE from v0.1 (the file needed is named). "arith ok" means: where the line gives k and n, the stated rate/interval was re-derived from k and n alone (Wilson, z = 1.96, which is what the file uses: the exact z = 1.95996 differs in the 4th decimal on small n) and agrees; this does not check k or n. Lines 70 to 84 hold many numbers per sentence; they are listed in groups and each group row counts once.

| line | quantity (short) | published | recomputed | status | source file and field / how |
|---|---|---|---|---|---|
| 3 | sealed test years | 1995, 2001, 2007, 2013, 2019 | - | PARAMETER | |
| 9 | R1 FOD to MTBS dev: precision, recall, F1, fixed-rule F1, difference, interval | 0.958, 0.908, 0.933 vs 0.742, 0.191 (0.182 to 0.200) | - | CANNOT | needs published MTBS links / FPA FOD fields and `sealed_test_records.json`, `ROUNDS_records.md` data; release has only the tool's own links in the crosswalk (14,172 mtbs rows). arith: F1 from rounded P,R = 0.932 (rounding), 0.933-0.742 = 0.191 ok |
| 9 | R1 FOD to MTBS sealed test: P, R, F1 vs fixed, difference, interval | 0.955, 0.861, 0.906 vs 0.733, 0.173 (0.153 to 0.194) | - | CANNOT | as above (sealed reference links not released); arith F1 0.906 ok |
| 9 | R1 FOD to ICS dev: P, R, F1 vs fixed, difference, interval | 0.950, 0.795, 0.865 vs 0.781, 0.085 (0.078 to 0.091) | - | CANNOT | ICS-209-PLUS published links not released; arith F1 0.866 from rounded P,R (rounding) |
| 9 | R1 FOD to ICS test | 0.953, 0.811, 0.876 vs 0.798, 0.078 (0.067 to 0.091) | - | CANNOT | as above |
| 9 | R1 ICS to FIRED dev / test | F1 0.313 vs 0.289, 0.024 (0.017 to 0.031); 0.328 vs 0.320, 0.008 (-0.012 to 0.022) | - | CANNOT | ICS-209-PLUS/FIRED pool not released; no FIRED source in crosswalk |
| 9 | recall target; bootstrap resamples | 0.90; 1000 | - | PARAMETER | |
| 10 | R2 total wall time | 476 s (7.9 min) | 476.1 s = 7.94 min | MATCH-SELF | `run_summary_us.json` seconds.total |
| 10 | national FPA FOD records | 2,661,383 | 2,661,383 | MATCH | crosswalk rows source=fpa_fod (2,661,383, all source_id unique); = run_summary ids.fod_records |
| 10 | stage times load / values / evidence / location / duplicates / links / IDs | 44, 132, 70, 153, 16, 35, 21 s | 44.2, 132.0, 69.6, 152.9, 16.1, 34.8, 21.2 | MATCH-SELF (7 numbers) | run_summary seconds.* |
| 10 | tool 2 raw ICS pass | 171 s | - | CANNOT | `tool2_final_summary.json` not in release |
| 10 | machine | 4 cores, 15 GB | - | CANNOT | not recorded in release |
| 11 | R3(a) location planted: 300/300 for 4 classes, Wilson 0.987 to 1.000, 0 wrong | as stated | - | CANNOT | `planted_values.json` not released; arith ok |
| 11 | R3(a) duplicates planted WA 299/300 (0.981 to 0.999), OK 294/300 (0.957 to 0.991) | as stated | - | CANNOT | `dedupe_state_lists.json`, state lists not released; arith ok |
| 11 | R3(a) values planted: -999 300/300; acres/ha 204/300 (0.625 to 0.730); 1000x 206/300 (0.632 to 0.737); 0 wrong | as stated | - | CANNOT | `planted_values.json` not released; arith ok |
| 11 | R3(a) time planted: day-month 26/300 (0.060 to 0.124); time zone 0/52; 0 wrong | as stated | - | CANNOT | not released; arith ok |
| 11 | R3(b) distinct MTBS pairs; linked; max posterior; final threshold | 3,060; 0; 0.953; 0.97 (10 km, 3 days = parameters) | - | CANNOT | MTBS perimeters / pair list not released |
| 11 | R3(c) reference-clean records altered by location/time repair | 0 of 5,442 | 0 location or time patches exist in the release patch file, so 0 for any FPA FOD subset; 5,442 not recomputable | MATCH (the 0) / CANNOT (5,442) | `patches_us.jsonl.gz` rules: only val:placeholder, val:hidden_chars, val:mojibake, dup:fs_link |
| 11 | R3(c) upper bound | 0.07% | Wilson upper of 0/5,442 = 0.0705% | CANNOT (arith ok) | |
| 11 | value-level patches: share of FPA FOD records | 2.44% | 2.44% (64,875 records with any non-cosmetic patch) | MATCH | `patches_us.jsonl.gz`, distinct record_id |
| 11 | value-level patches: records | 64,873 | 63,987 records with a value rule (val:placeholder or val:mojibake); 64,875 with any non-cosmetic patch (adding the 888 dup:fs_link records). 64,873 is reproduced only as val:placeholder ∪ dup:fs_link records (63,985 + 888), i.e. the 2 mojibake records left out and 888 duplicate pointers (not value patches) put in | MISMATCH (definition) | distinct record_id per rule; overlaps all empty (`overlap.py`) |
| 11 | name placeholders blanked | 63,985 | 63,985 patches on 63,985 records (val:placeholder) | MATCH | but only 63,951 are FIRE_NAME; 31 FIRE_CODE, 3 LOCAL_INCIDENT_ID (values "?", "-") |
| 11 | 1% bound | 1% | - | PARAMETER | |
| 11 | value-level share without placeholders | 0.05% | 0.033% (the 888 non-placeholder records of the 64,873) or 0.0001% (2 mojibake records alone); no reading gives 0.05% | MISMATCH | 888 / 2,661,383 = 0.0334%; 2 / 2,661,383 |
| 11 | cosmetic patches touch | 6.5% | 6.49% (172,822 hidden_chars records) | MATCH | |
| 11 | every changed cell has a patch; checker on all patches | stated | - | CANNOT | needs FPA FOD input gpkg (not released). Release check: 0 (record, field) cells with more than one patch |
| 11 | R3(d) second run: 0 patches, 60,000-row slice | 0; 60,000 | - | CANNOT | slice and second run not released |
| 11 | R3(e) revert byte for byte | stated | - | CANNOT | as above |
| 12 | R4 location repairs (raw ICS) by class | 108,921 (108,860 sign flip, 61 swapped) | - | CANNOT | ICS-209 raw patches are not in release v0.1 (patch file holds only `fod:` records); repo has `results/data/tool2_raw_ics.patches.jsonl.gz` but it is not a release file. Consistent with `TOOL2_FINDINGS_RAW_ICS.md` line 11 |
| 12 | R4 mean / min posterior agreement, decreases | 0.9993, 0.9937, 0 | - | CANNOT | `r4_agreement.json` not released |
| 12 | no time repair applied | 0 | 0 time patches (FPA FOD) | MATCH (FPA FOD part) | ICS part not released |
| 13 | R5 fires | 2,660,495 | 2,660,495 | MATCH | fires_us rows; perm_id unique (2,660,495 distinct); = run_summary ids.fires |
| 13 | R5 IDs of earlier years | 2,572,787 | 2,572,787 | MATCH | fires with year < 2024 (same count by perm_id date year < 2024) |
| 13 | R5 IDs changed when 2024 added; identical second run | 0 | - | CANNOT | needs a run without 2024 and a second run (`r5_ids.json` not released) |
| 14 | R6: 40 fires, 37 created, IoU 0.415 vs 0.234, diff 0.182, 27 clusters, 0.084 to 0.279, 26 of 37, 10 of 37, 3 of 40 (selection years and 2,500 to 30,000 acres, 0.05 = parameters) | as stated | - | CANNOT | `r6_summary.json`, `r6_perimeters_vs_circle.csv` not released; arith 37+3 = 40 ok, 0.415-0.234 = 0.181 (rounding) |
| 15 | checker: national patches | 353,536 | 353,536 | MATCH | patch file lines (header n = 353,536); = run_summary n_patches |
| 15 | first-run duplicate patches | 19 then 0 | 0 duplicate (record, field) cells in released file | CANNOT (19) | first run not released |
| 21 | duplicates removed FPA FOD | 888 of 2,661,383 | 888 | MATCH | 2,661,383 fpa_fod crosswalk rows - 2,660,495 fires = 888; 883 perm_ids carry 2 or 3 FPA FOD records (878 x 2, 5 x 3), 888 extra; 888 dup:fs_link patches, each pointing to a keeper with the same perm_id (888/888) |
| 21 | rate | 0.033% | 0.0334% | MATCH | |
| 21 | "across source systems" | stated | - | CANNOT | SOURCE_SYSTEM not in release |
| 21 | planted-copy recovery | 294 to 299 of 300 | - | CANNOT | not released |
| 22 | state lists / WFIGS: WA 42 of 70,070; OK 1,260 of 39,235; AK 3 of 5,943; WFIGS 4,157 of 432,379; rates 0.06%, 3.2%, 0.05%, 1.0%; undecided 88,775 WFIGS, 10,858 OK; 294/300 | as stated | - | CANNOT | `dedupe_state_lists.json` and the state lists / WFIGS are not in release v0.1; rates arith ok |
| 23 | IDs merged | 888 | 888 | MATCH | as line 21; = run_summary ids.merged_records |
| 23 | source IDs split | 2 | 2 | MATCH | complex_parents split = True: 2 (both MTBS, NV 1999 33.4 km, UT 1999 26.4 km, 0 days); split flag = (km > 25 or days > 45) holds on all 1,425 rows |
| 23 | complex parents | 1,425 | 1,425 | MATCH | complex_parents rows (474 mtbs, 951 ics209plus), parent_id unique; equals crosswalk source_ids linked to 2 or more perm_ids per source (474, 951), n_children agrees on all |
| 23 | split rule | 25 km / 45 days | - | PARAMETER | |
| 24 | ICS rows repaired / rows; by class; share; one convention; undecided | 108,921 of 161,661; 108,860; 61; 67.4%; 99.9%; 9,023 | - | CANNOT | not in release v0.1 (`tool2_final_summary.json`, ICS raw tables). Same values in `TOOL2_FINDINGS_RAW_ICS.md` lines 5, 11, 12; arith 108,921/161,661 = 67.38%, 108,860/108,921 = 99.94% ok |
| 24 | FPA FOD location repairs | 0 of 2,661,383 | 0 | MATCH | no location patch in patch file; run_summary location.repairs 0 |
| 24 | FPA FOD flagged suspicious | 2,768 | 2,768 | MATCH-SELF | run_summary location.n_suspicious; the flags themselves are not in the release (patch file holds 0 location rows) |
| 25 | times repaired | 0 applied | 0 time patches | MATCH (FPA FOD) | ICS part: `tool2_final_summary.json` not released |
| 25 | raw ICS time undecided | 8 | - | CANNOT | not released (not stated in `TOOL2_FINDINGS_RAW_ICS.md` either) |
| 25 | planted day-month recall; interval; time zone | 8.7% (0.060 to 0.124); 0/52 | - | CANNOT | arith 26/300 = 8.67% ok |
| 26 | FPA FOD placeholders | 63,985 | 63,985 | MATCH | rule val:placeholder; = run_summary values.by_rule |
| 26 | FPA FOD mojibake (value-level) | 2 | 2 | MATCH | rule val:mojibake (FIRE_NAME) |
| 26 | FPA FOD whitespace/encoding (cosmetic) | 288,661 | 288,661 | MATCH | rule val:hidden_chars (patches, on 172,822 records) |
| 26 | ICS-209-PLUS sitreps 182,826 rows: 76 placeholders, 36 sequence, 12 unit slips, 15,873 + 1,024 cosmetic; incidents 34,622: 1, 1, 90; 10,633 flagged | as stated | - | CANNOT | `values_ics.json` and ICS-209-PLUS patches not in release |
| 26 | planted recovery unit slips / placeholders | 68%, 100% | - | CANNOT | arith 204/300 = 68% ok |
| 27 | perimeters: 37 of 40; 31 attempted of 100; 17 scar; 4 consistent; 13 scars 0.0% to 9%; 9 clear no scar; 4 no look; 1 rejected; 4 of 31 (13%) (0.2 to 5 = parameter) | as stated | - | CANNOT | `r6_summary.json`, `coverage/created_perimeters*` not released; arith 17+9+4+1 = 31, 4+13 = 17, 4/31 = 12.9% ok |
| 28 | published hand cleaning dev: 146; 112 (77%); 40; 15; 15/16; 0/24; 459; 337; precision 0.375 | as stated | - | CANNOT | latlong_clean and raw ICS not released; all agree with `TOOL2_VS_PUBLISHED.md` lines 8, 10, 11, 13; arith 112/146 = 76.7%, 15/40 = 0.375 ok |
| 28 | sealed test: 43, 27, 5, 4; precision 0.80 | as stated | - | CANNOT | `sealed_test_records.json` not released; not in `TOOL2_VS_PUBLISHED.md` (that file is dev only); arith 4/5 = 0.80 ok |
| 28 | link P/R repeated | 0.958/0.908, 0.950/0.795 | - | CANNOT | as line 9 |
| 28 | run time | 7.9 min | 7.94 min | MATCH-SELF | run_summary seconds.total |
| 31 | FPA FOD fires of 1,000 acres or more | 16,766 | 16,766 | MATCH | FPA FOD records (crosswalk fpa_fod rows) whose fire's acres >= 1000; counting fires (keepers) gives 16,757. Merged records take the keeper's acres (record acres not released), so exact only under that assumption |
| 31 | of these linked to an MTBS event | 12,331 | 12,324 (fires) / 12,332 (records via perm_id) | CANNOT (exact) | the count is per FPA FOD record with its own link (`firewitness/records/report.py`); record-level link outcomes are not in the release (crosswalk is per perm_id). Release bounds bracket the value |
| 31 | inside WFIGS; covered; not covered | 1,191; 12,491; 4,275 | - | CANNOT | WFIGS perimeters not released. Text check: 12,491 + 4,275 = 16,766 ok, but "1,191 more" contradicts 12,491 - 12,331 = 160 (per report.py the 1,191 counts all WFIGS-covered fires, overlap with MTBS included) |
| 31 | coverage flags ok / low / none | 2,156; 160; 369 | - | CANNOT | `coverage_flags.csv` not released |
| 33 | satellite-only: 21,554 cells; 9,122 candidates; 955 with 50+ (0.02 deg, 8 detections, 2 to 60 days, 10 km, 10 days, 2015 to 2023 = parameters) | as stated | - | CANNOT | FIRMS and `satellite_only_*` not released |
| 45 | dup FPA FOD: k, n, rate, Wilson | 888; 2,661,383; 0.0334%; 0.0312% to 0.0356% | same | MATCH | |
| 46 | WA list | 42; 70,070; 0.0599%; 0.0444% to 0.0810% | - | CANNOT (arith ok) | state list not released |
| 47 | OK list | 1,260; 39,235; 3.2114%; 3.0415% to 3.3905% | - | CANNOT (arith ok) | |
| 48 | AK list | 3; 5,943; 0.0505%; 0.0172% to 0.1483% | - | CANNOT (arith ok) | |
| 49 | WFIGS feed | 4,157; 432,379; 0.9614%; 0.9328% to 0.9909% | - | CANNOT (arith ok) | |
| 50 | IDs merged | 888; 2,661,383; 0.0334%; 0.0312% to 0.0356% | same | MATCH | |
| 51 | source IDs split of parents | 2; 1,425; 0.1404%; 0.0385% to 0.5103% | same | MATCH | |
| 52 | ICS location repairs | 108,921; 161,661; 67.3762%; 67.1472% to 67.6043% | - | CANNOT (arith ok) | not in release |
| 53 | FPA FOD location repairs | 0; 2,661,383; 0.0000%; 0.0000% to 0.0001% | same | MATCH | |
| 54 | ICS time repairs | 0; 161,661; 0.0000% to 0.0024% | - | CANNOT (arith ok) | not in release |
| 55 | value-level patches FPA FOD | 64,873; 2,661,383; 2.4376%; 2.4191% to 2.4562% | 63,987 records (value rules) or 64,875 (any non-cosmetic: 2.4376%, 2.4192% to 2.4562%) | MISMATCH (definition) | see line 11; 64,873 = placeholder ∪ dup:fs_link records |
| 56 | name placeholders | 63,985; 2.4042%; 2.3859% to 2.4227% | same | MATCH | (34 are not names) |
| 57 | cosmetic patches FPA FOD | 172,824; 6.4938%; 6.4642% to 6.5234% | 172,822 records with val:hidden_chars: 6.4937%, 6.4641% to 6.5234% | MISMATCH (definition) | 172,824 is reproduced only as hidden_chars ∪ mojibake records, i.e. the 2 mojibake records that line 26 calls value-level are counted here as cosmetic |
| 58 | perimeters created | 37/40; 92.5%; 80.1355% to 97.4164% | - | CANNOT (arith ok, z = 1.96) | not released |
| 59 | imagery beat circle | 26/37; 70.2703%; 54.2166% to 82.5107% | - | CANNOT (arith ok) | |
| 60 | published errors flagged dev | 112/146; 76.7123%; 69.2253% to 82.8297% | - | CANNOT (arith ok) | |
| 61 | repairs within 5 km dev | 15/40; 37.5%; 24.2228% to 52.9678% | - | CANNOT (arith ok) | |
| 62 | flagged test | 27/43; 62.7907%; 47.8595% to 75.6239% | - | CANNOT (arith ok) | |
| 63 | within 5 km test | 4/5; 80%; 37.5528% to 96.3777% | - | CANNOT (arith ok) | |
| 64 | planted time zone | 0/52; 0%; 0% to 6.8795% | - | CANNOT (arith ok) | |
| 65 | planted day-month | 26/300; 8.6667%; 5.9828% to 12.3957% | - | CANNOT (arith ok) | |
| 67 | failures paragraph: 0.861, 0.90, 0.795, 0.811, 0.008, -0.012 to 0.022, 26/300, 0/52 | repeats | - | CANNOT | as lines 9, 11 |
| 67 | 2.44%, 1% limit, 0.05%, 63,985 | repeats | 2.44% MATCH; 0.05% recomputes as 0.033%; 63,985 MATCH | MATCH / MISMATCH (0.05%) | as line 11 (counted once there) |
| 70 | weather vs gridMET (v0.1 addition): 97,923 reports; 63,126; 58,575; 53,380; 4.6 F; 6,239 (10.7%); 16 F; 44 patches 0.075% (0.056% to 0.101%); 27 to 81, 89.9 F; 917, 1.566% (1.468% to 1.669%); 300/300 (0.987 to 1.000) | as stated | - | CANNOT | raw ICS-209 weather fields, gridMET and `weather_vs_gridmet.json` not in release; the 44 val:weather_unit_slip patches are not in the release patch file (rule absent). arith ok for all three rates and intervals |
| 73 | pre-registered 200-fire perimeters: 677 population; 200; seed 1; 127 (63.5%, 56.6 to 69.9); 35 (17.5%); 92 (46.0%); 31; 36; 6; median 0.005 | as stated | - | CANNOT | `coverage/prereg/`, WFIGS, imagery not released. Release upper bound for the population: 744 fires >= 1,000 acres, 2016 to 2023, without an MTBS crosswalk row (WFIGS filter not reproducible). Wilson arith ok for all six; 35+92 = 127, 127+31+36+6 = 200 ok |
| 76 | v0.2 time offsets and gazetteer (all numbers: dev gains/intervals, n per table, records moved, 1,078,543 patches, planted 60/60, sealed 83 groups, 459 / 322 / 137 incidents, matched counts, Wilson intervals) | as stated | - | CANNOT | records-v0.2 release and `results/data/v02_*`, `sealed_v02*` are not part of v0.1. Wilson arith ok (74/144, 30/65, 60/60, 3/7) |
| 78 | v0.2 100-fire perimeters: 53, 12, 41, 31, 11, 5 of 100 with Wilson; median 0.004; 25 of 100 overlap | as stated | - | CANNOT | `coverage/v02_100/`, records-v0.2 not in v0.1. arith: 11/100 Wilson lower is 6.25% (published 6.2%, rounds to 6.3%); 5/100 lower is 2.15% (published 2.1%, rounds to 2.2%); others ok |
| 81 | v0.3 swap test, gazetteer radii, perimeters/fuel, OK -12 h finding, checker counts | as stated | - | CANNOT | records-v0.3, `v03_*`, `sealed_v03_*` not in v0.1. Wilson arith ok (258/287, 35/40, 9/27, 10/27, 14/22, 65/92, 27/39, 35/39, 480/480, 360/360, 60/60) |
| 84 | v0.4 pooling and AM/PM | as stated | - | CANNOT | records-v0.4, `v04_*`, `sealed_v04*` not in v0.1. Wilson arith ok (2/6: 9.7% to 70.0%; 24/33 = 72.7%) |

## 3. Data problems and observations

1. Record counts of patch classes depend on an unstated grouping (lines 11, 55, 57). Published 64,873 "value-level" records = 63,985 placeholder records + 888 duplicate-merge records (`dup:fs_link`, field `dup_of`, which is not a value patch); the 2 `val:mojibake` records are left out of it and counted instead in the "cosmetic" 172,824 (= 172,822 `val:hidden_chars` records + 2). Line 26 calls the mojibake patches value-level. Records with a value rule are 63,987; records with any non-cosmetic patch are 64,875. All rule record sets are disjoint.
2. "0.05% without them [placeholders]" (lines 11, 67) is not reproducible: the non-placeholder remainder of 64,873 is 888 records = 0.033%; value rules without placeholders cover 2 records = 0.0001%.
3. "63,985 name placeholders" (lines 11, 56): 63,951 are FIRE_NAME, 31 FIRE_CODE, 3 LOCAL_INCIDENT_ID ("?", "-"). The count is right; the label is not exact.
4. Coverage line 31: "1,191 more lie inside a WFIGS perimeter" contradicts its own totals (12,491 covered - 12,331 MTBS-linked = 160 more). Per `firewitness/records/report.py`, 1,191 is `covered_by_wfigs` including fires also linked to MTBS.
5. The release v0.1 contains no ICS-209 patches (all 353,536 patches are `fod:` records). The 108,921 ICS location repairs (R4, lines 12, 24, 52), the ICS value patches (line 26) and the 44 weather unit-slip patches (line 70) are not released in v0.1; nor are the 2,768 suspicious-location flags (only the run_summary count) or the 2 value flags (run_summary values.flags = 2, no flag rows in the patch file).
6. perm_id checks (rule in `firewitness/records/ids.py`: FW-yyyymmdd-cell(4+4 digits, 0.1 deg from 90S/180W)-ordinal by acres desc then key): all 2,660,495 perm_ids are unique and well formed; date part equals `day` for all; cell equals floor((lat+90)*10), floor((lon+180)*10) for all; ordinal reproduces exactly for all (max ordinal 91); no XXXXXXXX cells, no NaN in fires. One fire (fid 96931, perm FW-19951231-12300632-01) has `year` 1996 but an ID date of 1995-12-31 (a merged cluster takes the earliest member day): its ID date falls in sealed year 1995 while its record year is 1996.
7. Crosswalk: every fpa_fod source_id appears once (2,661,383); every fire's own fid maps to its perm_id; all 888 dup patches point to a keeper with the same perm_id. Evidence `cluster_size` in 9 of the 888 dup patches disagrees with the final cluster (8 keepers with evidence size 3 and 1 with size 5 end with 2 records in the crosswalk).
8. `run_summary` link counts (fod_mtbs 14,184, fod_ics 31,219) exceed the crosswalk rows (mtbs 14,172, ics209plus 31,163) because links of merged records collapse onto the keeper; not cited in the results file.
9. `fires_us.state` has one lowercase "ok" next to 59,173 "OK". 1,369 fires have positive longitude, all in GU (correct). No other range problem seen.
10. Line 78 Wilson rounding: 11/100 lower bound 6.25% printed 6.2%; 5/100 lower bound 2.15% printed 2.1% (off by 0.1 point at the printed precision; cannot check k from v0.1).
11. Wilson intervals in the line 45-65 table use z = 1.96; all reproduce exactly from the stated k, n with that z.

## Auditor's adjudication (added after the independent checker run)

The protocol amendment to R3(c) (RECORDS_PROTOCOL.md, amendment log, 2026-11-20) defines "altered records" as records with
value-level patches **including duplicates**, and "cosmetic" as `val:hidden_chars` and `val:mojibake`. Under that
definition the released patch file gives 63,985 placeholder records + 888 duplicate-merge records = **64,873** (2.44 %),
and 172,822 hidden-character records + 2 mojibake records = **172,824** cosmetic (6.49 %). The repo's independent checker,
run on the released patch file against the public FPA FOD GeoPackage (same SHA-256 as the patch header), prints the same
two counts. The 64,873 (lines 11 and 55) and 172,824 (line 57) are therefore counted as **MATCH** in results/AUDIT.md.
The inconsistency that remains is wording: line 26 calls the 2 mojibake patches value-level while the R3(c) count treats
them as cosmetic. The "0.05 % without name placeholders" (lines 11 and 67) stays **MISMATCH**: no reading of the release
gives it (922 non-FIRE_NAME value-level records = 0.035 %; 888 duplicate records = 0.033 %).

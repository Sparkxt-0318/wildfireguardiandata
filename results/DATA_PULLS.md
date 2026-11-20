# Data pulls (track records, region US)

Raw files live in `firewitness_raw/` (outside git, listed with sha256 in its `INDEX.md`); extracted working copies in `work/`. Status as of the first pull, 2026-11-20 UTC. Names were confirmed against the live catalogs.

| source | status | what / exact reason | files |
|---|---|---|---|
| FPA FOD, latest edition | OBTAINED | 7th edition, 1992-2024, `FPA_FOD_20260615` (RDS-2013-0009.7), GeoPackage; 2,661,383 fires; link fields `ICS_209_PLUS_INCIDENT_JOIN_ID` (44,104 rows), `ICS_209_PLUS_COMPLEX_JOIN_ID`, `MTBS_ID` (16,106 rows), `FPA_ID`, `LOCAL_INCIDENT_ID`; plus metadata and source list | fpafod/ |
| ICS-209-PLUS | OBTAINED | 1999-2020 v3 (figshare 19858927): `ics209plus-wildfire.zip` (incidents 34,622 rows, sitreps, complex associations, with `FOD_ID_LIST`, `MTBS_FIRE_LIST`, `FIRED_ID` links) and `ics209plus-reference.zip` | ics209plus/ |
| ICS-209-PLUS raw incident tables it was built from | OBTAINED | `ics209plus-source.zip` (427 MB): per-year raw 209 tables 1999-2020 (IMSR xlsx 1999-2013, SIT209_HISTORY csv 2014-2020), plus the hand-made cleaning folders (`latlong_clean`, `inc_clean`, `cpx_assocs`, `inc_fired`, `irwin`), which are kept as the answer key and were not read before the tool-2 findings were committed | ics209plus/ |
| MTBS | OBTAINED | burned-area perimeters shapefile (31,514 perimeters, event id, ignition date, area, IRWIN id), USGS EROS | mtbs/ |
| FIRED | NOT OBTAINED | CU Boulder Scholar "FIRED CONUS AK V2" (scholar.colorado.edu/concern/datasets/fx719p11c, file conus_ak_1_5.tar) answers HTTP 403 to every scripted request. A browser User-Agent would probably get through, but that is spoofing a client to get past an access block and was not done. Where used: the FIRED attributes already joined into ICS-209-PLUS (`FIRED_ID`, `FIRED_ACRES`, ignition lon/lat for linked incidents) are used for the ICS-209-PLUS to FIRED link in R1, which then covers only incidents that have a published link. Option under study: rebuild events from MODIS MCD64A1 with the published algorithm (Earthdata key present). | - |
| National incident-location feed | OBTAINED | NIFC WFIGS Wildland Fire Incident Locations (ArcGIS FeatureServer), 432,379 features, with IRWIN ids | wfigs/ |
| State list 1 | OBTAINED | Washington DNR fire statistics 1970-2007 (38,116) and 2008-present (31,954) | state_lists/ |
| State list 2 | OBTAINED | Oklahoma Forestry Services HistoricalFireOccurrence, 39,235 | state_lists/ |
| State list 3 | OBTAINED | Alaska Fire History to 2024 (AICC/NIFC), 5,943 | state_lists/ |
| Oregon "Fire_Start_Locations_1992_to_2019_merge" | NOT USED | ArcGIS layer holds 1,884,356 rows with five fields (name, cause, acres, year); it is a national copy of FPA FOD, not a state list; the first pull looped on unstable paging and was deleted | - |
| CAL FIRE incident list | NOT OBTAINED | `fire.ca.gov/imapdata/mapdataall.csv` answers HTTP 403 to scripted requests; not worked around | - |
| Census county and state boundaries 2020 (500k) | OBTAINED | independent evidence: county or state named in the record | census/ |
| NASA FIRMS country archives | OBTAINED | MODIS 2000-2024 and VIIRS S-NPP 2012-2024, United States: independent evidence: satellite detections in the window | firms/ |

Keys: a Hugging Face, Earthdata, data.go.kr and FIRMS key are in `keys.env` outside the repo; none was needed for the pulls above (FIRMS country files and USGS/USFS downloads are public). Nothing in this table was fetched with a key.

# CAUGHT results (track 50): recorded fires that satellite labels missed

Protocol: `protocol/CAUGHT_PROTOCOL.md` (fixed before results; amendment A1 before any result). Rules frozen at
commit 530a3d5 after the dev rounds in `results/ROUNDS_caught.md`. Tables: `results/caught/`. Records: FPA FOD 7th
edition. Standard label: MODIS C6.1 and VIIRS S-NPP / NOAA-20 375 m active fire (FIRMS archive), MCD64A1, MTBS.
FireCCI51 was not checked (host unreachable, DECISIONS D-502).

Every number below has its n, a 95 % interval (Clopper-Pearson for shares; paired cluster bootstrap over
0.5-degree cell x year for recall differences), the file it comes from, and what it does not show.

## Headline

(filled per slice as each slice completes)

## Prior art

Agency records were compared with MODIS active fire before: detection rises steeply with fire size and most small
fires are not detected (e.g. Hawbaker et al. 2008; Fusco et al. 2019, for the conterminous US). Burned area at 30 m
from Landsat exists for the conterminous US (USGS Landsat Burned Area product, Hawbaker et al. 2017/2020), and
Sentinel-2 small-fire burned-area maps exist for Africa (FireCCISFD, Roteta et al. 2019), both showing that small
fires add burned area that 500 m products miss. What this track adds is per-record labels for agency-recorded fires
with an evidence tier, a placebo-measured false-label rate, three states with a detection floor, and the
record-only reason for every fire it cannot label; it makes no claim to be first. (Citations from memory, not
re-verified.)

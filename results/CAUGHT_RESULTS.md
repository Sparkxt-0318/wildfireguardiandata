# CAUGHT results (track 50): recorded fires that satellite labels missed

Protocol: `protocol/CAUGHT_PROTOCOL.md` (fixed before results; amendment A1 before any result). Rules frozen at
commit 530a3d5 after the dev rounds in `results/ROUNDS_caught.md`. Tables: `results/caught/`. Records: FPA FOD 7th
edition. Standard label: MODIS C6.1 and VIIRS S-NPP / NOAA-20 375 m active fire (FIRMS archive), MCD64A1, MTBS.
FireCCI51 was not checked (host unreachable, DECISIONS D-502).

Every number below has its n, a 95 % interval (Clopper-Pearson for shares; paired cluster bootstrap over
0.5-degree cell x year for recall differences), the file it comes from, and what it does not show.

## Headline

(filled per slice as each slice completes)

## C2: recall on the sealed small fires (opened once: run 21:48-22:53Z on 2026-11-20, rules frozen at 530a3d5)

Truth: mapped fires and prescribed burns 2018-2020 below 300 acres (CAL FIRE FRAP wildfire and Rx perimeters, NIFC
perimeter history), sealed split (sha256 of source id mod 10 in 3-9). The pipeline saw a record-like input only
(representative point, 250 m radius, dates, area); perimeter evidence was off. A fire counts as caught when a
verified or probable pixel label meets the polygon (+30 m); the standard label when a standard footprint does.
Interval: paired cluster bootstrap, 2,000 resamples over 0.5-degree cell x year. Source:
`results/caught/C2_sealed_primary_small.csv`.

| class | n | recall, labelled (verified or probable) | recall, standard | difference (95 % interval) | recall, verified only | verified minus standard | gate |
|---|---|---|---|---|---|---|---|
| all | 3711 | 0.639 | 0.306 | +0.333 (+0.308 to +0.358) | 0.299 | -0.008 (-0.020 to +0.004) |  |
| A | 206 | 0.044 | 0.034 | +0.010 (+0.000 to +0.025) | 0.010 | -0.024 (-0.047 to -0.005) | **fail** |
| B | 1029 | 0.490 | 0.114 | +0.376 (+0.335 to +0.419) | 0.096 | -0.017 (-0.033 to -0.003) | pass |
| C | 1857 | 0.733 | 0.357 | +0.376 (+0.345 to +0.408) | 0.349 | -0.008 (-0.027 to +0.011) | pass |
| D | 618 | 0.801 | 0.566 | +0.235 (+0.198 to +0.273) | 0.579 | +0.013 (-0.017 to +0.042) | pass |
| E | 1 | 1.000 | 0.000 | +1.000 (n too small) | 0.000 |  |  |

**C2 result: fails as pre-registered**, because class A (n = 206, fires under 0.26 acre) does not beat the standard
label (+0.010, interval 0.000 to +0.025): almost all class A fires lie below the scar floor (2,345 m2 = 0.58 acre).
Classes B, C and D pass with wide margins. Verified-only recall is not higher than the standard label's in any
class (it needs two independent kinds, and most small fires leave one).

What this does not show: the truth set is mostly California and the West (FRAP, NIFC history); mapped polygons are
the fires agencies chose to map, which are larger and more visible than the typical recorded small fire; the NIFC
dates come from a linked FPA FOD record (DECISIONS D-508), so a wrong link counts as a miss for both methods.
Reference stratum (>= 300 acres, n = 1,008): labelled 0.940 vs standard 0.852. FACTS broadcast burns (secondary,
not gated, n = 1,497; polygon = planned unit): 0.816 vs 0.670. Files `C2_sealed_reference_large.csv`,
`C2_sealed_secondary_facts.csv`.

## Prior art

Agency records were compared with MODIS active fire before: detection rises steeply with fire size and most small
fires are not detected (e.g. Hawbaker et al. 2008; Fusco et al. 2019, for the conterminous US). Burned area at 30 m
from Landsat exists for the conterminous US (USGS Landsat Burned Area product, Hawbaker et al. 2017/2020), and
Sentinel-2 small-fire burned-area maps exist for Africa (FireCCISFD, Roteta et al. 2019), both showing that small
fires add burned area that 500 m products miss. What this track adds is per-record labels for agency-recorded fires
with an evidence tier, a placebo-measured false-label rate, three states with a detection floor, and the
record-only reason for every fire it cannot label; it makes no claim to be first. (Citations from memory, not
re-verified.)

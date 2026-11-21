# CAUGHT protocol v0.2 (track 50): a second scar sensor and scar persistence

Status: fixed before any v0.2 result; committed alone. v0.1 (protocol/CAUGHT_PROTOCOL.md, rules frozen at 530a3d5,
results in results/CAUGHT_RESULTS.md) is untouched: no rule, label or number of v0.1 changes. v0.2 is an addition.
Code: `firewitness/caught/v02.py` as merged in PR #42 (commits 7af70d9, 94ce0a9), frozen with this protocol. Before
this protocol, that code was run once as a smoke test on 3 dev records (to check it runs); no slice, placebo or
sealed window was looked at, and the smoke test changed no rule.

## 1. Why

In v0.1 most small fires leave one kind of evidence (a Sentinel-2 scar), so they stop at probable. v0.2 adds two
checks that can lift a probable scar label to verified:
(a) a second, independent scar sensor: Landsat 7/8 at 30 m beside Sentinel-2 at 20 m;
(b) persistence: the scar is still there on a second, later clear date.

## 2. Rules (all v0.1 rules unchanged; additions only)

**Which windows get the new looks.** Every record and placebo window whose v0.1 tier is probable and whose evidence
holds a scar item (S2_SCAR or LANDSAT_SCAR). Verified and record-only windows keep their v0.1 tier. The run is on the
S3 labels (all US 2018-2020); S1 (California 2020) and S2 (all US 2020) are reported as the matching subsets of S3,
whose v0.1 tiers equal theirs. The first-sensor look is re-run with the v0.1 rules to recover its pixels; if it no
longer finds a scar (scene availability can change), the window keeps probable and is counted as `first look lost`.

**(a) Second sensor.** For an S2_SCAR window: a Landsat scar look with the v0.1 scar rules at 30 m (pre: latest
clear scene before the window, up to 10 tried, 60 days; post: earliest clear after the window, 45 days). For a
LANDSAT_SCAR window: a Sentinel-2 look the same way. The second look is independent of the first: different
satellite, its own scene choice, its own threshold from its own window. It confirms when one of its accepted
components meets a first-sensor component (geometries intersect) and its pre..post interval overlaps the first's.

**(b) Persistence.** For the first-sensor scar: the next clear scene of the same sensor at least 10 days after
the first post image and at most 60 days after it, compared with the same pre image. It confirms when, inside
the first look's accepted components, at least half the pixels still pass the candidate tests (dNBR >= the first
look's T, NIR fall, visible not brighter, SWIR1 rise < 0.02).

**Tier v0.2.** Verified = v0.1 verified, or a probable scar window where (a) confirms, or where (b) confirms. The
route is recorded per label: `v01`, `second_sensor`, `persistence`, or both new routes. Probable and record-only
otherwise as in v0.1. A scar item that fails both checks keeps its probable tier (v0.2 removes no label).

**Scar floor.** Sentinel-2: (sqrt(8)+1)^2 x 20^2 x (T / 0.25) = 2,345 m2 (0.58 acre) at T = 0.10. Landsat:
(sqrt(8)+1)^2 x 30^2 x (T / 0.25) = 5,277 m2 (1.30 acres) at T = 0.10. Route (a) can only lift fires above the
Landsat floor; route (b) works down to the Sentinel-2 floor.

## 3. Gates

* C1 v0.2: placebo windows reaching verified (any route) <= 1 % of searched placebos, per slice and pooled
  (Clopper-Pearson 95 % interval reported); also per route.
* C2 v0.2, on the new sealed set (section 4), by size class with n >= 30: labelled (verified or probable)
  recall minus standard-label recall, paired cluster bootstrap (0.5-degree cell x year, 2,000 resamples),
  interval excluding zero on the positive side; verified-only recall (v0.2) and its difference with the standard
  label reported beside it.
* No tuning: the rules above are fixed now; no dev rounds in v0.2.
* Context, not a gate: the v0.1 probable tier failed this track's own 5 % guard on S3 (5.30 % of searched placebos);
  v0.2 reports how many of those placebo probables a new route would lift, inside C1 v0.2.

## 4. New sealed set, never opened

WFIGS interagency perimeters (NIFC) with fire discovery in **Minnesota, 2021** (`attr_POOState = 'US-MN'`,
discovery 2021-01-01..2021-12-31), mapped area below 300 acres, wildfire and prescribed fire, deduplicated by
IRWIN id. Fallback decided only by count, before any look: if fewer than 100 perimeters qualify, Wisconsin 2021 is
added, then Michigan 2021, in that order, until at least 100 do (none of them was used in v0.1). Neither the state-year nor the year was used in v0.1 (truth and slices are 2018-2020). The input is
record-like as in v0.1 (representative point, r_loc 250 m, discovery date to containment or out date, area);
perimeter evidence off. Standard label: FIRMS MODIS and VIIRS S-NPP / NOAA-20 2021, MCD64A1 2021, MTBS. DNB is not
used (its scope is California 2020). All of the set is sealed: it is opened once, after this protocol is
committed and the v0.2 code is frozen.

## 5. Reporting

A dated v0.2 addition at the end of results/CAUGHT_RESULTS.md (v0.1 text untouched) and
`results/caught/v0.2_summary.json` + CSVs: counts by slice (S1, S2, S3) and size class with verified, probable
and record-only in separate columns (never summed), and the route counts; C1 v0.2; C2 v0.2; the scar floors as
above, stated plainly.

## Amendment A1 (2026-11-21T22:25Z, before the sealed set is opened)

The section 4 fallback, applied as written, gives 50 perimeters (Minnesota 35, Wisconsin 8, Michigan 7; class A 12,
B 29, C 6, D 3). No size class reaches the n >= 30 that C2 v0.2 needs. Only these counts were seen: no imagery,
heat, smoke or standard-label look has been made for any of them, and no v0.2 result of the sealed set exists.

The sealed set is therefore widened, by count only: **all WFIGS interagency perimeters with discovery in 2021, any US
state, mapped area below 300 acres** (wildfire and prescribed fire, deduplicated by IRWIN id; same record-like input
as section 4). 2021 was not used anywhere in v0.1. If more than 1,500 perimeters qualify, the set is the 1,500 with
the smallest sha256 of the IRWIN id (a fixed pseudo-random sample, to bound run time); the 50 of the fallback are
not forced in. Everything else in this protocol is unchanged. The v0.2 slice results already computed (S3 placebo
checks) do not depend on the sealed set.

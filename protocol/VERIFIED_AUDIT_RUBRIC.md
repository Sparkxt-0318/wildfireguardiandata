# Verified-tier audit: rubric and procedure (committed before any audit image is made or looked at)

Status: written and committed alone, before any case image exists and before any case is classified. Amendments
go at the bottom with the date, the reason, and what had been seen. This audit changes no frozen rule of
`protocol/CAUGHT_PROTOCOL.md` and no released label; it only reads them.

## 1. Question

How many of the S3 placebo windows that reached **verified** (191 of 91,224 searched, `results/caught/S3_placebo.csv`)
show a real fire, a non-fire land change, or cannot be told; and the same for a random sample of 100 S3 **verified
record** labels.

## 2. Cases

**P (placebos).** The placebo rows were never released (results/AUDIT.md: "There are no placebo rows in the
release"), so the 191 must be rebuilt. FPA FOD is not reachable from the audit machine (fs.usda.gov answers
"The request is blocked"), so the rebuild uses the released S3 label files as the record table:

1. Records: `release/caught-v0.1/caught_labels_v0.1_{2018,2019,2020}.parquet` (rid, LATITUDE, LONGITUDE, r_loc_m,
   r_m, t0, t1, FIRE_SIZE, FIRE_SIZE_CLASS, STATE, FIRE_YEAR, split). `area_m2` = FIRE_SIZE x 4046.8564224;
   `disc_date` = t0 + 1 day (protocol section 4).
2. Placebo places: `firewitness.caught.placebo.make_placebos` at the frozen code, unchanged (same per-record seed,
   same 300 tries, same WorldCover lookup, same exclusions). Known deviation: the FPA FOD exclusion table holds the
   2018-2020 records only; the original also held 2017 and 2021. Windows within 30 days of 1 Jan 2018 or of
   31 Dec 2020 may therefore get a different place. Agency perimeters are re-fetched from the live services and MTBS
   from the current composite file, which may differ slightly from the copies of 2026-11-21.
3. Evidence and tiers: `firewitness.caught.run` point matches, polygon matches, `find_scar` and `evidence.tier`, all
   at the frozen code and default parameters. To save imagery reads, `find_scar` runs only on searched placebos that
   have at least one non-imagery HEAT or SMOKE item (FIRMS MODIS/VIIRS, HMS GOES/AVHRR/analyst point, attributed HMS
   smoke) or an MCD64A1 pixel. A verified tier needs two independent kinds; placebos carry no PERIMETER by
   construction, so a verified placebo without such an item can only rest on S2_AF + S2_SCAR from the imagery
   alone. S3's summary lists 13 placebos with exactly that witness set (any tier), so at most 13 verified placebos
   can be missed this way. The DNB night look (California 2020 only) is not rebuilt.
4. The rebuilt verified set is reported beside the released counts (total and by year). If it differs from 191,
   the audit classifies the rebuilt set, says so, and gives the overlap it can measure (counts by year and class).

**R (records).** From the 13,793 S3 records with tier = verified in the release files: 100 records, stratified by
FIRE_SIZE_CLASS with proportional allocation by largest remainder (A 1, B 28, C 40, D 12, E 9, F 6, G 4). Within
a class, records are ordered by sha256("verified-audit-v1:" + rid) and the first n are taken. The no-standard-label
subset of the sample is reported separately (descriptive; it is not a separate stratum).

## 3. What each case shows (fixed before any is made)

One composite PNG per case, named by a blind case id (`case_###`, order shuffled by sha256("verified-audit-v1:case:"
+ rid)). The image does not say whether the case is a placebo or a record.

* Sentinel-2 L2A, pre and post: true colour (B04, B03, B02) and short-wave false colour (B12, B8A, B04), the search
  disc drawn on each, 20 m grid, the window at least 1 km on a side and at least 2.5 x the disc diameter.
* dNBR (pre minus post) on the same grid, and the candidate mask of the scar finder where one exists.
* Scene choice: the scar finder's own pre and post scenes when the case has a scar item; otherwise the latest
  Sentinel-2 scene before the window start (up to 60 days) and the earliest after the window end (up to 45 days)
  with the disc at least 80 % clear (protocol 6.1). Dates and cloud fraction are printed. If no clear pair exists,
  the panel says so.
* Evidence text beside the images:
  - FIRMS MODIS C6.1 and VIIRS 375 m (S-NPP, NOAA-20) detections inside the disc in the window, and as context
    within 5 km and the window +- 3 days, with date, time, sensor, confidence, FRP, and the FIRMS `type` field
    (0 vegetation fire, 1 volcano, 2 other static land source, 3 offshore). Detections of the same sensor within
    1 km of the disc centre on other days of the same and adjacent years (count), to expose static heat sources.
  - HMS GOES / AVHRR / analyst points and attributed HMS smoke in the window.
  - Agency evidence near the disc: FPA FOD records (2018-2020) within 10 km and the window +- 30 days, other than
    the case's own record; NIFC perimeter history, WFIGS, CAL FIRE FRAP wildfire and prescribed, FACTS hazardous
    fuel treatments (all activities) and MTBS polygons meeting the disc with dates overlapping the window +- 30 days.
  - The witness set that made the case verified (witness names only, e.g. "GOES, S2_SCAR"; no tier, no "placebo").
  - ESA WorldCover class of the disc centre.

## 4. Classes

Applied in this order; the first rule that fits decides.

**(b) non-fire** (land change or non-fire heat), with one subtag:
* `static_heat`: the heat items sit on a place that is hot on many other days (>= 5 days of FIRMS detections within
  1 km outside the window in the same or adjacent year, or FIRMS type 1/2/3), e.g. a flare, plant or mine, and
  the images show no burn patch.
* `harvest`: crop or timber harvest; brightening or greening/browning confined to straight field or stand edges,
  bare soil or stubble showing, no char (true colour does not darken; SWIR false colour turns pink/tan, not dark).
* `clearing`: vegetation removed for a road, pad, pipeline, solar farm, lot or similar, often with bright bare soil.
* `construction`: new buildings, pavement, pads or earthworks.
* `water`: a water edge, flooding, reservoir drawdown or wetland change explains the dNBR.
* `other_change`: another explained non-fire change (snow, phenology across the whole window, cloud/shadow residue
  in the mask, mis-registration).
  A heat detection does not rescue a case in (b) unless rule (a) below fits.

**(a) fire** (for placebos: a real fire with no FPA FOD record by construction; "unrecorded" means not in FPA FOD
within 5 km and 30 days, and the audit says when another agency polygon such as FACTS covers it), when either:
* `burn_patch`: the post image shows a patch in or touching the disc that darkens in true colour and turns dark
  red-brown or black in the short-wave false colour (SWIR2 up, NIR down), absent in the pre image, and either its
  outline is not set by straight parcel edges or an independent heat item (FIRMS, HMS point, S2/Landsat hot spot)
  lies on it in the window. A blackened field with straight edges and heat on it is a fire (agricultural or
  prescribed burn; subtag `ag_or_rx_burn`); without heat it is (c).
* `heat_only`: no visible patch (or the pair is not clear), and heat from at least two independent overpasses or
  two sensors falls within 1 km in the window, the place is not static heat by the rule above.

**(c) unclear**: anything else, including no clear image pair with fewer than two heat overpasses; a dark change
that could be shadow, wet soil, flooding or harvest residue; and conflicting cues.

Each classification records: class, subtag, one sentence of reason naming what in the image or the evidence decided
it, and the rater's confidence (low / medium / high; descriptive only).

## 5. Raters and agreement

Two independent raters, each a separate Claude model instance (not a human analyst, not trained in remote-sensing
photo-interpretation), each given this rubric and the case images in batches, blind to placebo/record status and to
the other rater. Final class = the class both raters gave; any disagreement in class is final (c) unclear. Agreement
is reported as raw agreement and Cohen's kappa, per arm (P and R).

## 6. Numbers reported

For each arm: counts in (a), (b), (c), each with a Wilson 95 % interval on the share of the arm's n; (b) by subtag;
and the same for rater 1 alone and rater 2 alone. For P, the share (a) is also stated against the 91,224 searched
placebos (what it implies for the C1 rate if (a) placebos were treated as not false). Every number in
`results/VERIFIED_AUDIT.md` carries its n, interval, source file, and what it does not show. Failures (cases with no
image, rebuild mismatches, raters unable to decide) are reported as failures, not dropped.

## Amendment log

(none)

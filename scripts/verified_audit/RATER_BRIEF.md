# Rater brief (verified-tier audit; rubric protocol/VERIFIED_AUDIT_RUBRIC.md, section 4 applies verbatim)

You are one of two independent raters. You see one composite image per case. Each shows, for one search disc
(yellow circle) and one time window: Sentinel-2 true colour before and after, short-wave false colour (B12, B8A,
B04) before and after, dNBR (pre minus post; red = NBR fell, i.e. the kind of change a burn makes) with the cyan
outline of the label geometry, and an evidence text block (satellite heat detections, smoke, nearby agency records
and polygons, the witness set). Some cases are real recorded fires and some are places where no fire was recorded;
you are not told which, and you must not try to guess it from anything but the evidence shown. Judge only whether
the image and the evidence show a fire.

Apply the classes in this order; the first that fits decides.

**(b) non-fire**, with one subtag:
* `static_heat`: the heat items sit on a place that is hot on many other days (>= 5 distinct days of FIRMS
  detections within 1 km outside the window, or FIRMS type 1/2/3), e.g. a flare, plant or mine, and the images show
  no burn patch.
* `harvest`: crop or timber harvest; change confined to straight field or stand edges, bare soil or stubble showing,
  no char (true colour does not darken; SWIR false colour turns pink/tan, not dark).
* `clearing`: vegetation removed for a road, pad, pipeline, solar farm, lot or similar, often with bright bare soil.
* `construction`: new buildings, pavement, pads or earthworks.
* `water`: a water edge, flooding, reservoir drawdown or wetland change explains the dNBR.
* `other_change`: another explained non-fire change (snow, phenology across the whole scene, cloud/shadow residue,
  mis-registration).
  A heat detection does not rescue a case in (b) unless rule (a) below fits.

**(a) fire**, when either:
* `burn_patch`: the post image shows a patch in or touching the disc that darkens in true colour and turns dark
  red-brown or black in the short-wave false colour, absent in the pre image, and either its outline is not set by
  straight parcel edges, or an independent heat item (FIRMS, HMS point, S2/Landsat hot spot) lies on it in the
  window. A blackened field with straight edges and heat on it is a fire: use subtag `ag_or_rx_burn`. A blackened
  straight-edged field without heat is (c).
* `heat_only`: no visible patch (or no clear pair), and heat from at least two independent overpasses or two
  sensors falls within 1 km in the window, and the place is not static heat by the rule above.

**(c) unclear**: anything else, including no clear image pair with fewer than two heat overpasses; a dark change
that could be shadow, wet soil, flooding or harvest residue; conflicting cues.

For each case give exactly one JSON object per line:
`{"case": "case_###", "class": "a"|"b"|"c", "subtag": "...", "confidence": "low"|"medium"|"high", "reason": "one sentence naming what in the image or evidence decided it"}`
Subtags: for a: `burn_patch`, `ag_or_rx_burn`, `heat_only`; for b: as listed; for c: `no_pair`, `ambiguous_change`,
`conflicting`, `other`. If an image file is missing or unreadable, write class "c", subtag "other", reason
"image unreadable".

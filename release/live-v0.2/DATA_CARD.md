# Data card — live-v0.2

- **What:** for 100 US wildfires (WFIGS incidents 2023-01-10 to 2025-04-05 with a polar satellite detection within 3 km
  and no heat in the 9 days before; 25 per final-size class; seed 52), the earliest GOES frame at which the fire is
  distinguishable from the site's own history (thermal onset, frozen v0.1 method A2), whether a visible-band plume
  supports it, and FRP / burning area at the onset frame.
- **Sources:** GOES-16 and GOES-18 ABI L1b (bands 1, 7, 14), L2 clear-sky mask (ACMC) and fire product (FDCC), public
  NOAA buckets on AWS; WFIGS incident locations; FIRMS (for placebo cleanliness). Raw files are not redistributed.
- **Columns (main):** onset_utc / onset_lo / onset_hi (UTC, bootstrap interval), onset_sat, label_kind (two witnesses,
  one witness, no earlier onset), lead_vs_* (minutes before first standard detection, fire product, polar, discovery);
  supported / plume_lead_min (smoke); frp_mw, frp_lo, frp_hi (MW, 95 % interval incl. ±10 % for the T⁴ approximation),
  t_bg (K), area_m2 (at 800 K), area_lo_m2 / area_hi_m2 (1200 K / 600 K with the FRP interval).
- **Known limits:** the smoke witness does not work as specified (V2 failed; thick plumes flagged as cloud are removed,
  bright components above 50 pixels are ignored). Our FRP runs ~1.5× above the product's at its first detection; at the
  onset frame there is no independent truth. Only 12 of 100 fires have an earlier onset; no class-0 fire does.
- **Intended use:** research on early detection and its limits; not for operational alerting.

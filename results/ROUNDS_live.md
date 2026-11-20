# ROUNDS_live — improvement loop (track 51, protocol §9)

Dev fires only; the sealed test is not opened for any round. Each round: replay on dev, read the trace of every late or
missed fire and every false alert, name one cause, change one thing, replay. Kept only if the cross-validated dev lead
improves at the same false-alert budget (1 clustered false alert per 10,000 pixel-site-days).

| round | cause named | change | dev score before → after (mean clipped lead, min) | false alerts / site-day | kept |
|---|---|---|---|---|---|
| R1 | polar site and GOES pixel offset by terrain parallax / navigation (8 fires 'weak signal at site') | site radius 1 -> 2 pixels (alert within ~5 km) | -53.7 → -49.7 (earlier 11 → 13 of 96; no alert 52 → 52; h 64 → 64) | 9.88e-05 | yes |
| R2 | scene filter discards the fire's own hot pixels and smoke (e.g. 2024-IDSCF-240103) | scene filter ignores the central 11 x 11 pixels | -49.7 → -50.7 (earlier 13 → 12 of 96; no alert 52 → 52; h 64 → 72) | 9.88e-05 | no |
| R3 | history too cloudy for 6 values at +-5 min (monsoon; 2023-AZA3S-231213, 2023-NMGNF-000428) | history fallback to +-30 min where +-5 min has < 6 values | -49.7 → -39.6 (earlier 13 → 16 of 96; no alert 52 → 47; h 64 → 67) | 9.88e-05 | yes |
| R4 | ACM files missing for hours (2024-UTUWF-200810, 2024-CAANF-243334) | cloud reference falls back to the pixel's own clear BT14 history | -39.6 → -40.5 (earlier 16 → 16 of 96; no alert 47 → 48; h 67 → 68) | 9.88e-05 | no |
| R5 | growing fires lose evidence when more than 4 neighbours are hot (late fires) | compactness limit 4 -> 8 pixels | -39.6 → -42.4 (earlier 16 → 15 of 97; no alert 47 → 50; h 67 → 88) | 9.88e-05 | no |
| R6 | fire under ACM-flagged cloud edge with clear 3.9 um excess (thin cloud) | keep a cloud-flagged pixel >= 10 K hotter at 3.9 um than its annulus | -39.6 → -47.9 (earlier 16 → 13 of 96; no alert 47 → 48; h 67 → 93) | 9.88e-05 | no |

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
| R7 | false alerts recur at the same pixels on several days (static or intermittent industrial heat; e.g. 33.695 N 116.567 W on two days, 34.85 N 118.675 W for 12 h) | no alert where G reached 40 within 1 px on any of the 7 previous days | -39.6 → -42.8 (earlier 16 → 15 of 96; no alert 47 → 48; h 67 → 66) | 9.88e-05 | no |
| R8 | daytime false alerts from solar heating of bare surfaces raise BT7 alone; BT7-BT14 cancels part of it | feature BT7 -> BT7-BT14 (same filters) | -39.6 → -49.6 (earlier 16 → 11 of 95; no alert 47 → 48; h 67 → 80) | 9.88e-05 | no |
| R9 | late fires with moderate, persistent signal accumulate too slowly | reference value k 4 -> 3 | -39.6 → -47.5 (earlier 16 → 14 of 96; no alert 47 → 50; h 67 → 106) | 9.88e-05 | no |
| R10 | single-frame spikes (glint, transient hot surfaces) jump straight to the threshold | cap 40 -> 20 | -39.6 → -43.1 (earlier 16 → 16 of 96; no alert 47 → 49; h 67 → 66) | 9.88e-05 | no |
| R11 | both satellites see weak early signal that neither alone carries over the threshold | two-witness divisor rho 1.5 -> 1.25 | -39.6 → -40.2 (earlier 16 → 16 of 96; no alert 47 → 48; h 67 → 70) | 9.88e-05 | no |
| R12 | intermittent cloud during onset: evidence decays by 10 % per cloudy frame and is lost before the fire clears the threshold | cloud decay 0.9 -> 0.97 | -39.6 → -40.9 (earlier 16 → 16 of 96; no alert 47 → 48; h 67 → 71) | 9.88e-05 | no |

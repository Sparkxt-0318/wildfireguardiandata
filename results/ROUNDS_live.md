# ROUNDS_live — improvement loop (track 51, protocol §9)

Dev fires only; the sealed test is not opened for any round. Each round: replay on dev, read the trace of every late or
missed fire and every false alert, name one cause, change one thing, replay. Kept only if the cross-validated dev lead
improves at the same false-alert budget (1 clustered false alert per 10,000 pixel-site-days).

| round | cause named | change | dev score before → after (mean clipped lead, min) | false alerts / site-day | kept |
|---|---|---|---|---|---|
| R1 | polar site and GOES pixel offset by terrain parallax / navigation (8 fires 'weak signal at site') | site radius 1 -> 2 pixels (alert within ~5 km) | -53.7 → -49.7 (earlier 11 → 13 of 96; no alert 52 → 52; h 64 → 64) | 9.88e-05 | yes |

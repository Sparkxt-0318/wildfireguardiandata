# ROUNDS_live — improvement loop (track 51, protocol §9)

Dev fires only; the sealed test is not opened for any round. Each round: replay on dev, read the trace of every late or
missed fire and every false alert, name one cause, change one thing, replay. Kept only if the cross-validated dev lead
improves at the same false-alert budget (1 clustered false alert per 10,000 pixel-site-days).

| round | cause named | change | dev score before → after (mean clipped lead, min) | false alerts / site-day | kept |
|---|---|---|---|---|---|

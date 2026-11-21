# fuel v0.1

Rules-only fuel-map checker (track 53). Overlays (verdict, rules fired, suggested class, manifest, map, report) for the 10 sealed areas (LF2022 map M22 and LF2016 map M16) and for the 29 rebuilt fires (LF2016 map). Evidence-card tables are left out of the zip (100 MB with them); regenerate with `python -m firewitness fuel check <area>`.

Sealed result (M22, 1,819 plots): F1 ratio 7.91 [6.36, 10.03], F2 0.92 %, F3 pass. See `results/FUEL_RESULTS.md` for every number, its n and interval, the 29-fire stretch (no improvement), and the limitations, including that only round 1 of the improvement loop came from reading individual wrong verdicts.

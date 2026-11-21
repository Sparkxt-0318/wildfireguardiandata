# records v0.3 release files

- `scar_size_flags.jsonl.gz`: 121 flag patches on FPA FOD records ("scar much smaller than recorded size"), with fuel type and the module verdict for that fuel type. Flags, not perimeters.
- `gazetteer_suggestions.csv`, `gazetteer_suggestions_patches.jsonl.gz`: GNIS place-name placements for 204 ICS-209 incidents with missing coordinates, in new fields (`suggested_lat`, `suggested_lon`, `suggested_radius_km`, `location_status` = "suggested location, unverified"). Never repairs; the radii are 31 to 73 km (90% coverage on dev), the sealed coverage was 35 of 40 (Wilson 73.9% to 94.5%).
- `v03_gazetteer_radii.json`: radii by place type, frozen before the sealed incidents were scored. `sealed_v03_gazetteer.csv`: the sealed matches.
- `v03_swap_dev_pooled.json`, `sealed_v03_swap_pooled.json`, `sealed_v03_swap_by_year.json`: day-month swap test per group (no group called swap).
- `known_perimeters_v03.csv`, `known_perimeter_fuel_summary.json`: scar area against MTBS perimeters by fuel type (timber: module under-measures; grass and shrub: not clear).

Results, failures and the open finding on OK Forestry: `results/RECORDS_RESULTS.md` (addition dated 2026-11-21T03:20Z). Protocol: `protocol/RECORDS_PROTOCOL_v0.3.md`.

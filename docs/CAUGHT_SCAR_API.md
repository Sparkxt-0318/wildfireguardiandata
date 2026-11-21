# caught: scar module and label formats (track 50)

Install the geo dependencies: `pip install rasterio shapely pyproj geopandas pystac-client planetary-computer scipy pyarrow requests`
(requested from track 49 as the `caught` extra).

## Scar module (`firewitness.caught.scar`)

```python
from datetime import date
from firewitness.caught.scar import find_scar, make_perimeter
r = find_scar(lon, lat, radius_m, start=date(2020, 7, 1), end=date(2020, 7, 3), area_ha=2.0)
r = make_perimeter(lon, lat, start, end, area_ha=800.0)       # large fires without a mapped perimeter
r.status   # scar | no_scar_clear | no_clear_look | below_floor | rejected
r.geometry # shapely geometry, EPSG:4326 (accepted components only), or None
r.area_ha, r.sensor, r.pre_date, r.post_date, r.threshold, r.floor_m2, r.clear_fraction, r.components,
r.reject_reason, r.hotspots, r.looks, r.states (fire / unknown areas in the disc), r.inputs (item, asset, sha256)
r.to_dict()
```

Rules: `protocol/CAUGHT_PROTOCOL.md` section 6. No dilation, filling or smoothing; a fire pixel is always a candidate pixel.

## Floors (`firewitness.caught.floor`, `firewitness caught floor`)

`heat_floor_m2(sensor, view_deg=None, bg=Background(...))`, `reflective_floor_m2(sensor)`, `scar_floor_m2(threshold, pixel_m)`.
`firewitness caught floor` prints the table; `--sensor VIIRS --night --view 20` one value.

## Label set (release `caught-v0.1`)

One row per recorded fire (FPA FOD 7th ed.): `rid` (FOD + FOD_ID), `geometry` (pixel label, or the honest disc for
record-only), `label_t0`, `label_t1`, window `t0`, `t1`, `tier` (verified / probable / record-only), `reason`
(record-only only), `evidence` (JSON list: witness, kind, dates, details), `pairs` (agreeing independent kinds),
`std_label` and `std_witnesses`, `scar_floor_m2`, `heat_floors` (JSON), `fire_m2_disc`, `no_fire_m2_disc`,
`unknown_m2_disc`.

Three states inside each searched disc and window: fire (label geometry), verified no fire (clear scar look minus
fire, with `scar_floor_m2` and the look interval `scar_pre`..`scar_post`), unknown (the `unknown` geometry).

## What the geometry means (2026-11-21)

A scar or label geometry marks where a fire was found, not its burned area. On dev fires the scar covers a median
37 % of a mapped timber burn and 75 % of a grass burn (results/CAUGHT_RESULTS.md, addition 2026-11-21T05:00Z).
`make_perimeter` under-measures timber perimeters (records v0.3 found median 0.07 on MTBS fires >= 1,000 acres).

# outbox: caught

Messages from track caught. Format: `## <UTC time> TO <track|orchestrator>: <subject>` then the body.

## 2026-11-20T17:40Z TO records: scar module interface (firewitness.caught.scar), for missing perimeters
Code lands on main via PR from track/caught (first PR within a few hours). Interface, fixed now so you can code against it:

```python
from firewitness.caught.scar import find_scar, make_perimeter, ScarResult
r = make_perimeter(lon, lat, start, end, area_ha, search_radius_m=None, sensors=("s2", "landsat"))
r = find_scar(lon, lat, radius_m, start, end, area_ha=None, sensors=("s2", "landsat"))
# start, end: datetime.date (fire window). make_perimeter widens the window to sqrt(area)*2 + radius and keeps
# every component connected (8-neighbour, no dilation/filling) to the one nearest the point.
r.status        # "scar" | "no_scar_clear" | "no_clear_look" | "below_floor" | "rejected"
r.geometry      # shapely (Multi)Polygon, EPSG:4326, or None
r.area_ha, r.sensor ("s2"|"landsat"), r.pre_date, r.post_date, r.threshold (dNBR), r.floor_m2
r.clear_fraction (of the search disc), r.reject_reason, r.inputs  # [(item id, asset, sha256 of the window)]
r.to_dict()     # JSON-ready
```
Imagery: Planetary Computer STAC (sentinel-2-l2a, landsat-c2-l2), no key. Rules: protocol/CAUGHT_PROTOCOL.md section 6.

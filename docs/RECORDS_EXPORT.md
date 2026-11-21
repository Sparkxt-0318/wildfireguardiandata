# records: duplicate-collapse export (for the video track)

`firewitness records link --export-examples N --out-examples results/collapse_examples` writes one JSON per fire:

```
{"example_id": "ex000", "cluster_id": "FW-20080501-13000599-01",
 "members":  [{"source": "fpa_fod|ics209plus|mtbs", "record_id": str, "name": str|null, "date": "YYYY-MM-DD",
               "lat": float, "lon": float, "acres": float|null, "state": str, "cluster_id": str}],
 "pairs":    [{"a": record_id, "b": record_id, "probability": float, "outcome": "link"}],
 "merged":   {"name", "date", "lat", "lon", "acres", "state", "n_sources"},
 "raw_kept": same list as members, unchanged}
```
`cluster_id` is the permanent fire ID (`FW-yyyymmdd-cell-ordinal`).

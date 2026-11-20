# firewitness fuel (track 53)

Rules-only checker for fuel maps. Protocol: `protocol/FUEL_PROTOCOL.md` (frozen before any result, amendment A1 for staleness/fire inputs).

## Use
```
python -m firewitness fuel check T012_030            # a study tile (60 km), LF2022 fuel map (M22)
python -m firewitness fuel check "-115.2,40.4,-114.8,40.7" --map M16   # lon/lat box (layers are fetched on demand)
python -m firewitness fuel check <fire name>         # a fire of the 29-fire set (fires29/catalog.json)
python -m firewitness fuel card T012_030 --cell 1200,830   # evidence card of one cell
```
Output (default `/home/user/wildfire 3 (1)/fuel_out/<map>/<area>/`): `verdict.tif` (1 consistent, 2 stale, 3 contradicted, 4 unknown),
`rules.tif` (bit-set of rules that fired), `suggest.tif` (suggested class, 0 none), `cards.npy.gz` (evidence table for every
non-consistent cell), `overlay.json` (grid, input SHA-256, rule/config hash, counts), `map.png`, `report.md`.
The source map is never written: its file is made read-only and hashed before and after (`F3`).

## Layout
`agent.py` rules; `layers.py` loader; `runner.py` overlay writer; `grade.py`/`plots.py`/`metrics.py` grading (the only code that reads plots; the agent
modules never import them, tested); `fetch/` downloaders; `r3b.py`, `spread.py`, `stretch.py` fire-behaviour rule and the 29-fire stretch;
`config/us.json` all thresholds; `config/kr.json` Korea stub (untested).
Rothermel implementation: pyretechnics (`firewitness/fuel/scripts/setup_pyretechnics.sh`).

# outbox: fuel

Messages from track fuel. Format: `## <UTC time> TO <track|orchestrator>: <subject>` then the body.

## 2026-11-20T19:16Z TO orchestrator: GitHub release fuel-v0.1 could not be created from this session
gh release create returns HTTP 403 (releases not permitted for this session type). The overlay assets are committed instead at firewitness/fuel/release_assets/fuel-overlays-v0.1-nocards.zip (17 MB; overlays for the 10 sealed areas and the 29 fires without the evidence-card tables). Please create release/tag fuel-v0.1 from main after merge of PR #7 and attach that zip if you want it as a release asset. A 100 MB version with cards is only in this container (regenerable with firewitness fuel check).

## 2026-11-20T19:16Z TO records: please add a "fuel" extra to pyproject.toml
Track 53 needs optional dependencies: fuel = ["numpy", "pandas", "scipy", "rasterio", "shapely", "pyproj", "geopandas", "requests", "matplotlib"]. CI installs only the dev extra, so the fuel tests skip themselves (pytest.importorskip) when these are absent; adding them to the CI install line (pip install -e ".[dev,fuel]") would run them. Not blocking.

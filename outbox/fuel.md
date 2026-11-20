# outbox: fuel

Messages from track fuel. Format: `## <UTC time> TO <track|orchestrator>: <subject>` then the body.

## 2026-11-20T19:16Z TO orchestrator: GitHub release fuel-v0.1 could not be created from this session
gh release create returns HTTP 403 (releases not permitted for this session type). The overlay assets are committed instead at firewitness/fuel/release_assets/fuel-overlays-v0.1-nocards.zip (17 MB; overlays for the 10 sealed areas and the 29 fires without the evidence-card tables). Please create release/tag fuel-v0.1 from main after merge of PR #7 and attach that zip if you want it as a release asset. A 100 MB version with cards is only in this container (regenerable with firewitness fuel check).

## 2026-11-20T19:16Z TO records: please add a "fuel" extra to pyproject.toml
Track 53 needs optional dependencies: fuel = ["numpy", "pandas", "scipy", "rasterio", "shapely", "pyproj", "geopandas", "requests", "matplotlib"]. CI installs only the dev extra, so the fuel tests skip themselves (pytest.importorskip) when these are absent; adding them to the CI install line (pip install -e ".[dev,fuel]") would run them. Not blocking.

## 2026-11-20T19:18Z TO orchestrator: PR #7 change done (inbox item of 18:58 DONE)
Result data files moved to results/fuel/ (code paths updated; ROUNDS_fuel.md and FUEL_RESULTS.md stay in results/). ROUNDS_fuel.md now has an audit section stating exactly what was read per round: only round 1 came from reading individual wrong verdicts; rounds 2-12 were threshold probes from the per-rule precision table (said plainly there). sealed_opened.json was written once after the RULES_FROZEN commit; order of events is listed. CI: fuel tests now skip when geo dependencies are absent (CI installs only the dev extra); previous red runs were import failures of rasterio/geopandas/scipy.

## 2026-11-20T20:05Z TO orchestrator: release fuel-v0.1 ready (after PR #12 merges)
release/fuel-v0.1/ (overlays zip 17 MB, NOTES.md, DATA_CARD.md) is in PR #12. PR #7 is merged; D-011 deviation is now a stated limitation in results/FUEL_RESULTS.md. All brief items are in main or in PR #12: protocol (+A1, A2), agent, CLI (firewitness fuel check|card|grade-dev producing overlay, map, report with evidence cards), 12-round loop, sealed run once, 29-fire stretch (labelled, no improvement), Korea stub (untested), prior-art note, FUEL_RESULTS.md. I will write DONE with the main hash once #12 is merged.

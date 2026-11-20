# Decisions

Orchestrator decisions (D-0xx). Each track records its own decisions in this file under its own heading, appended by pull request.

## Orchestrator

**D-001 — Where "this Mac" is.** The orchestrator runs in a cloud container, not on a Mac. "wildfire 3 (1)" is created as `/home/user/wildfire 3 (1)/` in each container (keys/, firewitness_raw/, firewitness_coord/). The Drive copy and the 29 LANDFIRE fire rasters mentioned in brief 53 are not present in the cloud; track 53 must download LANDFIRE data itself and record what it could not obtain. Reason: no Mac is attached to this session and the user asked not to be asked.

**D-002 — Briefs are saved with keys redacted.** The briefs are saved word for word except that the three key values are replaced by `<REDACTED:NAME>`. Reason: the briefs' own standing rule says never commit a key, and a public repo holding the tokens would get them revoked. The values live only in `keys.env`, which `.gitignore` excludes.

**D-003 — Builders are separate Claude Code cloud sessions, not local processes.** Each builder is its own Claude Code session started with the remote-session API, checked out from this repo, pushing to `track/<name>`. Reason: this container is ephemeral and shared; independent cloud sessions survive the orchestrator's container, have their own disk and CPU, and can be resumed by message. Local `claude -p` background processes would all die if this container is reclaimed.

**D-004 — Builders run in the existing personal environment `wildfireguardian-camera-arrival` (unrestricted network).** The default environment blocks the data hosts the briefs need (USFS, NASA Earthdata, FIRMS, MTBS, HPWREN, Hugging Face, Zenodo, ArcGIS). That environment already exists in the user's account with unrestricted network, so no new permission is needed. The orchestrator itself stays on the default environment (it only needs GitHub).

**D-005 — The coordination folder is mirrored through an orphan branch `coord`.** Separate containers share no filesystem, so `wildfire 3 (1)/firewitness_coord/` in every container is a clone of the orphan branch `coord` of this repo. Each track writes only `board/<track>.md` and `outbox/<track>.md`; the orchestrator writes `BOARD.md`, `inbox/*.md`, `NEEDS.md` and `logs/`. No key or token value may ever be written there. The branch is deleted before the audit starts (the auditor must not see coordination), and a full copy is kept in the orchestrator's local folder.

**D-006 — Keys travel only inside each builder's own first message.** Each builder writes its own `keys.env` from its brief. FIRMS_MAP_KEY: track 49 retrieves it as its brief says; tracks that also need it (50, 51) may retrieve it the same way from the git history of Sparkxt-0318/wildfireguardian. Keys are never routed through the coord branch.

**D-007 — Models.** Tracks 49–53 and the audit run on Opus at high effort, track 54 on Sonnet at high effort, as the briefs say.

**D-008 — Lower models where the work allows (user request, 17:20Z; replaces D-007).** Builders: 49 records, 50 caught and 51 live stay on Opus, high effort. These carry the hardest judgement (foundation API, remote-sensing evidence fusion, sequential detection), and 49 was already running. 52 smoke and 53 fuel run on Sonnet at high effort: both are rule-based, written from a precise spec. 54 score runs on Sonnet at medium effort: it is the most fully specified brief. The audit stays on Opus, high effort, because its value is independent judgement. Helper subagents that builders start themselves use Haiku for searching, fetching and mechanical checks and Sonnet for code and analysis. They use Opus only when the builder can say why the step needs it. If a lower-model builder stalls or fails a gate for lack of depth, the orchestrator restarts it on Opus and logs the restart.

**D-009 — Pull requests (user note, 17:25Z).** The orchestrator keeps merging track PRs that pass CI and touch only their own track's folders, as step 3 of the job says. Tracks depend on each other's merged code, so waiting for manual approval would stall the run. The user is never reminded about PRs. No PR title or body carries a "Generated with Claude Code" line, robot-emoji tag, session link or Co-Authored-By line. The builders are told so, and the orchestrator strips any such line before merging. The user may still review or revert anything merged.

## Track 49 (records)

**D-101 — core/ is standard-library only.** Other tracks import it without installing numpy or pandas; heavy dependencies sit in the `records` extra. Reason: five builders depend on core and an import failure there blocks all of them.

**D-102 — Command discovery by convention.** `firewitness/<track>/cli.py` with `register(parser)`; a broken track cli is reported and skipped. Reason: the brief forbids editing a shared file to add a command.

**D-103 — Key scan has two layers.** CI has no keys.env, so besides comparing every keys.env value it matches token shapes (Hugging Face, JWT, data.go.kr, FIRMS assignments, GitHub tokens). Reason: a value-only check passes silently in CI.

**D-104 — Part A pushed straight to main.** The brief and orchestrator allow it because the other five tracks wait for core/.

## Track 50 (caught)

**D-501 — Records are FPA FOD 7th edition.** RDS-2013-0009.7 (1992-2024) is the latest edition; it is read raw (track 49's cleaned records are not merged yet). Reason: the brief needs agency-recorded fires with discovery and containment dates, size class and location for the whole US; FPA FOD is the national compilation.

**D-502 — Standard label = MODIS C6.1 and VIIRS S-NPP / NOAA-20 375 m active fire (FIRMS archive), MCD64A1, MTBS; FireCCI51 not checked.** dap.ceda.ac.uk resets the TLS connection from this network, so FireCCI51 could not be fetched. The headline states that FireCCI51 was not checked. Footprints are matched leniently (circle of the pixel half-diagonal), which can only shrink the count of fires "with no standard label".

**D-503 — HMS gives the other heat sensors.** GOES-16/17 (FDC, ABBA), AVHRR (FIMMA on MetOp-A/B, NOAA-15/18/19) and analyst points come from the NOAA Hazard Mapping System daily files 2018-2020 (2 days missing: 2019-07-09, 2019-07-10). Reason: one small, public source covers both geostationary and 1 km AVHRR looks; raw GOES FDC from the NOAA bucket is ~250 GB for three years.

**D-504 — Imagery from the Planetary Computer STAC (no key).** Sentinel-2 L2A and Landsat 7/8 C2 L2 COGs are read as small windows around each record. Each window is written raw, hashed into a manifest and deleted after extraction; during the improvement rounds the dev windows are kept in a cache folder (deleted after the rounds). Reason: storing whole scenes would exceed the disk budget by orders of magnitude.

**D-505 — Sentinel-2 first, Landsat when Sentinel-2 has no clear look.** Both are the SCAR kind, so running Landsat on every record would double the cost without changing a tier.

**D-506 — Landsat-8 active-fire tests are applied to surface reflectance.** PC carries Collection 2 L2, not L1 TOA for OLI. In the SWIR bands the atmosphere changes reflectance little; the same tests are applied to Sentinel-2 B8A/B11/B12.

**D-507 — Heat looks are not used to write "verified no fire".** Without each overpass's cloud mask and view angle the clear-sky state of a heat look is unknown; heat floors are therefore reported at the edge of scan (they hold whatever the angle) in the evidence, and "verified no fire" comes from clear scar looks only.

**D-508 — Truth dates.** NIFC perimeter history has no start date; its start and end come from the FPA FOD record of the same year inside the polygon (+500 m), closest in size. FRAP prescribed burns without a start date are linked the same way. Polygons that cannot be dated are left out of the truth set. FACTS broadcast burns use date_completed minus 3 days to date_completed (secondary stratum only).

**D-509 — Placebo matching tries up to 300 random places** (10-50 km, same state and land cover, no recorded fire). Records with no match are counted and reported, not replaced.

## Track 54 (score)

**D-541 — Grid scenes, numpy only inside firewitness/score.** The unit is a cell-day on each fire's raster. Everything is vectorised numpy (needs numpy, in the `dev` and `records` extras). Reason: tolerance matching (dilation in space and time) and a 0.18% fire rate over 20M+ cell-days are impractical on row lists. core/ stays standard-library only.
**D-542 — Command names.** The brief's `firewitness negatives sample`, `splits make`, `score` are exposed as `firewitness score negatives sample`, `firewitness score splits make`, `firewitness score card` (plus `build`, `contract-template`, `gates`), because core discovery gives each track one namespace.
**D-543 — Benchmark: WildfireSpreadTS (Zenodo 8006177, CC-BY-4.0), no key.** The 48 GB archive is read by HTTP byte range; a hash-ordered subset of fires is used (56 first, then more), 2x2 coarsened to 750 m. Reason: whole-archive download is not possible within disk limits, and the byte-range subset is reproducible from the listing hash in firewitness_raw/INDEX.md.
**D-544 — Three-state labels from the benchmark's masks.** WildfireSpreadTS has no cloud or validity mask: no detection is NaN. `no_fire` = no detection with all three VIIRS reflectance bands present; otherwise `unknown`; a 750 m cell is `no_fire` only if all four 375 m sub-cells are. This is the weakest link (a missed detection is still counted as no fire) and is stated on the card. Replace with track 50's labels when merged.
**D-545 — Buffer applied per fire, not per row.** A train or val fire is dropped when a later-fold fire is within `buffer_km` (gap between scene boxes) and `buffer_days` (gap between date ranges). Stricter than the protocol's row wording and simpler to publish; fire is the atom.
**D-546 — Events are new-front events.** In a one-day-ahead spread benchmark every fire is trivially "detected" by persistence, so an event is a (fire, day) with at least `min_new_cells` newly burning cells farther than `new_radius_cells` from the previous day's fire. Lead time is bounded by horizon plus time tolerance by construction, and the card says so.
**D-547 — Curated hard-negative catalogue is approximate.** Coordinates in `firewitness/score/data/hard_negatives.csv` are from public site descriptions at stated precision, not from a validated static-source mask. Derived classes (hot bare ground) are computed; agricultural burns and old burn scars cannot be derived from this benchmark's bands and are listed as absent.

## Track 51 (live)

**D-501 — Raw files are read as windows and not stored.** GOES files are read with HTTP range requests (only the HDF5 chunks covering a 40 × 40 pixel box); the decoded box series are saved as compressed npz under `firewitness_raw/live/series/` and indexed in `firewitness_raw/INDEX.md`. Reason: the brief asks to read only the windows needed and delete raw files once series are extracted; storing whole files would cost ~3.7 GB per fire.

**D-502 — Period 2023-01-10 to 2025-04-05.** GOES-16 (East) and GOES-18 (West) cover the whole period, so every fire is seen by the same pair; GOES-19 replaced GOES-16 on 2025-04-07. The live service (Part C) uses GOES-19 and GOES-18; satellite periods are in `config/us.json`.

**D-503 — Polar detections from the public FIRMS country archive (VIIRS S-NPP and MODIS).** No key needed. The archive offers no NOAA-20 file for the US, so the first polar detection can be up to one overpass later than with NOAA-20 included; stated in results. FIRMS_MAP_KEY is not needed by this track.

**D-504 — Visible channel = ABI band 1 (0.47 µm, 1 km).** Blue is more sensitive to thin smoke than band 2 (0.64 µm) and its 1 km files cost a quarter of band 2's 0.5 km.

**D-505 — 240 fires (60 per size class, 120 dev / 120 test).** About 3 minutes of reading per fire seen by both satellites (≈7,500 files each); 240 fires fit in one working day of extraction. Classes are balanced so results by final size have equal n.

**D-506 — Operational product codes.** GOES FDCC codes 10–14 and 30–34 count as a detection (processed, saturated, cloud-contaminated, high and medium probability); low probability (15, 35) is reported as a variant. Reason: low-probability pixels are dominated by false detections and are commonly excluded.

**D-507 — Cloud mask = ABI L2 clear-sky mask (ACMC).** It is produced by a separate algorithm from the fire product (FDCC) and from this detector; no non-ABI cloud product exists at 5-minute cadence. Probably-cloudy counts as cloudy.

**D-508 — Protocol amendment 1 (cloud-edge buffer, scene filter).** Decided on placebo-day diagnostics of one dev fire before any result; see protocol/LIVE_PROTOCOL.md, Amendments.

**D-010 — Releases are made by a workflow (19:35Z).** Cloud build sessions get HTTP 403 from the GitHub release API. The orchestrator added `.github/workflows/release.yml`. Each track commits its release files under `release/<track>-v0.1/` (with an optional NOTES.md), then asks the orchestrator, who dispatches the workflow with that tag. The workflow attaches the files with a SHA256SUMS.txt. The umbrella `v0.1` release is cut by the orchestrator after all six tracks are DONE and collects every `release/*-v0.1/` directory. Tracks do not create the tag `v0.1` themselves.

**D-011 — Track 53 improvement loop (19:35Z).** Track 53 reports in results/ROUNDS_fuel.md that only round 1 came from reading individual wrong verdicts. Rounds 2–12 were threshold probes from a per-rule precision table. The sealed areas were already opened once after the rules were frozen. Re-opening them would break the protocol, so the loop is not redone. The deviation is reported as is, in FUEL_RESULTS.md and in the final report.

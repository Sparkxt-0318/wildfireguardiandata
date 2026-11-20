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

## Track 54 (score)

**D-541 — Grid scenes, numpy only inside firewitness/score.** The unit is a cell-day on each fire's raster. Everything is vectorised numpy (needs numpy, in the `dev` and `records` extras). Reason: tolerance matching (dilation in space and time) and a 0.18% fire rate over 20M+ cell-days are impractical on row lists. core/ stays standard-library only.
**D-542 — Command names.** The brief's `firewitness negatives sample`, `splits make`, `score` are exposed as `firewitness score negatives sample`, `firewitness score splits make`, `firewitness score card` (plus `build`, `contract-template`, `gates`), because core discovery gives each track one namespace.
**D-543 — Benchmark: WildfireSpreadTS (Zenodo 8006177, CC-BY-4.0), no key.** The 48 GB archive is read by HTTP byte range; a hash-ordered subset of fires is used (56 first, then more), 2x2 coarsened to 750 m. Reason: whole-archive download is not possible within disk limits, and the byte-range subset is reproducible from the listing hash in firewitness_raw/INDEX.md.
**D-544 — Three-state labels from the benchmark's masks.** WildfireSpreadTS has no cloud or validity mask: no detection is NaN. `no_fire` = no detection with all three VIIRS reflectance bands present; otherwise `unknown`; a 750 m cell is `no_fire` only if all four 375 m sub-cells are. This is the weakest link (a missed detection is still counted as no fire) and is stated on the card. Replace with track 50's labels when merged.
**D-545 — Buffer applied per fire, not per row.** A train or val fire is dropped when a later-fold fire is within `buffer_km` (gap between scene boxes) and `buffer_days` (gap between date ranges). Stricter than the protocol's row wording and simpler to publish; fire is the atom.
**D-546 — Events are new-front events.** In a one-day-ahead spread benchmark every fire is trivially "detected" by persistence, so an event is a (fire, day) with at least `min_new_cells` newly burning cells farther than `new_radius_cells` from the previous day's fire. Lead time is bounded by horizon plus time tolerance by construction, and the card says so.
**D-547 — Curated hard-negative catalogue is approximate.** Coordinates in `firewitness/score/data/hard_negatives.csv` are from public site descriptions at stated precision, not from a validated static-source mask. Derived classes (hot bare ground) are computed; agricultural burns and old burn scars cannot be derived from this benchmark's bands and are listed as absent.

## Track 52 (smoke)

**D-521 — Working size 512 x 384.** FIgLib frames (2048 x 1536) are decoded with JPEG DCT scaling to 1/4 size; all distances in tests are at that size. Reason: deterministic, fast (80 frames in under a second), and smoke edges are tens of pixels wide.
**D-522 — Opacity is measured against a smoke colour fitted from the plume, with a grey fallback.** Over uniform sky the smoke colour and the opacity cannot be separated, so the fallback is stated (dark grey if the pixel got darker, light grey if lighter) and S1 reports the error by true smoke colour. Reason: an honest, reproducible definition; no claim of physical optical depth.
**D-523 — Noise bar is per pixel, the named level is scalar.** L0 = median over pixels of N(x), the largest opacity a pixel showed while smoke-free; a pixel is above the noise when it reaches max(L0, N(x)); the bar for pre-ignition frames is built without their own block. Reason: a pooled quantile is dominated by clouds, shadows and glints (L0 reached 1.0 on cloudy days); a per-pixel bar lets faint smoke over quiet sky be seen while glints raise the bar only at their own pixels. Replaced two earlier definitions (pooled quantile; MAD spread) after the dev placebo showed 51% false frames; see results/ROUNDS_smoke.md rounds 0a-0d.
**D-524 — Classes by lineage, one parent per region.** A region links to the earlier region that feeds it with the most area; a lineage is a root and its descendants. Reason: small noise regions swallowed by a growing plume made the plume impure under a "set of roots" rule and almost no plume was ever confirmed (S1 detection 22%).
**D-525 — Shadows are not smoke by a stated clause.** The smoke rule needs a texture loss of 15% or a chromaticity shift of 0.02 measured on the opacity core; a shadow keeps both. Reason: a moving tower shadow produced 13 of 36 false pre-ignition frames in one dev sequence.
**D-526 — Pyro-SDIS is S4-only with a relaxed background rule (protocol A2).** Only 1 of 1,007 events had the specified background; the relaxed rule gives about 10 events. Reason: it is the only way to put any Pyro human boxes on the opacity scale; the small n is stated everywhere.
**D-527 — HPWREN boxes copied into the repo.** Nine small CSVs (40 KB) under `firewitness/smoke/data/hpwren_bb/` with credit and no stated licence. Reason: S4 must be reproducible without a network call.
**D-528 — Opus not used.** The track runs on Sonnet at high effort as set by the orchestrator (D-008); the depth bar is held by the protocol gates, not by the model.

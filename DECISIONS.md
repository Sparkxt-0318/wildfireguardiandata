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

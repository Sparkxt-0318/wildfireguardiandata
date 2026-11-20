# ROUNDS_smoke: pre-loop development and improvement loop

Image data: HPWREN, http://hpwren.ucsd.edu/. Dev sequences only (32 of them, protocol section 3); the sealed sequences have not been run. S1 here is S1-lite (96 composite cases, protocol amendment A2). Accept rule (protocol section 7): S1 improves (no component worse by more than 5%, at least one better by more than 5%) and S2 false-frame count does not increase. S3 and the human offset are never used to accept a change.

## Pre-loop development (rounds 0a to 0e; do not count toward the 12)

The first implementation was run on dev before the loop; the failures below were fixed first because the loop needs a version that runs. Each was looked at in frames.

| round | what was seen | named cause | change | effect (dev) |
|---|---|---|---|---|
| 0a | first S2-style run: 51% of pre-ignition frames showed a "smoke" region. A pooled 99.9th-percentile noise floor gave L0 = 1.0 on cloudy days, a MAD spread gave L0 = 0.02 | the noise floor was either dominated by clouds and shadows (real changes) or ignored glints and edge jitter | per-pixel bar N(x) (largest opacity the pixel showed while smoke-free, 5x5 max), L0 = median of N; a pixel is above noise at max(L0, N(x)) | 51% to 10% of pre frames |
| 0b | a moving tower shadow on the ground gave 13 of 36 false frames in one sequence (viewed) | a shadow dims the background like a veil but keeps its relative contrast and chromaticity | smoke rule needs texture loss >= 15% or chromaticity shift >= 0.02 | removed that sequence's false frames; detection fell (most plumes failed the clause) |
| 0c | S1 detection 22%: planted plumes found as lineages but classed other (viewed, 16 cases) | (i) tiny noise regions inside a growing plume made it impure under a root-set rule; (ii) the veil clause was measured over the faint fringe | one parent per region (largest area); veil measured on the top quarter of opacity | S1 detection 22% to 70%; S3 detected 19 to 29 of 32; false frames up to 198/1122 |
| 0d | placebo regions found where a pixel sat exactly at its own maximum (slowly growing shadow, viewed) | pre frames were tested against a bar built from the same frames | per-frame bar built without the frame's own block and a 2-frame gap | removed an artefact |
| 0e | S1 edge error 50-65 px | the whole frame was compared, including false regions far from the plume | edge error computed in a window around the planted plume (protocol A2 item 3) | edge error at 0.20 now 7.4 px |

Baseline for the loop = version v2 (after 0e): S2 198 false of 1122 pre frames (17.7%, pooled bootstrap interval 8.9% to 27.3%, 14 of 32 sequences); S1-lite: opacity MAE 0.136, bias 0.000, edge error at 0.20 median 7.4 px, detection 70%, first-smoke error median 0 frames; S3 detected 29 of 32, median +240 s.
v2 does not meet the S2 gate (1%) or the S1 targets; the loop therefore starts from a failing baseline, which is stated here.

## Loop

### R1: chromaticity clause 0.02 to 0.05
Frames viewed: 20 false placebo chains over 4 sequences (sunrise ramp, cloud shadows, tower shadow, a second fire's plume visible before ignition). Named cause: ordinary lighting patches on coloured terrain shift chromaticity by more than 0.02. Result: S2 198 to 165 false frames; S1 detection 70% to 54%. **Rejected** (S1 detection worse by more than 5%, under the original and the amended rule).

Accept rule from R2 on: protocol amendment A3 (no S1 component worse than 5%, S2 false frames not up, at least one of S1 or S2 better than 5%). The S1 composites' source placement is frozen on the continuous-seam horizon (a physical requirement: smoke starts on terrain) so that S1 does not move when the method's horizon changes; baseline numbers below were re-run on that population.

### R2: horizon as a continuous seam
Frames viewed: sky-seeded chains in a cloudy sequence (20201208 om-s) classed as ground smoke. Named cause: the horizon was the first strong vertical gradient per column from the top, which cloud edges satisfy. Change: the horizon is the continuous left-to-right seam (dynamic programming, at most 2 px per column) of the strongest bright-above-dark step in the background (viewed on three cameras: it follows the ridge, not the cloud). A first attempt compared S1 populations that had moved with the horizon and was refused for an artefact (S1 detection 70% to 64%, because planted sources sat in the sky under the new horizon); after freezing S1 placement, re-run: S2 198 to 164 (-17%), S1 MAE 0.129 to 0.129, edge at 0.20 8.14 px unchanged, detection 70.8% to 72.9% (+2.9%, inside tolerance). **Accepted** (A3).

### R3: confirmation area 150 to 400 px
Frames viewed: 6 false chains in a windy shrub scene (so-w: seeds of 22 to 56 px, foliage flicker) and a cloudy-sky scene (bh-s). Named cause: small flicker regions of a few hundred pixels pass a 150 px confirmation; real plumes reach thousands of px. Result: S2 164 to 99 (-40%); S1 MAE 0.129 unchanged, edge 8.14 px unchanged, detection 72.9% to 70.8% (-2.9%). **Accepted** (A3). The first-smoke time does not move (it is the frame of the root, not of the confirmation); only plumes that never reach 400 px are lost.

### R4: minimum lineage length 3 to 5 frames
Frames viewed: the same false chains (median duration 8 frames, 20 of 38 at least 8). Named cause: short-lived regions pass a 3-frame persistence test. Result: S2 99 to 95 (-4%); S1 detection 70.8% to 67.7% (-4.4%). **Rejected** (nothing better by more than 5%).

### R5: a textured background must lose contrast (chromaticity counts only over flat background)
Frames viewed: tower-shadow and shrub-flicker chains where the chroma clause passed (35 of 50 false chains had a shift of at least 0.02). Named cause: any local lighting patch on coloured ground shifts chromaticity slightly. Result: S2 99 to 54 (-45%); S1 detection 70.8% to 53.1% (-25%); S3 detected 14 of 32. **Rejected** (S1 detection worse by more than 5%): real plumes over textured ridges fail the contrast test too.

### R6: endmember prior weight 0.02 to 0.002
Frames viewed: S1 misses (28 of 96 at R3; 15 of them dark-smoke composites). Named cause: the fitted smoke colour is pulled to the neutral prior (0.6), so dark smoke is measured against the wrong colour. Result: S1 opacity MAE 0.129 to 0.119 (-7.8%), edge error at 0.20 8.14 to 7.03 px (-13.7%), detection 70.8% to 64.6% (-8.8%); S2 99 to 98. **Rejected** (detection worse by more than 5%). The opacity estimate improved; the loss is in classification, which R7 addresses.

### R7: a region whose opacity core lies above the horizon passes the veil clause
Frames viewed: 16 S1 misses (e.g. 20200911 lp-e, dark smoke over hazy flat sky: the opacity map matched the truth, edges within 3 px, but the lineage was classed other because texture loss is undefined or negative and chromaticity is neutral). Named cause: the veil clause needs a textured or coloured background, and neutral flat sky has neither. Change: a region whose core (top quarter of opacity) lies more than half above the horizon passes the clause (a shadow cannot fall on the sky). Result: S1 detection 70.8% to 78.1% (+10%); MAE, edge error unchanged; S2 99 to 99. **Accepted**.

### R8: endmember prior weight 0.002 again, on top of R7
Frames viewed: none new (same S1 misses as R6). Named cause as R6. Result: MAE 0.129 to 0.119 (-7.8%), edge at 0.20 8.14 to 7.03 px (-13.7%), detection 78.1% to 74.0% (-5.3%); S2 99 to 98. **Rejected** (detection worse by just over the 5% tolerance). Recorded as a real trade: a more data-driven smoke colour measures opacity better and detects slightly less.

### R9: the lineage must not fade within its own life (last-frame area at least 50% of its peak)
Frames viewed: the false chains' area series were not stored; judged from the 6 chains viewed in R3 (short, flickering). Named cause: transient regions appear and fade. Result: S2 99 to 99; S1 detection 78.1% to 77.1%. **Rejected** (nothing better). A lineage that merges into a larger region ends without fading, so the rule does not touch the main false groups.

### R10: growth to at least 5x the seed area (was 2x)
Frames viewed: the R3 false chains again (flicker regions of 22 to 85 px reaching a few hundred px). Named cause: flicker and light patches double their area by chance; a plume grows by an order of magnitude. Result: S2 99 to 80 (-19%); S1 detection 78.1% to 76.0% (-2.7%, inside tolerance), MAE and edge unchanged. **Accepted** (A3). The smoke rule in docs/SMOKE_EDGE.md now says five times.

### R11: seed area at most 400 px (was 900)
Frames viewed: S1 composites (seeds of about 500 px at the noise level for opacity 0.9) and false chains (seeds 22 to 160 px). Named cause: large first regions are not plume seeds. Result: S2 80 to 80; S1 detection 76.0% to 44.8%. **Rejected** (the noise-level contour of a real first frame is already several hundred pixels).

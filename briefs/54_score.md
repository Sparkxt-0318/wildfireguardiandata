===== BRIEF 54: score (negatives, splits and the scoring contract). Run with: Sonnet, high effort. =====
Standing rules. No watermark or attribution lines in commits, pull requests or files. No hard stop: keep working until every step is done in depth. Use the folder "wildfire 3 (1)" on this Mac first (same as "wildfire 3" in the Drive folder "wildfireguardian"). Keys: before anything else, make sure the file "wildfire 3 (1)/keys/keys.env" exists and holds these lines (add any that are missing, change nothing else in it): HF_TOKEN=<REDACTED:HF_TOKEN> EARTHDATA_USERNAME=sparkxt EARTHDATA_TOKEN=<REDACTED:EARTHDATA_TOKEN> DATA_GO_KR_KEY=<REDACTED:DATA_GO_KR_KEY> Then read keys only from that file. The file stays on this Mac and outside the repo: Hugging Face and GitHub revoke tokens they find in a public repo, which would stop the run; never print, log or commit a key; if a key you need is missing, write its name in NEEDS.md at the repo root, carry on with everything that does not need it, and look again every hour. Save every raw download under "wildfire 3 (1)/firewitness_raw/" and add it to the folder's index. Do not ask me questions: decide, record the decision and its reason in DECISIONS.md, and continue.
Repo. Sparkxt-0318/wildfireguardiandata, created by prompt 49 (if missing, retry every 10 minutes for an hour, then create it). You own firewitness/score/ and the branch track/score.
Problem. Fire is about 0.1% of pixels, so how negatives are chosen and how a match is scored decides the result: random negatives and random splits inflate scores, tolerant matching changes F1 many-fold, and the top model by a threshold-free metric can flag many times the true area. Others have measured this. Build the fix.
Protocol first. protocol/SCORE_PROTOCOL.md, committed alone before any result.
Build three commands.

1. firewitness negatives sample. Negatives come only from "verified no fire" (prompt 50's three states; until that is merged, from a benchmark's own masks with everything else marked unknown). Each negative is matched to a positive on fire-danger class, land cover, region and season. A catalogue of hard negatives (hot places that are not wildfires) is included and flagged.
2. firewitness splits make. Splits blocked in space and time with a buffer, and by fire. The split files are published so everyone scores on the same ones.
3. firewitness score. A contract file states the unit, the match tolerance in space and time, and the threshold (fixed on validation, never on test). The score card always shows: precision, recall and F1 at the threshold; predicted area over true area; event-level detection and lead time; the same numbers for persistence and for climatology; cells excluded as unknown; results at three stated tolerances; and both a strict reading and one that uses the label's interval.

Gates: planted cheats must lose.

* N1: a model that memorises location scores no better than persistence under the blocked splits.
* N2: a model that flags everything loses on the card.
* N3: a model fed information from after the fire is caught by a leak check.
* N4: the same predictions give the same card in any order and on a re-run.
* N5: a simple model trained with the matched sampler does not over-predict in high-danger periods where the same model trained on random negatives does. This is a check of the tool, not a new survey.

Run it on one public spread benchmark with an adapter (no key needed; if only a keyed source works, write the key name in NEEDS.md and use another). Add an adapter for firewitness labels when prompts 50 and 51 are merged.
Improvement loop (after the first version passes, at most 8 rounds). Try to write a new cheat that wins under the contract; if it wins, fix the contract, keep the cheat as a test. Log in results/ROUNDS_score.md.
Deliver. The three commands, the split files, the contract template, docs/SCORING.md (two pages). results/SCORE_RESULTS.md with each gate's outcome and what it does not show. Do not re-verify the papers in my analysis.

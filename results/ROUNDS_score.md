# Improvement loop (track score)

Protocol: after the first version passes, try to write a new cheat that wins under the contract; if it wins, fix the contract and keep the cheat as a test. At most 8 rounds. Round 0 is the first run of the gates against the contract frozen in `protocol/SCORE_PROTOCOL.md` (commit dbce880).

## Round 0: first run (contract as pre-registered)
Synthetic benchmark (90 fires): N1 PASS, N2 PASS, N3 **FAIL**, N4 PASS, N5 PASS.
- N3 failure: the burn-scar cheat that lies about `info_until` scored AUC 0.952 on new-ignition cells, below the pre-registered `leak.auc` of 0.97, so the behavioural screen did not flag it. The next-day-label cheat (AUC 1.0) and the cheat that declared honestly were caught.
WildfireSpreadTS subset (56 fires): N1, N2, N3, N4 PASS; N5 **FAIL** (see results/SCORE_RESULTS.md: matched sampler cut top-danger over-prediction 6x versus random negatives, but the pre-registered absolute limit of 2.0x was not met).

## Round 1: leak screen limit
Change: `leak.auc` default 0.97 -> 0.90. Reason: honest models measured AUC 0.74 (real) and 0.77 (synthetic) on the same cells, so 0.90 keeps a margin of 0.13 above an honest model while catching the scar cheat (0.95). This is set after seeing one cheat, so it is a tuned limit; the docs say so. Kept as tests: `tests/score/test_gates.py::test_n3_*`.
Outcome: synthetic N3 now PASS.

## Round 2: a cheat that won (front peek)
Cheat `models.leaky_front`: uses today's label only within 3 cells of yesterday's fire (persistence elsewhere) and declares `info_until` = issue day. It **won**: strict F1 0.9996 (synthetic) and 0.926 (WildfireSpreadTS subset) against persistence 0.675 and 0.644, and the round-1 leak check passed it because the behavioural screen only looked at cells far from any fire.
Fix: second behavioural screen on the ring within `radius_cells` of the previous day's fire (cells newly burning vs cells not burning). Honest models measured front AUC 0.57-0.82 (synthetic) and 0.64-0.80 (real); the cheat 1.000. New contract field `leak.front_auc` = 0.95. Kept as `tests/score/test_gates.py::test_round2_*` and inside gate N3.

## Round 3: tolerance gaming (halo)
Cheat `models.halo`: persistence thickened by 2 cells, to profit from tolerant matching. It did **not** win: it loses to persistence at the strict tolerance and its predicted-area ratio is larger, which the card shows. At the loose tolerance it ties persistence (both near 1.0), which is why the card always lists all three tolerances. No contract change. Kept as test.

## Round 4: training on test fires
Cheat: a model fitted on every fire, test included. The card cannot see this from the predictions alone, so a model may declare `trained_on_fires` in the predictions meta; overlap with the test fold now fails the card and prints a warning. A model that does not declare it gets "not declared". Limit: a dishonest declaration is not caught (docs say so). Kept as test.

## Round 5: silent on fire-free days
Cheat `models.abstain_cheat`: persistence, but silent on days it secretly knows no fire burns. Result on the 12-fire early subset: +0.014 strict F1 over persistence (CI excludes zero); on synthetic no difference. **Not caught**: it changes which days are scored, not cell scores, and no screen on cell scores or declared dates can see it. No contract change possible without labels from the future; documented as a limit in docs/SCORING.md and SCORE_RESULTS.md.

## Round 6: N5 on the full 168-fire subset
Re-ran all gates on 168 fires. N5 still fails the pre-registered limit (matched 10.7x vs random 7.1x at the validation threshold). Decision: no change to the limit or the model after seeing it; the result is reported as a FAIL with the raw-probability reading (6.8x vs 53.7x) alongside. The loop is stopped here: rounds 7-8 were not needed because no further cheat I could construct from the declared interfaces was found that the contract could still catch (the remaining ones need information the scorer does not have). Total rounds used: 6 of 8.

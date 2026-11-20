# Improvement loop (track score)

Protocol: after the first version passes, try to write a new cheat that wins under the contract; if it wins, fix the contract and keep the cheat as a test. At most 8 rounds. Round 0 is the first run of the gates against the contract frozen in `protocol/SCORE_PROTOCOL.md` (commit dbce880).

## Round 0: first run (contract as pre-registered)
Synthetic benchmark (90 fires): N1 PASS, N2 PASS, N3 **FAIL**, N4 PASS, N5 PASS.
- N3 failure: the burn-scar cheat that lies about `info_until` scored AUC 0.952 on new-ignition cells, below the pre-registered `leak.auc` of 0.97, so the behavioural screen did not flag it. The next-day-label cheat (AUC 1.0) and the cheat that declared honestly were caught.
WildfireSpreadTS subset (56 fires): N1, N2, N3, N4 PASS; N5 **FAIL** (see results/SCORE_RESULTS.md: matched sampler cut top-danger over-prediction 6x versus random negatives, but the pre-registered absolute limit of 2.0x was not met).

## Round 1: leak screen limit
Change: `leak.auc` default 0.97 -> 0.90. Reason: honest models measured AUC 0.74 (real) and 0.77 (synthetic) on the same cells, so 0.90 keeps a margin of 0.13 above an honest model while catching the scar cheat (0.95). This is set after seeing one cheat, so it is a tuned limit; the docs say so. Kept as tests: `tests/score/test_gates.py::test_n3_*`.
Outcome: see below as rounds proceed.

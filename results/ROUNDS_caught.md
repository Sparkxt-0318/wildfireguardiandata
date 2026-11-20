# ROUNDS: caught (track 50)

Dev data only: S1 (California 2020) dev records (sha256(FOD_ID) mod 10 in 0-2), their matched placebos, and the
dev truth fires (sha256(source id) mod 10 in 0-2, US 2018-2020). The sealed truth split is not read until the rules
are frozen.

## Metrics and keep rule (written before the v1 truth numbers were seen)

* **Catches**: (a) dev truth fires of the primary small stratum labelled verified or probable where the label meets
  the polygon; (b) the verified ones among (a); (c) dev records with no standard label that reach verified (the
  headline on dev).
* **Placebo rates**: share of searched dev placebos reaching verified, and reaching probable.
* **Before the loop** ("after the first version passes"): version 1 must pass on dev: verified placebo rate <= 1 %
  (C1), probable placebo rate <= 5 % (this track's guard), labelled-recall above the standard label's on dev truth.
  Fixes made to get there are listed below as development fixes, each with its cause, whatever they do to catches.
* **Loop rounds** (at most 12): one named cause per round, from reading every miss and every placebo hit. A change
  is kept only if catches (a) or (c) rise and neither placebo rate rises; otherwise it is reverted.

## Version 1 on dev

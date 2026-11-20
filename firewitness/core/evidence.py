"""Evidence combination: independent sources as witnesses of a hidden truth.

Each witness reports agree / disagree / unknown for one hypothesis ("these two records are the same
fire", "this repaired location is right"). A witness has m = P(agree | hypothesis true) and
u = P(agree | hypothesis false). Under conditional independence the log-likelihood ratios add
(Fellegi-Sunter). The result is a probability and a decision: "yes", "no", or "undecided" when the
posterior sits between the two thresholds (the sources cannot settle it).

m and u may be given or fitted WITHOUT labels by EM (fit_witnesses).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

EPS = 1e-6


@dataclass(frozen=True)
class Witness:
    name: str
    m: float  # P(agree | true)
    u: float  # P(agree | false)

    def log_lr(self, obs: bool | None) -> float:
        if obs is None:
            return 0.0
        m = min(max(self.m, EPS), 1 - EPS)
        u = min(max(self.u, EPS), 1 - EPS)
        return math.log(m / u) if obs else math.log((1 - m) / (1 - u))


@dataclass
class Verdict:
    prob: float
    decision: str  # "yes" | "no" | "undecided"
    log_odds: float
    contributions: dict = field(default_factory=dict)

    def __iter__(self):
        yield self.prob
        yield self.decision


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def combine(witnesses: Sequence[Witness], observations: Mapping[str, bool | None] | Sequence[bool | None],
            prior: float = 0.5, hi: float = 0.95, lo: float = 0.05) -> Verdict:
    """Posterior probability the hypothesis is true, and a decision.

    observations: {witness name: True/False/None} or a sequence aligned to witnesses.
    Decision: prob >= hi -> yes; prob <= lo -> no; else undecided. With no informative witness the
    answer is always undecided unless the prior itself is outside (lo, hi).
    """
    prior = min(max(prior, EPS), 1 - EPS)
    obs = (observations if isinstance(observations, Mapping)
           else dict(zip((w.name for w in witnesses), observations)))
    lo_odds = math.log(prior / (1 - prior))
    contrib = {}
    for w in witnesses:
        c = w.log_lr(obs.get(w.name))
        contrib[w.name] = c
        lo_odds += c
    p = _sigmoid(lo_odds)
    dec = "yes" if p >= hi else "no" if p <= lo else "undecided"
    return Verdict(p, dec, lo_odds, contrib)


def fit_witnesses(patterns: Sequence[Sequence[bool | None]], names: Sequence[str],
                  init_prior: float = 0.1, iters: int = 200, tol: float = 1e-8,
                  m0: float = 0.9, u0: float = 0.1) -> tuple[list[Witness], float]:
    """Fit m, u and the prior by EM from unlabeled comparison vectors (rows of agree/disagree/None).

    Returns (witnesses, prior). Label switching is prevented by initialising m > u and keeping m >= u.
    """
    k = len(names)
    m = [m0] * k
    u = [u0] * k
    pi = init_prior
    n = len(patterns)
    if n == 0:
        return [Witness(nm, m0, u0) for nm in names], pi
    for _ in range(iters):
        # E step
        gam = []
        for row in patterns:
            lt = math.log(pi)
            lf = math.log(1 - pi)
            for j, o in enumerate(row):
                if o is None:
                    continue
                mj = min(max(m[j], EPS), 1 - EPS)
                uj = min(max(u[j], EPS), 1 - EPS)
                lt += math.log(mj if o else 1 - mj)
                lf += math.log(uj if o else 1 - uj)
            mx = max(lt, lf)
            g = math.exp(lt - mx) / (math.exp(lt - mx) + math.exp(lf - mx))
            gam.append(g)
        # M step
        new_pi = min(max(sum(gam) / n, 1e-6), 1 - 1e-6)
        nm, nu = [], []
        for j in range(k):
            num_m = den_m = num_u = den_u = 0.0
            for g, row in zip(gam, patterns):
                o = row[j]
                if o is None:
                    continue
                den_m += g
                den_u += 1 - g
                if o:
                    num_m += g
                    num_u += 1 - g
            mj = (num_m + 0.5) / (den_m + 1.0)
            uj = (num_u + 0.5) / (den_u + 1.0)
            if uj > mj:  # keep orientation
                mj, uj = uj, mj
            nm.append(mj)
            nu.append(uj)
        delta = max(abs(new_pi - pi), *(abs(a - b) for a, b in zip(nm, m)), *(abs(a - b) for a, b in zip(nu, u)))
        m, u, pi = nm, nu, new_pi
        if delta < tol:
            break
    return [Witness(nm_, m[j], u[j]) for j, nm_ in enumerate(names)], pi

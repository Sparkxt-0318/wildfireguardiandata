"""Vectorised unlabeled fitting of witness reliabilities (same model as core.evidence.fit_witnesses_grouped)."""
from __future__ import annotations

import numpy as np

from ..core import Witness

EPS = 1e-6


def fit_grouped(obs: np.ndarray, group: np.ndarray, names, init_priors: dict | None = None, iters: int = 300,
                tol: float = 1e-9, m0: float = 0.9, u0: float = 0.1, weights: np.ndarray | None = None,
                fixed: dict | None = None):
    """obs: (n, k) int8 with 1 agree, 0 disagree, -1 unknown. group: (n,) ints. Returns (witnesses, {group: prior}).

    Orientation is enforced (m >= u) so labels cannot switch.
    """
    obs = np.asarray(obs)
    n, k = obs.shape
    groups = np.unique(group)
    fixed = fixed or {}
    pri = np.array([fixed.get(int(g), (init_priors or {}).get(int(g), 0.5)) for g in groups])
    gi = np.searchsorted(groups, group)
    m = np.full(k, m0)
    u = np.full(k, u0)
    w = np.ones(n) if weights is None else weights
    known = obs >= 0
    agree = (obs == 1)
    for _ in range(iters):
        mm, uu = np.clip(m, EPS, 1 - EPS), np.clip(u, EPS, 1 - EPS)
        lt = np.log(np.clip(pri[gi], EPS, 1 - EPS))
        lf = np.log(1 - np.clip(pri[gi], EPS, 1 - EPS))
        lt = lt + (known * np.where(agree, np.log(mm), np.log(1 - mm))).sum(1)
        lf = lf + (known * np.where(agree, np.log(uu), np.log(1 - uu))).sum(1)
        mx = np.maximum(lt, lf)
        g = np.exp(lt - mx) / (np.exp(lt - mx) + np.exp(lf - mx))
        newpri = np.array([fixed[int(groups[i])] if int(groups[i]) in fixed else
                           np.clip((g[gi == i] * w[gi == i]).sum() / max(w[gi == i].sum(), 1e-9), 1e-6, 1 - 1e-6)
                           for i in range(len(groups))])
        gw = (g * w)[:, None]
        nw = ((1 - g) * w)[:, None]
        num_m = (gw * agree * known).sum(0)
        den_m = (gw * known).sum(0)
        num_u = (nw * agree * known).sum(0)
        den_u = (nw * known).sum(0)
        nm = (num_m + 0.5) / (den_m + 1.0)
        nu = (num_u + 0.5) / (den_u + 1.0)
        swap = nu > nm
        nm, nu = np.where(swap, nu, nm), np.where(swap, nm, nu)
        delta = max(np.abs(newpri - pri).max(), np.abs(nm - m).max(), np.abs(nu - u).max())
        m, u, pri = nm, nu, newpri
        if delta < tol:
            break
    return [Witness(nm_, float(m[j]), float(u[j])) for j, nm_ in enumerate(names)], {int(gr): float(p) for gr, p in zip(groups, pri)}


def posterior(obs: np.ndarray, witnesses, prior: np.ndarray) -> np.ndarray:
    """Posterior P(true) for each row given witnesses and per-row prior (conditional independence)."""
    m = np.clip([w.m for w in witnesses], EPS, 1 - EPS)
    u = np.clip([w.u for w in witnesses], EPS, 1 - EPS)
    known = obs >= 0
    agree = obs == 1
    llr = known * np.where(agree, np.log(m / u), np.log((1 - m) / (1 - u)))
    pr = np.clip(prior, EPS, 1 - EPS)
    lo = np.log(pr / (1 - pr)) + llr.sum(1)
    return 1.0 / (1.0 + np.exp(-np.clip(lo, -50, 50)))

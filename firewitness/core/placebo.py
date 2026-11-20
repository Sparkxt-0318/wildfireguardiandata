"""Placebo-test helper and cluster bootstrap.

A placebo test asks: would the same procedure "find" this much agreement on data where the true link
is destroyed? placebo_test() runs the statistic on the real data and on n perturbed copies.
"""
from __future__ import annotations

import random
from typing import Any, Callable, Hashable, Sequence


def placebo_test(statistic: Callable[[Any], float], data: Any, perturb: Callable[[Any, random.Random], Any],
                 n: int = 200, seed: int = 0, larger_is_better: bool = True) -> dict:
    """statistic(data) vs statistic(perturb(data, rng)) repeated n times.

    Returns {real, placebo_mean, placebo_sd, p (one-sided, add-one), placebo: [...]}.
    """
    rng = random.Random(seed)
    real = float(statistic(data))
    plc = [float(statistic(perturb(data, rng))) for _ in range(n)]
    more = sum((x >= real) if larger_is_better else (x <= real) for x in plc)
    mean = sum(plc) / len(plc) if plc else float("nan")
    sd = (sum((x - mean) ** 2 for x in plc) / max(len(plc) - 1, 1)) ** 0.5 if plc else float("nan")
    return {"real": real, "placebo_mean": mean, "placebo_sd": sd, "p": (more + 1) / (n + 1),
            "n": n, "placebo": plc}


def shuffle_column(rows: Sequence[dict], column: str, rng: random.Random) -> list[dict]:
    """Perturbation: shuffle one column across rows (destroys its relation to everything else)."""
    vals = [r[column] for r in rows]
    rng.shuffle(vals)
    return [{**r, column: v} for r, v in zip(rows, vals)]


def cluster_bootstrap(items: Sequence[Any], cluster: Callable[[Any], Hashable],
                      statistic: Callable[[Sequence[Any]], float], n: int = 1000, seed: int = 0,
                      alpha: float = 0.05) -> dict:
    """Bootstrap resampling whole clusters (e.g. state-year). Returns estimate and percentile interval."""
    groups: dict[Hashable, list] = {}
    for it in items:
        groups.setdefault(cluster(it), []).append(it)
    keys = list(groups)
    rng = random.Random(seed)
    stats = []
    for _ in range(n):
        samp: list = []
        for _k in keys:
            samp.extend(groups[rng.choice(keys)])
        stats.append(statistic(samp))
    stats.sort()
    lo = stats[int((alpha / 2) * (n - 1))]
    hi = stats[int((1 - alpha / 2) * (n - 1))]
    return {"estimate": statistic(list(items)), "lo": lo, "hi": hi, "n_clusters": len(keys), "n_boot": n}


def paired_cluster_bootstrap(items: Sequence[Any], cluster: Callable[[Any], Hashable],
                             stat_a: Callable[[Sequence[Any]], float],
                             stat_b: Callable[[Sequence[Any]], float], n: int = 1000, seed: int = 0,
                             alpha: float = 0.05) -> dict:
    """Interval for stat_a - stat_b on the same resamples (e.g. F1 of ours minus F1 of best fixed rule)."""
    res = cluster_bootstrap(items, cluster, lambda s: stat_a(s) - stat_b(s), n, seed, alpha)
    res["excludes_zero"] = interval_excludes_zero(res)
    return res


def interval_excludes_zero(res: dict) -> bool:
    return res["lo"] > 0 or res["hi"] < 0

"""Development loop helper (protocol section 9): run the agent on the dev areas, grade against dev plots, save numbers."""
from __future__ import annotations
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import grade, runner
from .areas import DEV

RESULTS = Path(__file__).resolve().parents[2] / "results" / "fuel"   # data files; the write-ups stay in results/


def run_dev(label: str, map_key: str = "M22", tiles=None, save=True):
    tiles = tiles or DEV
    cfg = runner.region_cfg()
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(lambda t: runner.run_area(t, map_key, cfg), tiles))
    out, df = grade.evaluate(tiles, map_key, label)
    out["code_hash"] = runner.code_hash()
    out["map"] = map_key
    if save:
        RESULTS.mkdir(exist_ok=True)
        (RESULTS / f"dev_{label}_{map_key}.json").write_text(json.dumps(out, indent=1, default=str))
        df.to_pickle(runner.OUT_ROOT / f"dev_{label}_{map_key}_plots.pkl")
    return out, df


def brief(out) -> str:
    f1, f2, fs = out["F1"], out["F2"], out["F1_stale"]
    return (f"plots {out['n_plots']}  verdicts {out['verdict_counts']}\n"
            f"F1 ratio {f1['ratio']:.2f} [{f1['lo']:.2f},{f1['hi']:.2f}] n_c={f1['n_a']} (dis {f1['rate_a']:.2f}) n_k={f1['n_b']} (dis {f1['rate_b']:.3f}) "
            f"evaluable={f1['evaluable']} pass={f1['passed']}\n"
            f"F2 share {f2['share']:.3f} wilson_hi {f2['wilson_hi']:.3f} (n_agree {f2['n_agree']}) pass={f2['passed']}\n"
            f"stale/consistent ratio {fs['ratio']:.2f} [{fs['lo']:.2f},{fs['hi']:.2f}] n_s={fs['n_a']}")


if __name__ == "__main__":
    label = sys.argv[1]
    mk = sys.argv[2] if len(sys.argv) > 2 else "M22"
    o, _ = run_dev(label, mk)
    print(brief(o))

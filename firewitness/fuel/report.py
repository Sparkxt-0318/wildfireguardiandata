"""Evidence cards, map and Markdown report for an agent run."""
from __future__ import annotations
from pathlib import Path

import numpy as np

from . import agent
from .layers import Layers

NLCD_NAMES = {11: "open water", 12: "perennial ice/snow", 21: "developed open", 22: "developed low", 23: "developed medium",
              24: "developed high", 31: "barren", 41: "deciduous forest", 42: "evergreen forest", 43: "mixed forest",
              52: "shrub/scrub", 71: "grassland", 81: "pasture/hay", 82: "cultivated crops", 90: "woody wetlands",
              95: "emergent wetlands"}
RULE_TEXT = {
    "R1.1": "timber class with no canopy in the independent layers",
    "R1.2": "grass/shrub class under dense tall forest in all four independent layers",
    "R1.3": "burnable class on open water", "R1.4": "burnable class on snow/ice", "R1.5": "burnable class on pavement/built",
    "R1.6": "burnable class on bare ground", "R1.7": "unburnable class on natural vegetation",
    "R1.9": "grass/shrub lifeform contradicted by NLCD and WorldCover",
    "S1": "wildfire perimeter after the map year", "S2": "tree-cover loss after the map year (Hansen)",
    "R3a": "burned (perimeter + LANDFIRE disturbance) although labelled unburnable",
    "R3b": "observed spread faster than the class can produce", "U0": "no or unmapped fuel class",
}


def rules_fired(mask: int):
    return [agent.BIT_RULES[b] for b in range(13) if (int(mask) >> b) & 1]


def card(L: Layers, res: agent.Result, r: int, c: int, cfg: dict) -> dict:
    """Evidence card for one cell: every value a rule looked at, the rules that fired and the thresholds crossed."""
    ind = cfg["indicators"]
    fired = rules_fired(res.rules[r, c])
    x = L.grid.xmin + (c + 0.5) * 30.0
    y = L.grid.ymax - (r + 0.5) * 30.0
    d = {
        "cell": {"row": int(r), "col": int(c), "x_5070": x, "y_5070": y},
        "verdict": agent.VERDICT_NAMES[int(res.verdict[r, c])],
        "map_class": int(L.fbfm[r, c]),
        "map_group": agent.GROUP_NAMES.get(int(res.group[r, c]), "none"),
        "rules_fired": [{"id": k, "meaning": RULE_TEXT[k]} for k in fired],
        "tree_evidence": {"S": int(res.S[r, c]), "layers_available": int(res.n[r, c])},
        "layers": {
            "nlcd2021": f"{int(L.lc[r, c])} ({NLCD_NAMES.get(int(L.lc[r, c]), '?')})",
            "tcc2021_percent": int(L.tcc[r, c]) if L.tcc[r, c] <= 100 else None,
            "canopy_max_m": int(L.chm_max[r, c]) if L.chm_max[r, c] != 255 else None,
            "canopy_share_ge3m_percent": int(L.chm_cov[r, c]) if L.chm_cov[r, c] != 255 else None,
            "worldcover_percent": {k: int(v[r, c]) for k, v in L.wc.items() if v[r, c] not in (0, 255)},
            "hansen_tree_cover_2000": int(L.tc2000[r, c]), "hansen_loss_year": int(L.loss_year[r, c]) or None,
            "wildfire_perimeter_year_after_map": int(L.post_fire_year[r, c]) or None,
            "map_year": L.map_year,
        },
        "thresholds": {"tcc_tree>=": ind["tcc_tree"], "tcc_none<=": ind["tcc_none"], "wc_tree>=": ind["wc_tree"],
                       "canopy_max_tree>=": ind["chm_max_tree"]},
        "suggested_class": int(res.suggest[r, c]) or None,
        "suggested_group": agent.GROUP_NAMES.get(int(res.sgroup[r, c])),
    }
    return d


def card_text(d: dict) -> str:
    lines = [f"Cell ({d['cell']['row']},{d['cell']['col']})  verdict: {d['verdict'].upper()}  map class {d['map_class']} ({d['map_group']})"]
    for r in d["rules_fired"]:
        lines.append(f"  rule {r['id']}: {r['meaning']}")
    t = d["tree_evidence"]
    lines.append(f"  tree evidence score {t['S']} from {t['layers_available']} independent layers")
    for k, v in d["layers"].items():
        lines.append(f"  {k}: {v}")
    if d["suggested_class"] or d["suggested_group"]:
        lines.append(f"  suggestion: class {d['suggested_class']} group {d['suggested_group']}")
    return "\n".join(lines)


def map_png(res: agent.Result, path: Path, title: str = "", step: int = 4):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    v = res.verdict[::step, ::step]
    cmap = ListedColormap(["#ffffff", "#2e7d32", "#f9a825", "#c62828", "#9e9e9e"])
    fig, ax = plt.subplots(figsize=(7, 7), dpi=120)
    ax.imshow(v, cmap=cmap, vmin=0, vmax=4, interpolation="nearest")
    ax.set_title(title or "fuel-map verdicts")
    ax.axis("off")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, label=n) for c, n in zip(["#2e7d32", "#f9a825", "#c62828", "#9e9e9e"],
              ["consistent", "stale", "contradicted", "unknown"])], loc="lower left", fontsize=8)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def report_md(name: str, map_key: str, manifest: dict, examples: list[str]) -> str:
    cnt = manifest["counts"]
    tot = sum(cnt.values())
    lines = [f"# Fuel-map check: {name} ({map_key})", "",
             f"Code {manifest['code_version']} / rules hash `{manifest['code_hash'][:12]}`; config hash `{manifest['config_hash'][:12]}`.",
             "Source map untouched (input hashes before and after are identical; see overlay.json).", "",
             "| verdict | cells | share |", "|---|---|---|"]
    for k, v in cnt.items():
        lines.append(f"| {k} | {v} | {100 * v / max(tot, 1):.1f} % |")
    lines += ["", "| rule | cells |", "|---|---|"]
    for k, v in manifest["rule_counts"].items():
        if v:
            lines.append(f"| {k} {RULE_TEXT.get(k, '')} | {v} |")
    lines += ["", f"Cells with a suggested class: {manifest['suggestions']}.", "", "## Evidence cards (examples)", ""]
    for e in examples:
        lines += ["```", e, "```", ""]
    lines += ["A verdict is a statement about agreement between the map and independent public layers, not a field measurement."]
    return "\n".join(lines) + "\n"


def write_report(name: str, map_key: str, cfg: dict, manifest: dict, out: Path):
    """Map PNG + Markdown report with evidence-card examples for one run. Recomputes verdicts from the layers (deterministic)."""
    from .areas import area_dir
    from .layers import load
    L = load(area_dir(name), map_key, cfg, cutoff_year=manifest.get("event_cutoff_year"))
    res = agent.check(L, cfg)
    map_png(res, Path(out) / "map.png", f"{name} {map_key}")
    rows, cols = np.nonzero(res.verdict == agent.CONTRADICTED)
    pick = np.linspace(0, len(rows) - 1, min(5, len(rows))).astype(int) if len(rows) else []
    examples = [card_text(card(L, res, int(rows[i]), int(cols[i]), cfg)) for i in pick]
    (Path(out) / "report.md").write_text(report_md(name, map_key, manifest, examples))

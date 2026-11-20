"""Smoke opacity, regions, first-smoke trace and class rules.
Image credit: HPWREN, http://hpwren.ucsd.edu/. No trained model is used anywhere."""
from __future__ import annotations
import numpy as np
import cv2
from . import core, seq
from .core import H, W, BAN, VALID, lum, smooth
from .params import get as get_params, cfg_hash

cv2.setNumThreads(1)
CLASSES = ["none", "smoke", "cloud", "haze_fog", "dust", "other"]

RULES = {
    "smoke": "A region above the noise level that is linked back through the frames to a small seed on or just above the ground, has grown since the seed, and (where the background has texture) has lost at least 15% of its relative contrast or shifted the background chromaticity by at least 0.02 (a shadow does neither), is smoke.",
    "cloud": "A region above the noise level that lies mostly above the horizon, has no seed on the ground and drifts slowly is cloud.",
    "haze_fog": "A region at the lowest opacity band (below 0.15) that covers more than 15% of the frame and has no seed is haze or fog.",
    "dust": "A region with a warm colour shift above 0.04 that has no seed growth into a plume (it does not reach twice its seed area) is dust.",
    "other": "Any region above the noise level that matches none of the rules above is other (lighting change, moving object, lens artefact).",
}


# ---------------------------------------------------------------- preparation
def prepare(sq, params=None, pre_idx=None):
    """Background, lighting correction, endmember, noise floor, opacity maps for every frame."""
    p = params or get_params()
    fr = sq["frames"].astype(np.float32) / 255.0
    off = sq["offsets"]
    T = len(fr)
    info = dict(name=sq.get("name", ""), n_frames=int(T), excluded=None, notes=[])
    if pre_idx is None:
        pre_idx = np.where((off <= p["pre_end_offset"]) & (off >= p["pre_start_offset"]))[0]
    pre_idx = np.asarray(pre_idx)
    if T < p["min_frames"]:
        info["excluded"] = "fewer than %d frames" % p["min_frames"]
    elif len(pre_idx) < p["min_pre_frames"]:
        info["excluded"] = "fewer than %d pre-ignition frames" % p["min_pre_frames"]
    if info["excluded"]:
        return dict(info=info, params=p)
    # registration to the pre-window median
    gray = np.stack([lum(f) for f in fr])
    ref = np.median(gray[pre_idx], axis=0)
    shifts = np.array([core.estimate_shift(ref, g)[:2] for g in gray])
    mag = np.hypot(shifts[:, 0], shifts[:, 1])
    info["max_pre_shift"] = float(mag[pre_idx].max())
    info["median_pre_luminance"] = float(np.median(gray[pre_idx][:, BAN:H - BAN]))
    if info["max_pre_shift"] > p["max_shift_px"]:
        info["excluded"] = "moving camera: pre-window shift %.1f px" % info["max_pre_shift"]
    elif info["median_pre_luminance"] < p["min_luminance"]:
        info["excluded"] = "night: median luminance %.2f" % info["median_pre_luminance"]
    if info["excluded"]:
        return dict(info=info, params=p)
    for i in range(T):
        if mag[i] > p["apply_shift_above"]:
            fr[i] = core.shift_image(fr[i], *shifts[i])
    info["max_shift_all"] = float(mag.max())
    sg = p["smooth_sigma"]
    B = core.build_background(fr, pre_idx)
    Bs = smooth(B, sg)
    # lighting-corrected, smoothed frames and differences
    post = np.array([i for i in range(T) if i not in set(pre_idx.tolist())])
    d = np.zeros((T, H, W, 3), np.float32)
    for i in post:
        n, _, _ = core.normalise(fr[i], B)
        d[i] = smooth(n, sg) - Bs
    # null: pre frames against a background that excludes their block and a gap
    nb, gap = p["null_block"], p["null_gap"]
    dnull = {}
    Bnull_s = {}
    for k in range(0, len(pre_idx), nb):
        blk = pre_idx[k:k + nb]
        lo, hi = blk[0] - gap, blk[-1] + gap
        rest = np.array([i for i in pre_idx if i < lo or i > hi])
        if len(rest) < 8:
            rest = np.array([i for i in pre_idx if i not in set(blk.tolist())])
        Bk = core.build_background(fr, rest)
        Bks = smooth(Bk, sg)
        for i in blk:
            n, _, _ = core.normalise(fr[i], Bk)
            d[i] = smooth(n, sg) - Bks
            Bnull_s[i] = Bks
    # endmember from the strongest changed frames among post frames
    nn = np.linalg.norm(d[pre_idx], axis=3)[:, BAN:H - BAN]
    tau_d = float(np.quantile(nn, p["null_quantile"]))
    cand = []
    for i in post:
        m = (np.linalg.norm(d[i], axis=2) >= tau_d) & VALID
        cand.append((int(m.sum()), int(i)))
    cand.sort(reverse=True)
    top = [i for c, i in cand[:6] if c >= p["support_min_px"]]
    S, ok = core.estimate_endmember([d[i] for i in top], Bs, p, tau_d) if top else (np.full(3, p["endmember_prior"]), False)
    # opacity maps
    alpha = np.zeros((T, H, W), np.float32)
    for i in range(T):
        Bi = Bnull_s.get(i, Bs)
        alpha[i] = core.opacity(d[i], Bi, S, p) if ok else core.default_endmember_alpha(d[i], Bi, p)
        alpha[i][~VALID] = 0
    null = alpha[pre_idx][:, BAN:H - BAN]
    # horizon from the background (needed for the noise pool and the seed rule)
    horizon = horizon_line_gradient(Bs) if p.get("horizon_method") == "gradient" else horizon_line(Bs)
    # camera noise floor: the null opacity on the ground below the horizon (sensor, compression, shimmer, shadows).
    # Sky pixels are excluded from the pool: clouds there are real changes, handled by the class rules.
    rows = np.arange(H)[:, None]
    ground = (rows >= horizon[None, :] + p["horizon_tol"]) & VALID
    # Camera noise. N(x) = the largest opacity pixel x showed while smoke-free (5x5 spatial max).
    # L0 = the median of N over valid pixels: the noise level of a typical pixel. A pixel counts as "above the
    # noise level" when its opacity reaches T(x) = max(L0, N(x)): specular glints, moving foliage and cloud or
    # shadow passages seen in the pre window raise the bar at their own pixels only.
    Nmap = cv2.dilate(np.max(alpha[pre_idx], axis=0), np.ones((5, 5), np.uint8))
    L0 = max(float(np.median(Nmap[VALID])), p["noise_floor_min"])
    Tmap = np.maximum(L0, Nmap).astype(np.float32)
    noisy = Nmap > L0
    # per-frame bar: pre-window frames are tested against a bar built without their own block and gap, so that
    # a frame is never compared with a maximum it helped to set (a slowly growing shadow would pass otherwise)
    T_of = {}
    for k in range(0, len(pre_idx), nb):
        blk = pre_idx[k:k + nb]
        lo, hi = blk[0] - gap, blk[-1] + gap
        rest = np.array([i for i in pre_idx if i < lo or i > hi])
        if len(rest) < 8:
            rest = np.array([i for i in pre_idx if i not in set(blk.tolist())])
        Nk = cv2.dilate(np.max(alpha[rest], axis=0), np.ones((5, 5), np.uint8))
        Tk = np.maximum(L0, Nk).astype(np.float32)
        for i in blk:
            T_of[int(i)] = Tk
    T_frames = [T_of.get(i, Tmap) for i in range(T)]
    info["masked_share"] = float(noisy[VALID].mean())
    # horizon from the background
    return dict(info=info, params=p, offsets=off, pre_idx=pre_idx, B=B, Bs=Bs, d=d, alpha=alpha,
                S=S, S_fitted=bool(ok), L0=L0, T=Tmap, T_frames=T_frames, tau_d=tau_d, horizon=horizon, frames=fr, shifts=shifts, noisy=noisy)


def texture_loss_map(prep, t):
    """1 - (relative contrast of the frame / relative contrast of the background); nan where the background is flat."""
    from .vector import _grad_energy
    n, _, _ = core.normalise(prep["frames"][t], prep["B"])
    Is = smooth(n, prep["params"]["smooth_sigma"]); Bs = prep["Bs"]
    yi, yb = lum(Is), lum(Bs)
    ci = _grad_energy(yi) / (cv2.GaussianBlur(yi, (0, 0), 4) + 0.03)
    cb = _grad_energy(yb) / (cv2.GaussianBlur(yb, (0, 0), 4) + 0.03)
    return np.where(cb > 0.02, 1.0 - ci / np.maximum(cb, 1e-4), np.nan).astype(np.float32)


def horizon_line_gradient(Bs):
    """v0 rule: first strong vertical gradient per column from the top (fooled by cloud edges); kept for the loop record."""
    y = smooth(lum(Bs), 3)
    gy = np.abs(np.diff(y, axis=0)); gy[:20] = 0; gy[H - 30:] = 0
    first = np.where((gy > 0.02).any(0), (gy > 0.02).argmax(0), H // 2)
    return np.convolve(np.pad(first.astype(np.float32), 20, mode="edge"), np.ones(41) / 41, "valid")


def horizon_line(Bs, band=6, penalty=0.01):
    """Row of the terrain/sky boundary per column: the continuous left-to-right seam (dynamic programming, at most
    2 px step per column) that follows the strongest bright-above-dark-below step of the background luminance.
    A continuous seam is not fooled by the edges of clouds, which are local."""
    y = smooth(lum(Bs), 2)
    cs = np.cumsum(np.pad(y, ((1, 0), (0, 0)), mode="edge"), axis=0)
    r = np.arange(H)
    above = (cs[r] - cs[np.clip(r - band, 0, H)]) / np.maximum(r - np.clip(r - band, 0, H), 1)[:, None]
    below = (cs[np.clip(r + band + 1, 0, H)] - cs[r + 1]) / np.maximum(np.clip(r + band + 1, 0, H) - (r + 1), 1)[:, None]
    step = above - below                       # (H, W): positive where bright sits above dark
    step[:BAN + band] = 0; step[H - BAN - band:] = 0
    cost = -step
    acc = np.zeros_like(cost); acc[:, 0] = cost[:, 0]
    back = np.zeros((H, W), np.int16)
    for x in range(1, W):
        prev = acc[:, x - 1]
        best = prev.copy(); arg = np.arange(H)
        for d in (1, 2):
            for sgn in (-1, 1):
                sh = np.roll(prev, sgn * d)
                if sgn == 1:
                    sh[:d] = np.inf
                else:
                    sh[-d:] = np.inf
                cand = sh + penalty * d
                better = cand < best
                best = np.where(better, cand, best); arg = np.where(better, (np.arange(H) - sgn * d), arg)
        acc[:, x] = best + cost[:, x]; back[:, x] = arg
    row = np.empty(W, np.int32); row[-1] = int(np.argmin(acc[:, -1]))
    for x in range(W - 1, 0, -1):
        row[x - 1] = back[row[x], x]
    return row.astype(np.float32)


# ---------------------------------------------------------------- regions
def regions(alpha_t, T, area_min):
    """connected pixels with alpha at or above the bar T(x)"""
    m = (alpha_t >= T).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = [k for k in range(1, n) if st[k, cv2.CC_STAT_AREA] >= area_min]
    return lab, keep, st, cen


def build_nodes(prep, idxs):
    """For each frame index in idxs: list of node dicts with a boolean mask."""
    p = prep["params"]
    nodes = {}
    for t in idxs:
        lab, keep, st, cen = regions(prep["alpha"][t], prep["T_frames"][t], p["area_min"])
        nl = []
        for k in keep:
            mk = lab == k
            nl.append(dict(t=int(t), mask=mk, area=int(st[k, cv2.CC_STAT_AREA]), cx=float(cen[k][0]), cy=float(cen[k][1]),
                           mass=float(prep["alpha"][t][mk].sum())))
        nodes[int(t)] = nl
    return nodes


def link_nodes(nodes, idxs, p):
    """Directed links a(t) -> b(t+1): at least link_overlap of a lies inside b (b dilated)."""
    k = p["link_dilate"]
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
    links = []
    for t in idxs[:-1]:
        t2 = t + 1
        if t2 not in nodes:
            continue
        dil = [cv2.dilate(b["mask"].astype(np.uint8), ker).astype(bool) for b in nodes[t2]]
        for ia, a in enumerate(nodes[t]):
            for ib, b in enumerate(nodes[t2]):
                inter = np.count_nonzero(a["mask"] & dil[ib])
                if inter / a["area"] >= p["link_overlap"]:
                    links.append(((t, ia), (t2, ib)))
    return links


def chains_from_links(nodes, links):
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for t, nl in nodes.items():
        for i in range(len(nl)):
            find((t, i))
    for a, b in links:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    groups = {}
    for n in list(parent):
        groups.setdefault(find(n), []).append(n)
    return list(groups.values())


def ancestors(chain_nodes, links, target):
    """Nodes with a forward-link path into `target` (set of nodes)."""
    back = {}
    for a, b in links:
        back.setdefault(b, []).append(a)
    seen = set(target); stack = list(target)
    while stack:
        x = stack.pop()
        for a in back.get(x, []):
            if a not in seen:
                seen.add(a); stack.append(a)
    return seen


def analyse(prep, idxs):
    """Lineages over frame indices idxs (consecutive ints). A lineage = a root region (no earlier region links
    into it) and its pure descendants (regions fed by that root only). Returns (chains, nodes)."""
    p = prep["params"]
    idxs = list(idxs)
    nodes = build_nodes(prep, idxs)
    links = link_nodes(nodes, idxs, p)
    preds, succs = {}, {}
    for a, b in links:
        preds.setdefault(b, []).append(a); succs.setdefault(a, []).append(b)
    # every region has one parent: the earlier region feeding it with the most area (small regions swallowed by a
    # growing plume do not make the plume's lineage impure). A lineage is a root and all regions descending from it.
    root_of = {}
    for t in idxs:
        for i in range(len(nodes[t])):
            n = (t, i)
            if n not in preds:
                root_of[n] = n
            else:
                par = max(preds[n], key=lambda q: nodes[q[0]][q[1]]["area"])
                root_of[n] = root_of[par]
    roots_of = {n: frozenset([r]) for n, r in root_of.items()}
    hor = prep["horizon"]
    out = []
    for r in [n for n, rs in roots_of.items() if rs == frozenset([n])]:
        pure = [n for n, rs in roots_of.items() if rs == frozenset([r])]
        ts = sorted({t for t, _ in pure})
        if len(ts) < p["min_chain_frames"]:
            continue
        areas = {t: sum(nodes[t][i]["area"] for tt, i in pure if tt == t) for t in ts}
        masses = {t: sum(nodes[t][i]["mass"] for tt, i in pure if tt == t) for t in ts}
        big = [t for t in ts if areas[t] >= p["confirm_area"]]
        if not big:
            continue
        t_conf = big[-1]
        rn = nodes[r[0]][r[1]]
        seed_area = rn["area"]; cx, cy = rn["cx"], rn["cy"]
        on_ground = cy >= hor[int(np.clip(cx, 0, W - 1))] - p["horizon_tol"]
        grown = max(areas.values()) / max(seed_area, 1) >= p["grow_ratio_min"]
        small_seed = seed_area <= p["seed_area_max"]
        tex = lineage_texture_loss(prep, nodes, pure, t_conf)
        cshift = lineage_colour_shift(prep, nodes, pure, t_conf)
        # a veil changes more than brightness: relative contrast falls, or chromaticity moves (a shadow does neither)
        if p.get("veil_rule") == "texture_first" and tex is not None:
            textured = tex >= p["texture_loss_min"]          # a textured background must lose contrast
        else:
            textured = (tex is not None and tex >= p["texture_loss_min"]) or cshift >= p["chroma_shift_min"]
        preexisting = r[0] == idxs[0]      # present at the first analysed frame: no seed was seen
        cls = classify_chain(prep, nodes, pure, r, on_ground, grown and textured, small_seed, areas, t_conf)
        if preexisting and cls[0] == "smoke":
            cls = ("other", RULES["other"])
        out.append(dict(nodes=pure, root=r, t_first=r[0], t_conf=t_conf, ts=ts, mass=sum(masses.values()),
                        seed_area=seed_area, seed_xy=(cx, cy), on_ground=bool(on_ground),
                        grown=bool(grown), small_seed=bool(small_seed), cls=cls[0], rule=cls[1],
                        area_conf=areas[t_conf], texture_loss=tex, colour_shift=cshift))
    # class and rule of every node: the chain it belongs to, or (merged regions) its largest-mass root, else other
    cls_of_root = {c["root"]: (c["cls"], c["rule"], c["mass"]) for c in out}
    for t in idxs:
        for i, nd in enumerate(nodes[t]):
            best = None
            for rt in roots_of[(t, i)]:
                if rt in cls_of_root and (best is None or cls_of_root[rt][2] > best[2]):
                    best = cls_of_root[rt]
            nd["cls"], nd["rule"] = (best[0], best[1]) if best else ("other", RULES["other"])
    return out, nodes


def _core(prep, nodes, pure, t_conf):
    """pixels of the lineage at t_conf in the top quarter of opacity (the veil core, not the faint fringe)"""
    m = np.any([nodes[t][i]["mask"] for t, i in pure if t == t_conf], axis=0)
    a = prep["alpha"][t_conf]
    thr = np.quantile(a[m], 0.75)
    return m & (a >= thr)


def lineage_colour_shift(prep, nodes, pure, t_conf):
    from .vector import _chroma
    m = _core(prep, nodes, pure, t_conf)
    n, _, _ = core.normalise(prep["frames"][t_conf], prep["B"])
    Is = smooth(n, prep["params"]["smooth_sigma"])
    cs = np.linalg.norm(_chroma(Is) - _chroma(prep["Bs"]), axis=-1)
    return float(np.median(cs[m]))


def lineage_texture_loss(prep, nodes, pure, t_conf):
    m = _core(prep, nodes, pure, t_conf)
    tl = texture_loss_map(prep, t_conf)[m]
    tl = tl[np.isfinite(tl)]
    if len(tl) < max(30, 0.2 * m.sum()):
        return None            # background too flat to say (open sky): the rule does not apply
    return float(np.median(tl))


def classify_chain(prep, nodes, g, root, on_ground, grown, small_seed, areas, t_conf):
    p = prep["params"]
    if on_ground and grown and small_seed:
        return "smoke", RULES["smoke"]
    # lowest-opacity broad veil
    tt = t_conf
    amax = max(nodes[t][i]["mass"] / nodes[t][i]["area"] for t, i in g)
    cover = max(areas.values()) / float(H * W)
    if amax < p["haze_alpha_max"] and cover > p["haze_cover_min"]:
        return "haze_fog", RULES["haze_fog"]
    if not on_ground:
        return "cloud", RULES["cloud"]
    # warm colour shift at the ground without plume growth
    node_masks = [nodes[t][i]["mask"] for t, i in g if t == tt]
    m = np.any(node_masks, axis=0)
    fr = prep["frames"][tt]; B = prep["B"]
    warm = float(np.median(((fr[..., 0] - fr[..., 2]) / (fr.sum(-1) + 1e-3) - (B[..., 0] - B[..., 2]) / (B.sum(-1) + 1e-3))[m]))
    if warm >= p["dust_warm_min"] and not grown:
        return "dust", RULES["dust"]
    return "other", RULES["other"]


# ---------------------------------------------------------------- run
def label_sequence(sq, params=None, pre_idx=None):
    p = params or get_params()
    prep = prepare(sq, p, pre_idx)
    if prep["info"].get("excluded"):
        return dict(prep=prep, excluded=prep["info"]["excluded"])
    T = len(prep["alpha"])
    pre = prep["pre_idx"]
    post_idx = list(range(int(pre[-1]) + 1, T))
    chains, nodes = analyse(prep, post_idx)
    smoke = [c for c in chains if c["cls"] == "smoke"]
    first = None; main = None
    if smoke:
        main = max(smoke, key=lambda c: c["mass"])
        first = main["t_first"]
    # placebo on the pre window (null alphas)
    pchains, _ = analyse(prep, list(range(int(pre[0]), int(pre[-1]) + 1)))
    placebo_frames = sorted({t for c in pchains if c["cls"] == "smoke" for t, _ in c["nodes"]})
    return dict(prep=prep, chains=chains, nodes=nodes, main=main, first_frame=first,
                first_offset=None if first is None else int(prep["offsets"][first]),
                placebo_chains=pchains, placebo_frames=placebo_frames, excluded=None)


def class_map(nodes, t, shape=(H, W)):
    """uint8 class index map (see CLASSES) for frame t from analysed nodes."""
    m = np.zeros(shape, np.uint8)
    for nd in nodes.get(t, []):
        m[nd["mask"]] = CLASSES.index(nd["cls"])
    return m


def contours_at(alpha_t, T, level):
    """Edge polygons of {alpha >= max(level, T)} as lists of (x, y) integer points."""
    thr = np.maximum(level, T) if level is not None else T
    m = (alpha_t >= thr).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cs:
        if len(c) >= 4 and cv2.contourArea(c) >= 8:
            out.append(cv2.approxPolyDP(c, 0.8, True).reshape(-1, 2).tolist())
    return out

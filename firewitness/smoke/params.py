"""All tunable numbers in one place. Every output records the hash of this dict.
Changes are made only through the improvement loop (results/ROUNDS_smoke.md)."""
import copy, hashlib, json

DEFAULT = dict(
    version="v1",
    veil_sky_rule=True,
    horizon_method="seam",
    # frames and background
    pre_end_offset=-300,        # background = frames with offset <= this (seconds)
    pre_start_offset=-2400,
    min_pre_frames=12,
    max_shift_px=3.0,           # pre-window registration drift limit (working size)
    apply_shift_above=0.3,
    min_luminance=0.20,         # night frames out of scope below this (median, pre window)
    min_frames=60,
    # opacity
    smooth_sigma=2.0,
    endmember_dark=0.30,
    endmember_light=0.85,
    endmember_prior=0.60,
    endmember_prior_weight=0.02,
    min_endmember_dist2=0.02,
    support_min_px=300,
    # noise floor / levels
    null_quantile=0.999,
    noise_floor_min=0.03,
    noise_pixel_quantile=0.95, texture_loss_min=0.15, chroma_shift_min=0.02,
    levels=[0.10, 0.20, 0.40, 0.60],
    null_block=6, null_gap=2,
    # regions and tracing
    area_min=20,
    link_dilate=3,
    link_overlap=0.5,           # share of the earlier region that must lie inside the later one
    confirm_area=400,
    min_chain_frames=3,
    # classes
    seed_area_max=900,
    grow_ratio_min=5.0,
    horizon_tol=8,
    haze_alpha_max=0.15,
    haze_cover_min=0.15,
    dust_warm_min=0.04,
    cloud_speed_max=6.0,
)


def get(**over):
    c = copy.deepcopy(DEFAULT)
    c.update(over)
    return c


def cfg_hash(c):
    return hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()[:16]

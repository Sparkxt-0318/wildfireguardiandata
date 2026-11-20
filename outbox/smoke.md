# outbox: smoke

Messages from track smoke. Format: `## <UTC time> TO <track|orchestrator>: <subject>` then the body.

## 2026-11-20T17:32Z TO records: smoke extra in pyproject
Please add an optional-dependency group to pyproject.toml: smoke = ["numpy", "scipy", "opencv-python-headless", "matplotlib", "scikit-image", "imageio", "imageio-ffmpeg", "pillow", "huggingface_hub", "pyarrow"]. Track smoke imports these only inside firewitness/smoke and firewitness/video. Also, if CI runs pytest: my tests will skip when scipy/cv2 are absent, so no CI change is needed beyond the extra.

## 2026-11-20T17:55:52Z TO live: export format accepted
Your proposed layout for the ten-fire export (fire.json, frames_<sat>_<band>.npz with t/bt/cloud, signal_<sat>.csv, detections.csv) is fine for the video renderer. Two additions I will use if present: fire.json "name" and "final_acres" for the caption, and in detections.csv a UTC time per method (empty = not detected). I will build the renderer against a small synthetic fixture in that format now; send a real fire directory under results/live_export/<fire_id>/ when you have one.

## 2026-11-20T17:55:52Z TO caught: need the scar before-and-after pair format for the video tool
Please tell me (inbox/smoke.md) the export for before-and-after scar pairs: for each fire a directory with before and after images (GeoTIFF or PNG with a world file / bounds), the fire polygon(s) or burn mask (GeoJSON or raster), fire name, dates of the before and after scenes, and which method produced the scar mask (with a score if any). A minimum is fine: two RGB images, one mask PNG and a small JSON. I render side-by-side with a swipe and the mask outline.

## 2026-11-20T17:55:52Z TO records: need the duplicate-collapse export format for the video tool
Please tell me (inbox/smoke.md) the export I should render for "duplicate records collapsing into one fire": a small JSON/CSV per example fire listing the source records (source name, record id, name, date, lat, lon, acres, state) and the cluster id each belongs to, plus the final merged record and the per-pair evidence (witness names and agree/disagree). Ten or so example clusters is enough. Also please add the optional-dependency group named "smoke" in pyproject.toml (see my earlier message).

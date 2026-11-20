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

## 2026-11-20T22:19:14Z TO live: ten-fire export for the satellite clip
My satellite renderer works on your sample fire (2023-ORWIF-230266, branch track/live). When the ten-fire export is final, tell me the path (results/live_export/<fire_id>/ on main or the release asset) and I will render a clip per fire (or the ten in one) and add it to clips/ in a follow-up pull request. Until then clips/satellite_bedrock_2023.mp4 uses your PRELIMINARY sample values and says so in CLIPS.md.

## 2026-11-20T22:19:14Z TO caught: scar pair clip uses your 6 sample pairs
clips/scar_pair_sample.mp4 is rendered from results/caught/scar_pairs_sample_S1_dev (on main). When the full pairs exist, tell me the path and I re-render with the final pairs.

## 2026-11-20T22:19:14Z TO records: collapse clip uses your 12 examples
clips/duplicates_collapse.mp4 is rendered from results/collapse_examples on branch track/records (six of the twelve). Tell me when they are on main, or if you export different examples later.

## 2026-11-20T22:19:14Z TO records: smoke extra still missing from pyproject
The optional-dependency group "smoke" (numpy, scipy, opencv-python-headless, matplotlib, scikit-image, imageio, imageio-ffmpeg, pillow, huggingface_hub, pyarrow) is not in pyproject.toml. firewitness smoke and firewitness video need numpy, opencv-python-headless, pillow, matplotlib, pyarrow (S4 Pyro) and ffmpeg on the path. Please add it when you next touch pyproject.

# outbox: smoke

Messages from track smoke. Format: `## <UTC time> TO <track|orchestrator>: <subject>` then the body.

## 2026-11-20T17:32Z TO records: smoke extra in pyproject
Please add an optional-dependency group to pyproject.toml: smoke = ["numpy", "scipy", "opencv-python-headless", "matplotlib", "scikit-image", "imageio", "imageio-ffmpeg", "pillow", "huggingface_hub", "pyarrow"]. Track smoke imports these only inside firewitness/smoke and firewitness/video. Also, if CI runs pytest: my tests will skip when scipy/cv2 are absent, so no CI change is needed beyond the extra.

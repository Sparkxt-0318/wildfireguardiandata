# Prior art: image matting and smoke opacity estimation

Short note, written so that nothing in this track is described as a first. Sources were found by a literature search on 2026-11-20; the papers were read at abstract level only, and none was re-verified or reproduced. Where a claim below is about a method's content it is taken from the abstract.

**The mixture model is old.** Describing each pixel as a blend of a foreground and a background, I = alpha F + (1 - alpha) B, is the compositing equation of image matting. Applying it to smoke with a known or estimated background is not new:

- Chuang et al., "Video matting of complex scenes" (SIGGRAPH 2002) already demonstrates a smoke matte extraction technique inside a video matting framework.
- Tian et al., "Smoke Detection in Video: An Image Separation Approach" (International Journal of Computer Vision, 2013) assumes a frame is a linear blend of a smoke component and a background image, estimates the blending parameter given the background, and uses the separated smoke component for detection. This is the closest published formulation to the opacity map defined here (known background, per-pixel blend parameter).
- Fukuda et al., "Smoke matting and compositing in video sequences" (IWAIT 2019) mattes smoke without user interaction and without a physical smoke model.
- Ma et al., SFMatting-800 (2023) and SFMattingNet (Remote Sensing, 2025) build a smoke and fire matting dataset and a trimap-free network that predicts alpha, and evaluate classical and deep matting methods on it. They use human-annotated opacity as ground truth and a trained network; this track uses neither.
- Lu et al., Omnimatte (CVPR 2021) associates objects with their time-varying effects such as smoke and shadows in a self-supervised video decomposition.

**What this track does that those do not claim**, stated narrowly and without a priority claim: (1) it ties the lowest edge level to the camera's own pre-ignition noise, measured on the same camera; (2) it treats the continuous opacity map as the label and states which level each human annotation corresponds to (test S4); (3) it defines first smoke by tracing back from a confirmed plume through region links, and compares that time with the human offset in the FIgLib file names (test S3); (4) it classifies by plain-sentence rules on a measured vector, with no trained model; (5) it tests the opacity and edge estimate against composites of known truth (S1) and the false-alarm rate on pre-ignition frames (S2). Parts of (2) to (5) may exist in work not found by one search; absence from the search is not evidence of novelty.

**Other related ideas that are not smoke-specific**: dehazing with a transmission map (Koschmieder's law, He et al. dark channel prior, Fattal) uses the same physics with an estimated airlight; regulatory visible-emission opacity (Ringelmann charts, EPA Method 9) rates the share of light a plume blocks and is the origin of the word opacity for stack smoke. This track's "opacity" borrows that word and is not calibrated to Method 9 readings.

**Limits shared with all single-camera estimates**: with a uniform sky behind the smoke, opacity and smoke colour are not separable; every method needs a stated endmember or a prior.

# SMOKE_EDGE: a reproducible definition of the smoke edge, the first smoke frame and the smoke class

Version v1 (frozen after improvement round R12; parameters in `firewitness/smoke/params.py`, hash recorded in every output). Image data credit: HPWREN, http://hpwren.ucsd.edu/. For annotators and for code: every step below is a measurement or a rule you can apply by hand or by script. No trained model decides anything.

## 1. The label is a measured opacity map

For a fixed camera, at each pixel x and frame t, the opacity alpha(x, t) says how far the smoke has moved the pixel from the camera's own smoke-free background B(x) towards a smoke colour S:

    I(x, t) = (1 - alpha) * B(x) + alpha * S        (alpha between 0, clear, and 1, opaque)

1. **Background B.** The per-pixel temporal median of the frames before ignition (file-name offset at most -300 s, at most 40 minutes back, at least 12 frames), after every frame is corrected for lighting drift: a robust (Tukey) per-channel gain and offset fit of the frame to the background, using all pixels, so that smoke and clouds, being a minority of pixels, do not drive the fit. Frames are shifted to the background if the camera moved by more than 0.3 px; a camera that moved more than 3 px at 512 x 384 inside the pre-ignition window is out of scope.
2. **Smoke colour S.** The point where the colour changes of the strongly changed pixels meet (least-squares intersection of the lines from each pixel's background colour along its change vector), regularised towards a neutral grey. If the intersection is badly determined (fewer than 300 changed pixels, or fewer than 80% of pixels agree on its direction), S is not fitted; then each pixel is measured against a dark grey (0.30) if it got darker and a light grey (0.85) if it got lighter. Over uniform sky the smoke colour cannot be separated from the opacity: the map is then opacity relative to that stated grey. Say so wherever the map is used.
3. **Opacity.** alpha = (I - B) . (S - B) / |S - B|^2, clipped to 0..1, computed on frames smoothed with a 2 px Gaussian (512 x 384 working size, 4x area reduction of the 2048 x 1536 source).
4. The continuous map is the label. Any edge is cut from it.

## 2. Edges are contours at a stated opacity

- **Noise level.** In the pre-ignition frames each frame is measured against a background built without its own block of 6 frames and a 2-frame gap. N(x) is the largest opacity pixel x showed while smoke-free (5 x 5 spatial maximum). The **lowest named level L0** is the median of N over the frame: the noise of a typical pixel of this camera. It is measured, not chosen (a floor of 0.03 applies). A pixel is "above the noise level" when its opacity reaches T(x) = max(L0, N(x)), so glints, moving foliage, and cloud or shadow passages seen before ignition raise the bar at their own pixels only.
- **Fixed levels** above it: 0.10, 0.20, 0.40, 0.60. The edge at level l is the contour of {alpha >= max(l, T)}. An annotator who says "I drew the visible edge" is drawing at one of these levels; the effective level is measured in test S4.
- Regions smaller than 20 px at the working size are not regions.

## 3. First smoke by tracing back

1. Build regions per frame after the background window: connected pixels above the noise level.
2. Link a region at t to a region at t+1 when at least half of the earlier region lies inside the later one (the later one dilated by 3 px): the smoke grew out of it. Each region has one parent, the earlier region feeding it with the most area.
3. A **lineage** is a root region (no earlier region links into it) and all regions descending from it through parents. A root present in the first analysed frame is not a seed (it was already there).
4. A lineage is **confirmed** when it lasts at least 3 frames and reaches 400 px. First smoke is the frame of the root of the confirmed smoke lineage (section 5) with the largest summed opacity.

This is a trace back from a later, confirmed plume to the earliest frame where a region above the noise level persists and connects forward to it.

## 4. The vector per pixel

| variable | measurement |
|---|---|
| opacity | section 1 |
| colour shift | distance between the chromaticity (r-g, b-g over the sum) of the frame and of the background |
| loss of background texture | 1 - (relative contrast of the frame / relative contrast of the background), relative contrast = smoothed gradient energy over smoothed luminance; undefined where the background is flat |
| motion speed | Farneback optical flow of the opacity maps of consecutive frames, px per minute |
| motion direction | direction of that flow, degrees, 0 right, 90 up |
| attachment to a fixed source point | 1 for pixels inside the lineage rooted at the seed, else 0 |
| growth | change of opacity per minute |

## 5. Classes are rules on the vector, one plain sentence each

- **smoke**: a region above the noise level that is linked back through the frames to a small seed (at most 900 px) on or just above the ground (not above the horizon line, a continuous left-to-right seam of the strongest bright-above-dark step in the background luminance, 8 px tolerance), has grown to at least five times its seed area, and passes the veil test: the top quarter of its opacity has lost at least 15% of its relative contrast, or shifted the background chromaticity by at least 0.02, or lies mostly above the horizon (a shadow does none of these, and cannot fall on the sky).
- **cloud**: a region above the noise level that lies mostly above the horizon, has no seed on the ground and drifts slowly.
- **haze or fog**: a region below opacity 0.15 covering more than 15% of the frame, with no seed.
- **dust**: a region with a warm colour shift of at least 0.04 and a ground seed that does not grow into a plume (five times its seed area).
- **other**: everything else above the noise level (lighting change, moving object, lens artefact, a shadow).

The first rule that matches fires. A shadow keeps its relative contrast and chromaticity and cannot fall on the sky, so it fails the veil test of the smoke rule.

## 6. Out of scope

Cameras that move without registration; night frames (median pre-window luminance below 0.20); fewer than 60 frames or fewer than 12 pre-ignition frames. Excluded sequences are listed with the reason, never dropped silently. The map is not physical optical depth. Smoke seen only against uniform sky has an unidentified colour. Classes other than smoke have no independent truth in these sequences.

## 7. Parameters (v1)

Every number is in `firewitness/smoke/params.py` and its hash is written into each output. Working size 512 x 384; smoothing sigma 2 px; background offsets -2400 to -300 s (at least 12 frames); noise: per-pixel maximum over leave-block-out nulls (block 6 frames, gap 2), 5 x 5 spatial maximum, L0 = median of that map, floor 0.03; fixed levels 0.10, 0.20, 0.40, 0.60; minimum region 20 px; link overlap 0.5, dilation 3 px; confirmation 400 px and 3 frames; seed at most 900 px; growth at least 5x; veil test 0.15 texture loss or 0.02 chromaticity or sky core; horizon tolerance 8 px. How each number was chosen or changed: `results/ROUNDS_smoke.md`.

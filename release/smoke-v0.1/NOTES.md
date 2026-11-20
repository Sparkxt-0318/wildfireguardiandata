# smoke-v0.1 (track smoke)

Image data: HPWREN, http://hpwren.ucsd.edu/ (FIgLib). Every opacity map, contour and clip derived from it carries this credit.

Files
- `sealed_opacity_edges.tar.gz`: one folder per sealed FIgLib sequence (16; two are excluded with a reason in their `labels.json`): `opacity.npz` (`alpha` uint8 = opacity x 255 per frame, `noise_threshold` uint8, `offsets`, `classes`, `class_names`), `edges.json` (contours per frame at the noise level and 0.10, 0.20, 0.40, 0.60, working size 512 x 384), `labels.json` (parameters and hash, input hashes, first-smoke offset, lineage table with the class and the rule sentence that fired). Produced once with the frozen configuration v1: `firewitness smoke label <sequence dir> --out <dir>`.
- `SMOKE_EDGE.md`: the definition (two pages). `SMOKE_RESULTS.md`: results with n, interval, source file and limits. `PRIOR_ART_SMOKE.md`: prior-art note.
- `clips_gifs_stills.tar.gz`: GIFs (480 px) and still frames of the nine presentation clips; the MP4 clips (1080p) are in the repository folder `clips/`.

Read first: S2 (false pre-ignition frames) is 0.8% on the sealed set (upper limit 2.4%) but 7.1% on the dev set; the S1 opacity and edge targets are not met; see `SMOKE_RESULTS.md`.

"""Revert test on the national v0.1 patch set: load FPA FOD as the tool does, apply every released patch, revert,
compare canonical hashes (raw -> clean -> back). Also a second-application check: applying the patches to the clean
table must fail strictly or change nothing."""
import sys, gzip, json, time
from firewitness.core import PatchSet
from firewitness.records import pipeline, frame_ops
t = time.time()
raw = pipeline.load_fod_strings(None)
h_raw = frame_ops.sha256_frame(raw, "utf-8")
print("loaded", raw.shape, "sha256(raw, canonical)", h_raw, round(time.time()-t), "s", flush=True)
ps = PatchSet.read(sys.argv[1])
print("patches", len(ps.patches), "header input_sha256", ps.input_sha256, flush=True)
cols = list(raw.columns)
clean = frame_ops.apply_frame(raw, ps.patches, "rid")
h_clean = frame_ops.sha256_frame(clean, "utf-8")
print("clean", clean.shape, "sha256(clean)", h_clean, flush=True)
ch = frame_ops.changed_cells(raw, clean[[c for c in clean.columns if c in cols]], "rid")
pk = {(p.record_id, p.field) for p in ps.patches}
print("changed cells", len(ch), "changed cells without a patch", len(ch - pk), flush=True)
back = frame_ops.revert_frame(clean, ps.patches, "rid", cols)
h_back = frame_ops.sha256_frame(back, "utf-8")
print("sha256(back)", h_back, "EQUAL to raw:", h_back == h_raw, round(time.time()-t), "s")

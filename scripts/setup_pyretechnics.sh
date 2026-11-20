#!/bin/sh
# Fetch the published Rothermel implementation (pyretechnics, Sig-GIS) used by rule R3b and the spread stretch.
# Not vendored: its community licence allows non-commercial research use and it pins old numpy/Cython.
# The sdist is unpacked and its pure-Python `src/pyretechnics` is put on the path by firewitness.fuel.spread.
set -e
DEST="${FIREWITNESS_PYRETECHNICS:-$HOME/.cache/firewitness/pyretechnics_src}"
mkdir -p "$DEST" "$DEST/dl"
pip download pyretechnics --no-deps -d "$DEST/dl" >/dev/null
tar xzf "$DEST"/dl/pyretechnics-*.tar.gz -C "$DEST/dl"
rm -rf "$DEST/pyretechnics"
cp -r "$DEST"/dl/pyretechnics-*/src/pyretechnics "$DEST/pyretechnics"
python3 - <<PY
import sys; sys.path.insert(0, "$DEST")
import pyretechnics.surface_fire as sf
print("pyretechnics ready:", sf.__file__)
PY
